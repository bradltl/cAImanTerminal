#![no_main]
use caiman_terminal::{alpha_policy::HostFacts, context::Session, host, prompt::Prompt, worker::{self, Request}};
use libfuzzer_sys::fuzz_target;
use std::sync::{Arc, atomic::AtomicU64};
fuzz_target!(|data: &[u8]| {
    if data.len() > 4096 { return; }
    let Ok(candidate) = std::str::from_utf8(data) else { return; };
    // Exercise relative operands at an ordinary and a protected physical CWD,
    // including a lexically equivalent path. No filesystem commands are run.
    let cwd = ["/tmp", "/etc", "/tmp/../etc"][data.len() % 3];
    let mut session = Session::new(1, cwd.into());
    session.at_prompt = true;
    session.terminal_text = candidate.into();
    let request = Request { session, text: candidate.into(), ticket: 0, cancellation: Arc::new(AtomicU64::new(0)), passive: false };
    let trace = worker::check_candidate(&request, candidate, &HostFacts::local());
    if trace.stageable {
        assert!(!candidate.chars().any(char::is_control));
        assert!(host::parse_commands(candidate).is_ok());
        assert!(host::assess_risk_at(candidate, cwd, false, "").is_ok());
    }
    if host::assess_risk_at(candidate, cwd, false, "").is_err() { assert!(!trace.stageable); }
    let mut prompt: Prompt = serde_json::from_str(&worker::build_prompt(&request, candidate)).unwrap();
    assert!(!prompt.render().contains("<|"));
    for _ in 0..32 { if !prompt.compact() { break; } }
});
