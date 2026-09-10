use cayman_terminal::{
    context::Session,
    flag_help, host,
    worker::{self, Request},
};
use std::sync::{atomic::AtomicU64, Arc};
fn request(text: &str) -> Request {
    let mut session = Session::new(1, "/tmp".into());
    session.input = text.into();
    session.at_prompt = true;
    Request {
        session,
        text: text.into(),
        ticket: 0,
        cancellation: Arc::new(AtomicU64::new(0)),
        passive: true,
    }
}
#[test]
fn flags_trigger_even_for_short_commands_and_pipeline_members() {
    for text in [
        "ps -",
        "ps --",
        "ps -f",
        "ps --so",
        "ls -l",
        "du -",
        "find . -",
        "git status --",
        "printf x | ps -",
    ] {
        assert!(host::passive_eligible(text, true, false), "missed {text}");
        assert!(flag_help::context(text).is_some());
        assert!(!host::passive_eligible(text, false, false));
        assert!(!host::passive_eligible(text, true, true));
    }
    assert!(flag_help::context("cat -- -filename").is_none());
}
#[test]
fn ps_and_ls_use_installed_help_without_inference_or_staging() {
    for (text, expected) in [
        ("ps -", "all processes"),
        ("ps -f", "full-format"),
        ("ps --so", "sort order"),
        ("ls --hum", "human-readable"),
    ] {
        let answer =
            worker::process(&request(text), |_| panic!("flag help must not call Qwen")).unwrap();
        assert!(
            answer.response.explanation.unwrap().contains(expected),
            "missing {expected}"
        );
        assert!(answer.source.contains("/usr/bin/"));
        assert!(answer.validation.is_none());
    }
}
#[test]
fn descriptions_follow_multiline_help_and_short_clusters() {
    let docs = "Source: fixture\n -e   all processes\n -f\n      full format\n --sort <key>\n      choose sorting key\n --signal <n>  signal number";
    let cluster = flag_help::describe("ps", "-ef", docs);
    assert!(cluster.contains("all processes"));
    assert!(cluster.contains("full format"));
    let long = flag_help::describe("ps", "--so", docs);
    assert!(long.contains("choose sorting key"));
    assert!(!long.contains("signal number"));
    assert!(flag_help::describe("ps", "--invented", docs).contains("No documented option"));
}
#[test]
fn unknown_programs_get_an_honest_local_documentation_limit() {
    let answer = worker::process(&request("cayman_nonexistent_3298 -"), |_| {
        panic!("do not invent flags")
    })
    .unwrap();
    assert!(answer
        .response
        .explanation
        .unwrap()
        .contains("No installed flag documentation"));
    assert!(answer.validation.is_none());
}
