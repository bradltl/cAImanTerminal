//! Explicit synthetic benchmark only; no dogfood records are written here.
use crate::{
    context::Session,
    worker::{self, Event, Request},
};
use serde::Serialize;
use std::{
    path::PathBuf,
    sync::{atomic::AtomicU64, Arc},
    time::{Duration, Instant},
};

#[derive(Clone, Serialize)]
struct Sample {
    case: usize,
    elapsed_ms: f64,
    valid: bool,
    path: &'static str,
    timings: Option<crate::metrics::GenerationTimings>,
    pipeline: Option<crate::metrics::PipelineTimings>,
    queue_and_delivery_ms: f64,
    retryable: bool,
}
fn measure(
    worker: &worker::Worker,
    text: &str,
    case: usize,
    ticket: u64,
) -> anyhow::Result<Sample> {
    measure_at(
        worker,
        text,
        case,
        ticket,
        std::env::current_dir()?.display().to_string(),
    )
}
fn measure_at(
    worker: &worker::Worker,
    text: &str,
    case: usize,
    ticket: u64,
    cwd: String,
) -> anyhow::Result<Sample> {
    let mut session = Session::new(1, cwd);
    session.at_prompt = true;
    session.request_id = ticket;
    let started = Instant::now();
    worker.requests.send(Request {
        session,
        text: text.into(),
        ticket,
        cancellation: Arc::new(AtomicU64::new(ticket)),
        passive: false,
    })?;
    let deadline = started + Duration::from_secs(60);
    let mut pipeline = None;
    loop {
        let remaining = deadline.saturating_duration_since(Instant::now());
        match worker.events.recv_timeout(remaining)? {
            Event::Status(_) => (),
            Event::Measured {
                ticket: received,
                timings,
            } => {
                anyhow::ensure!(received == ticket, "Mismatched benchmark timing");
                pipeline = Some(timings);
            }
            Event::Completed {
                ticket: received,
                result,
                ..
            } => {
                anyhow::ensure!(received == ticket, "Mismatched benchmark result");
                let (valid, path, timings, retryable) = match result {
                    Ok(answer) => (
                        answer.validation.is_some(),
                        if answer.repaired {
                            "deterministic_correction"
                        } else if answer.timings.is_some() {
                            "normal_model"
                        } else {
                            "deterministic"
                        },
                        answer.timings,
                        false,
                    ),
                    Err(error) => (
                        false,
                        "rejected",
                        pipeline.as_ref().and_then(|p| p.generation.clone()),
                        error.starts_with("Unverifiable:"),
                    ),
                };
                let elapsed_ms = started.elapsed().as_secs_f64() * 1000.0;
                return Ok(Sample {
                    case,
                    elapsed_ms,
                    valid,
                    path,
                    timings,
                    queue_and_delivery_ms: (elapsed_ms
                        - pipeline.as_ref().map_or(0.0, |p| p.worker_ms))
                    .max(0.0),
                    pipeline,
                    retryable,
                });
            }
        }
    }
}
fn percentile(samples: &[Sample], percent: usize) -> f64 {
    let mut times: Vec<_> = samples.iter().map(|s| s.elapsed_ms).collect();
    times.sort_by(f64::total_cmp);
    times[(times.len() * percent).div_ceil(100).saturating_sub(1)]
}

