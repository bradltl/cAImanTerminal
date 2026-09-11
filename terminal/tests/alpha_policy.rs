use caiman_terminal::{
    alpha_policy::{evaluate, HostFacts},
    context::Session,
    worker::Request,
};
use std::sync::{atomic::AtomicU64, Arc};
fn fixture(text: &str) -> Request {
    let mut session = Session::new(1, "/tmp".into());
    session.at_prompt = true;
    Request {
        session,
        text: text.into(),
        ticket: 0,
        cancellation: Arc::new(AtomicU64::new(0)),
        passive: false,
    }
}
#[test]
fn explicit_cli_coverage_and_corrections_are_fail_closed() {
    let facts = HostFacts {
        package_manager: None,
        root: false,
        installed: vec!["df".into(), "ls".into(), "git".into()],
        documentation: Default::default(),
    };
    let good = evaluate(&fixture("show disk usage"), "df -h", &facts);
    assert!(good.stageable);
    let correction = evaluate(&fixture("show disk usage"), "df --made-up", &facts);
    assert!(correction.stageable);
    assert_eq!(
        correction.correction.as_deref(),
        Some("canonical_task_options")
    );
    for (request, candidate) in [
        ("git nonexistent", "git nonexistent"),
        ("df --made-up", "df --made-up"),
        ("show disk usage", "df -h; rm -rf /"),
        ("explain disk usage", "df -h"),
    ] {
        assert!(!evaluate(&fixture(request), candidate, &facts).stageable);
    }
    let mut passive = fixture("ls");
    passive.passive = true;
    assert!(!evaluate(&passive, "ls", &facts).stageable);
}
