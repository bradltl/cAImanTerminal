use caiman_terminal::{
    alpha_policy::HostFacts,
    context::Session,
    host,
    worker::{self, Request},
};
use proptest::prelude::*;
use std::{
    process::Command,
    sync::{atomic::AtomicU64, Arc},
};

fn level(command: &str) -> u8 {
    match host::assess_risk(command, false, "") {
        Err(_) => 3,
        Ok(v) => match v.risk {
            host::Risk::Normal => 0,
            host::Risk::Caution => 1,
            host::Risk::Elevated => 2,
        },
    }
}
#[test]
fn unicode_never_reaches_the_native_bash_scanner() {
    // Seed 18 reached native isdigit(U+5635B), which segfaulted in the debugger.
    // Retain the original input and the reduced unsafe lookahead class.
    for command in [
        "{\u{5635b}燡{🕴:_\u{49a2e}",
        "{\u{5635b}",
        "echo 'café'",
        "ls ./🦀",
    ] {
        assert!(host::parse_commands(command).is_err());
    }
    assert!(host::parse_commands("echo 'ascii data'").is_ok());
}
proptest! {
    #![proptest_config(ProptestConfig::with_cases(512))]
    #[test]
    fn arbitrary_input_cannot_escape_staging_controls(candidate in ".{0,256}") {
        let mut session = Session::new(1, "/tmp".into());
        session.at_prompt = true;
        let req = Request { session, text: candidate.clone(), ticket: 0, cancellation: Arc::new(AtomicU64::new(0)), passive: false };
        let trace = worker::check_candidate(&req, &candidate, &HostFacts::local());
        if trace.stageable {
            prop_assert!(!candidate.chars().any(char::is_control));
            prop_assert!(host::parse_commands(&candidate).is_ok());
            prop_assert!(level(&candidate) < 3);
        }
        if level(&candidate) == 3 { prop_assert!(!trace.stageable); }
    }
    #[test]
    fn adding_pipeline_stage_never_reduces_risk(
        a in prop::sample::select(vec!["ls", "sudo ls", "rm ./file", "cat /etc/shadow", "git status", "dd if=/dev/zero"]),
        b in prop::sample::select(vec!["ls", "cat -n -", "sh", "xargs sh", "rm ./file", "sudo ls"])
    ) {
        let pipeline = format!("{a} | {b}");
        prop_assert!(level(&pipeline) >= level(a).max(level(b)));
    }
    #[test]
    fn submission_and_wrapper_suffixes_never_stage(
        prefix in "[a-z]{1,16}",
        suffix in prop::sample::select(vec!["\r", "\n", "\x1b[200~", " && sh -c id", " $(id)", " `id`", " > out", " <<EOF"])
    ) {
        let command = format!("{prefix}{suffix}");
        prop_assert!(host::parse_commands(&command).is_err());
    }
    #[test]
    fn bash_parse_only_and_inert_tokenization_agree(words in prop::collection::vec("[a-zA-Z0-9 ;|_-]{1,20}", 1..8)) {
        let quoted = shlex::try_join(words.iter().map(String::as_str)).unwrap();
        let command = format!("echo {quoted}");
        let parsed = host::parse_commands(&command).unwrap();
        prop_assert_eq!(&parsed[0][1..], words.as_slice());
        // -n performs syntax checking only, not candidate execution.
        let status = Command::new("/bin/bash").args(["--noprofile", "--norc", "-n", "-c", &command]).env_clear().status().unwrap();
        prop_assert!(status.success());
        // A fixed printf script sees only independently generated inert argv.
        let output = Command::new("/bin/bash").args(["--noprofile", "--norc", "-c", "printf '%s\\0' \"$@\"", "fixture"]).args(&words).env_clear().output().unwrap();
        let decoded: Vec<_> = output.stdout.split(|b| *b == 0).filter(|b| !b.is_empty()).map(|b| String::from_utf8(b.to_vec()).unwrap()).collect();
        prop_assert_eq!(decoded, words);
    }
}
