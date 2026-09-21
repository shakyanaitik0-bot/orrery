import { ImageResponse } from "next/og";

export const size = { width: 64, height: 64 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#080d13",
          borderRadius: 14,
        }}
      >
        <svg width="44" height="44" viewBox="0 0 44 44">
          <ellipse cx="22" cy="22" rx="20" ry="9" stroke="#5aa9c7" strokeWidth="2" fill="none" />
          <ellipse
            cx="22"
            cy="22"
            rx="20"
            ry="9"
            stroke="#4bd6b0"
            strokeWidth="2"
            fill="none"
            transform="rotate(60 22 22)"
          />
          <ellipse
            cx="22"
            cy="22"
            rx="20"
            ry="9"
            stroke="#e0b341"
            strokeWidth="2"
            fill="none"
            transform="rotate(120 22 22)"
          />
          <circle cx="22" cy="22" r="5.5" fill="#e6eef5" />
        </svg>
      </div>
    ),
    { ...size }
  );
}
