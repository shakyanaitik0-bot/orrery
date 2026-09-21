"""YouTube ingestion: pull a video's transcript, then hand it to the same
text pipeline PDFs and pasted notes already go through.

No YouTube API key is needed — `youtube-transcript-api` reads the caption
track a video already has (auto-generated or uploaded). A video with
captions disabled has nothing to extract, and that's a real, expected
failure rather than a bug: we say so rather than silently building an
empty graph.
"""

import re

import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    AgeRestricted,
    CouldNotRetrieveTranscript,
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
)

_URL_PATTERNS = [
    re.compile(r"(?:v=|/videos/|embed/|youtu\.be/|/v/|/shorts/)([A-Za-z0-9_-]{11})"),
]


class YoutubeExtractionError(Exception):
    """A video id couldn't be resolved, or has no readable transcript."""


def extract_video_id(url_or_id: str) -> str:
    candidate = url_or_id.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
        return candidate
    for pattern in _URL_PATTERNS:
        m = pattern.search(candidate)
        if m:
            return m.group(1)
    raise YoutubeExtractionError(
        "That doesn't look like a YouTube video URL or id."
    )


def fetch_transcript(url_or_id: str) -> str:
    """Return the video's transcript as plain text, or raise
    YoutubeExtractionError with a reason a learner would understand."""
    video_id = extract_video_id(url_or_id)

    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id)
    except TranscriptsDisabled as exc:
        raise YoutubeExtractionError(
            "This video has captions disabled, so there's no transcript to read."
        ) from exc
    except NoTranscriptFound as exc:
        raise YoutubeExtractionError(
            "No transcript is available for this video in a readable language."
        ) from exc
    except VideoUnavailable as exc:
        raise YoutubeExtractionError(
            "That video is unavailable — check the link is correct and public."
        ) from exc
    except AgeRestricted as exc:
        raise YoutubeExtractionError(
            "That video is age-restricted, so its transcript can't be read without signing in."
        ) from exc
    except (IpBlocked, RequestBlocked) as exc:
        raise YoutubeExtractionError(
            "YouTube is blocking transcript requests from this server right now "
            "(this happens on some networks/IPs). Try again in a few minutes, "
            "or use pasted notes/a PDF instead."
        ) from exc
    except CouldNotRetrieveTranscript as exc:
        # Catch-all for the library's other failure modes (proxy/cookie/PO-token
        # issues, YouTube layout changes, etc.) — surface a clear reason instead
        # of a bare 500.
        raise YoutubeExtractionError(
            f"Couldn't read that video's transcript: {exc}"
        ) from exc
    except requests.exceptions.RequestException as exc:
        # A network-layer failure reaching YouTube at all (DNS, proxy, timeout) —
        # this happened unhandled before and surfaced as a bare 500.
        raise YoutubeExtractionError(
            f"Couldn't reach YouTube to fetch that transcript: {exc}"
        ) from exc

    text = " ".join(snippet.text.strip() for snippet in fetched.snippets if snippet.text.strip())
    if len(text) < 40:
        raise YoutubeExtractionError(
            "That video's transcript is too short to build a concept graph from."
        )
    return text
