//! Python bindings for the Orrery adaptive learning engine.
//!
//! The algorithms themselves are `skillcoco-core` (MIT, vendored in
//! `packages/engine`) — Bayesian Knowledge Tracing and SM-2 as implemented and
//! unit-tested upstream. Nothing here reimplements them; this crate only
//! marshals values across the Python boundary so the API server can score
//! mastery with the same code the desktop app used.

use pyo3::prelude::*;
use skillcoco_core::bkt::{update_mastery, BKTParams, MASTERY_THRESHOLD};
use skillcoco_core::sm2::sm2_calculate;

/// Update a learner's mastery estimate for one concept after one observation.
///
/// `prior` is the current P(knows this concept) in [0, 1]; `correct` is whether
/// they just answered correctly. Returns the posterior with the BKT learning
/// step applied.
#[pyfunction]
#[pyo3(signature = (prior, correct, p_know=0.3, p_learn=0.1, p_guess=0.2, p_slip=0.1))]
fn bkt_update(
    prior: f64,
    correct: bool,
    p_know: f64,
    p_learn: f64,
    p_guess: f64,
    p_slip: f64,
) -> f64 {
    let params = BKTParams {
        p_know,
        p_learn,
        p_guess,
        p_slip,
    };
    update_mastery(&params, prior, correct)
}

/// The mastery probability at which a concept counts as learned.
#[pyfunction]
fn mastery_threshold() -> f64 {
    MASTERY_THRESHOLD
}

/// Schedule the next review of a flashcard.
///
/// `quality` is recall quality in [0, 5]. Returns
/// `(interval_days, ease_factor, repetitions)`.
#[pyfunction]
#[pyo3(signature = (quality, repetitions, ease_factor, interval))]
fn sm2_schedule(
    quality: i32,
    repetitions: i32,
    ease_factor: f64,
    interval: f64,
) -> (f64, f64, i32) {
    let r = sm2_calculate(quality, repetitions, ease_factor, interval);
    (r.interval, r.ease_factor, r.repetitions)
}

#[pymodule]
fn orrery_engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(bkt_update, m)?)?;
    m.add_function(wrap_pyfunction!(sm2_schedule, m)?)?;
    m.add_function(wrap_pyfunction!(mastery_threshold, m)?)?;
    Ok(())
}