pub fn run(model: PathBuf) -> anyhow::Result<()> {
    anyhow::ensure!(
        !cfg!(debug_assertions),
        "Latency acceptance requires a release build"
    );
    let mut settings = crate::settings::Settings::default();
    if let Ok(threads) = std::env::var("CAYMAN_BENCH_THREADS") {
        settings.inference.threads = threads.parse()?;
    }
    let samples: usize = std::env::var("CAYMAN_BENCH_SAMPLES")
        .unwrap_or_else(|_| "200".into())
        .parse()?;
    let runs: usize = std::env::var("CAYMAN_BENCH_RUNS")
        .unwrap_or_else(|_| "3".into())
        .parse()?;
    anyhow::ensure!(
        (1..=2000).contains(&samples) && (1..=3).contains(&runs),
        "Invalid benchmark size"
    );
    settings.validate()?;
    let corpus_text = include_str!("../resources/alpha-latency.json");
    let corpus: Vec<String> = serde_json::from_str(corpus_text)?;
    let model_candidate = std::env::var("CAYMAN_BENCH_MODEL_PATH").as_deref() == Ok("1");
    let worker = worker::spawn_with_routing(model, false, settings.clone(), model_candidate);
    let cold = measure(&worker, &corpus[0], 0, 0)?;
    // Deliberate benchmark opt-in simulates clicking Retry suggestion once.
    // Retries never replace first-attempt failures in the acceptance statistics.
    let profile_retry = std::env::var("CAYMAN_BENCH_RETRY").as_deref() == Ok("1");
    let mut next_ticket = 1;
    let mut retries = Vec::new();
    let mut measured = Vec::new();
    let mut passed = samples >= 200 && runs == 3;
    for run in 0..runs {
        let mut records = Vec::new();
        for i in 0..samples {
            let case = (i + run) % corpus.len();
            let sample = measure(&worker, &corpus[case], case, next_ticket)?;
            next_ticket += 1;
            if profile_retry && sample.retryable {
                let retry = measure(&worker, &corpus[case], case, next_ticket)?;
                next_ticket += 1;
                retries.push(serde_json::json!({"run":run,"first_plus_retry_ms":sample.elapsed_ms + retry.elapsed_ms,"sample":retry}));
            }
            records.push(sample);
            if (i + 1) % 20 == 0 {
                eprintln!("alpha latency run {}: {}/{}", run + 1, i + 1, samples);
            }
        }
        let p50 = percentile(&records, 50);
        let p95 = percentile(&records, 95);
        let failures = records.iter().filter(|s| !s.valid).count();
        passed &= failures == 0 && p50 <= 750.0 && p95 <= 1500.0;
        let mut paths = serde_json::Map::new();
        for path in [
            "normal_model",
            "deterministic",
            "deterministic_correction",
            "rejected",
        ] {
            let group: Vec<_> = records.iter().filter(|s| s.path == path).cloned().collect();
            if !group.is_empty() {
                paths.insert(path.into(), serde_json::json!({"count":group.len(),"p50_ms":percentile(&group,50),"p95_ms":percentile(&group,95)}));
            }
        }
        measured.push(
            serde_json::json!({"p50_ms":p50,"p95_ms":p95,"failures":failures,"paths":paths,"samples":records}),
        );
    }
    use sha2::{Digest, Sha256};
    // Separate, frozen deterministic calibration: synthetic filename evidence,
    // actual worker and gates, no inference or execution, no personal files.
    let directory = tempfile::tempdir()?;
    std::fs::write(
        directory.path().join("README.md"),
        "Synthetic benchmark fixture\n",
    )?;
    let mut deterministic = Vec::new();
    for _ in 0..20 {
        deterministic.push(measure_at(
            &worker,
            "read README.md",
            0,
            next_ticket,
            directory.path().display().to_string(),
        )?);
        next_ticket += 1;
    }
    let deterministic_summary = serde_json::json!({
        "fixture":"read_named_file_v1", "count":deterministic.len(),
        "p50_ms":percentile(&deterministic,50), "p95_ms":percentile(&deterministic,95),
        "failures":deterministic.iter().filter(|s| !s.valid).count(), "samples":deterministic
    });
    let corpus_hash = format!("{:x}", Sha256::digest(corpus_text.as_bytes()));
    println!(
        "{}",
        serde_json::json!({"policy":"alpha-v1","release_build":true,"corpus_sha256":corpus_hash,"expected_model_sha256":crate::model_file::DEFAULT_SHA256,"model_candidate_path":model_candidate,"threads":settings.inference.threads,"cold":cold,"runs":measured,"deterministic_calibration":deterministic_summary,"retry_profile_enabled":profile_retry,"retries":retries,"alpha_latency_passed":passed})
    );
    anyhow::ensure!(passed, "Alpha latency gate failed; dogfood remains blocked");
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn failed_completion_keeps_diagnostics_but_never_becomes_a_fast_success() {
        let (requests, receive) = std::sync::mpsc::sync_channel::<Request>(1);
        let (send, events) = std::sync::mpsc::channel();
        std::thread::spawn(move || {
            let request = receive.recv().unwrap();
            send.send(Event::Measured {
                ticket: request.ticket,
                timings: crate::metrics::PipelineTimings {
                    generation: Some(Default::default()),
                    ..Default::default()
                },
            })
            .unwrap();
            send.send(Event::Completed {
                id: request.session.id,
                ticket: request.ticket,
                passive: false,
                result: Err("Unverifiable: synthetic validation failure".into()),
            })
            .unwrap();
        });
        let sample = measure(&worker::Worker { requests, events }, "ls", 0, 4).unwrap();
        assert!(!sample.valid);
        assert!(sample.retryable);
        assert!(sample.timings.is_some());
        assert!(sample.pipeline.is_some());
        assert!(sample.queue_and_delivery_ms >= 0.0);
    }
}
