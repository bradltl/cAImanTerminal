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

#[derive(Serialize)]
struct Sample {
    case: usize,
    elapsed_ms: f64,
    valid: bool,
    path: &'static str,
    timings: Option<crate::metrics::GenerationTimings>,
}
fn measure(
    worker: &worker::Worker,
    text: &str,
    case: usize,
    ticket: u64,
) -> anyhow::Result<Sample> {
    let mut session = Session::new(1, std::env::current_dir()?.display().to_string());
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
    loop {
        let remaining = deadline.saturating_duration_since(Instant::now());
        match worker.events.recv_timeout(remaining)? {
            Event::Status(_) => (),
            Event::Completed {
                ticket: received,
                result,
                ..
            } => {
                anyhow::ensure!(received == ticket, "Mismatched benchmark result");
                let (valid, path, timings) = match result {
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
                    ),
                    Err(_) => (false, "rejected", None),
                };
                return Ok(Sample {
                    case,
                    elapsed_ms: started.elapsed().as_secs_f64() * 1000.0,
                    valid,
                    path,
                    timings,
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
    let worker = worker::spawn(model, false, settings.clone());
    let cold = measure(&worker, &corpus[0], 0, 0)?;
    let mut measured = Vec::new();
    let mut passed = samples >= 200 && runs == 3;
    for run in 0..runs {
        let mut records = Vec::new();
        for i in 0..samples {
            let case = (i + run) % corpus.len();
            records.push(measure(
                &worker,
                &corpus[case],
                case,
                (1 + run * samples + i) as u64,
            )?);
            if (i + 1) % 20 == 0 {
                eprintln!("alpha latency run {}: {}/{}", run + 1, i + 1, samples);
            }
        }
        let p50 = percentile(&records, 50);
        let p95 = percentile(&records, 95);
        let failures = records.iter().filter(|s| !s.valid).count();
        passed &= failures == 0 && p50 <= 750.0 && p95 <= 1500.0;
        measured.push(
            serde_json::json!({"p50_ms":p50,"p95_ms":p95,"failures":failures,"samples":records}),
        );
    }
    use sha2::{Digest, Sha256};
    let corpus_hash = format!("{:x}", Sha256::digest(corpus_text.as_bytes()));
    println!(
        "{}",
        serde_json::json!({"policy":"alpha-v1","release_build":true,"corpus_sha256":corpus_hash,"model_sha256":crate::model_file::DEFAULT_SHA256,"threads":settings.inference.threads,"cold":cold,"runs":measured,"alpha_latency_passed":passed})
    );
    anyhow::ensure!(passed, "Alpha latency gate failed; dogfood remains blocked");
    Ok(())
}
