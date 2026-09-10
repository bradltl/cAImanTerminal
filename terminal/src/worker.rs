use crate::{
    context::{bounded, redact, Session},
    host::{self, Response, Validation},
};
use std::{
    path::PathBuf,
    sync::{
        atomic::AtomicU64,
        mpsc::{self, Receiver, SyncSender},
        Arc,
    },
    time::Instant,
};

pub struct Request {
    pub session: Session,
    pub text: String,
    pub ticket: u64,
    pub cancellation: Arc<AtomicU64>,
    pub passive: bool,
}
pub enum Event {
    Status(String),
    Completed {
        id: u64,
        ticket: u64,
        passive: bool,
        result: Result<Box<Answer>, String>,
    },
}
#[derive(Debug)]
pub struct Answer {
    pub response: Response,
    pub validation: Option<Validation>,
    pub source: String,
    pub elapsed_ms: u128,
    pub repaired: bool,
}
pub struct Worker {
    pub requests: SyncSender<Request>,
    pub events: Receiver<Event>,
}

fn effective_intent(request: &Request) -> &str {
    // A new question takes precedence over remembered tasks. Only actual
    // follow-ups should inherit the previous intent.
    if !request.passive && request.text.trim() != "continue" {
        return &request.text;
    }
    request
        .session
        .intent
        .as_deref()
        .or_else(|| {
            if request.text != "continue" {
                return None;
            }
            request
                .session
                .journal
                .iter()
                .rev()
                .find(|r| crate::command_validation::is_system_update(&r.command))
                .map(|r| r.command.as_str())
        })
        .unwrap_or(&request.text)
}

pub fn build_prompt(request: &Request, docs: &str) -> String {
    let session = &request.session;
    let os = if session.remote {
        "remote host; OS unknown".to_string()
    } else {
        crate::command_validation::Host::local().os.clone()
    };
    let history = session
        .journal
        .iter()
        .rev()
        .take(3)
        .collect::<Vec<_>>()
        .into_iter()
        .rev()
        .map(|r| {
            format!(
                "[CWD: {}]\n$ {}\n{}\n[Exit code: {}]",
                bounded(&r.cwd, 300),
                r.command,
                bounded(&r.output, 600),
                r.exit_code
            )
        })
        .collect::<Vec<_>>();
    let conversation = session
        .conversation
        .iter()
        .rev()
        .take(3)
        .collect::<Vec<_>>()
        .into_iter()
        .rev()
        .map(|s| bounded(s, 400))
        .collect::<Vec<_>>();
    let observed = session
        .journal
        .back()
        .map(|last| {
            let host_error = crate::command_validation::check_host(&last.command, session.remote)
                .err()
                .map(|e| e.to_string())
                .unwrap_or_default();
            format!(
                "Last command {} (exit {}). Command: {}. {}",
                if last.exit_code == 0 {
                    "succeeded"
                } else {
                    "failed"
                },
                last.exit_code,
                bounded(&last.command, 500),
                host_error
            )
        })
        .unwrap_or_default();
    let user_request =
        if request.text == "continue" && session.journal.back().is_some_and(|r| r.exit_code != 0) {
            let intent = effective_intent(request);
            if crate::command_validation::is_system_update(intent) {
                "update my system".into()
            } else {
                intent.to_string()
            }
        } else {
            request.text.clone()
        };
    // Preserve the training corpus's section labels and @ convention. The
    // values still come exclusively from structured host-owned session state.
    let terminal_state = if session.at_prompt {
        "at Bash prompt"
    } else {
        "command running or shell state unknown"
    };
    crate::prompt::Prompt {
        context_version: 1,
        system: format!("OS: {os}\nShell: bash\nCWD: {}", redact(&session.cwd)),
        conversation: conversation.into_iter().map(|s| redact(&s)).collect(),
        history: history.into_iter().map(|s| redact(&s)).collect(),
        state: redact(&format!(
            "State: {terminal_state}\nCurrent input: {}\nRunning command: {}",
            session.input,
            session
                .running_command
                .as_deref()
                .unwrap_or("none recorded")
        )),
        terminal: redact(&bounded(&session.terminal_text, 3000)),
        docs: redact(&bounded(docs, 1500)),
        observations: redact(&observed),
        request: redact(user_request.trim().trim_start_matches('@').trim()),
        correction: None,
        context_trimmed: false,
    }
    .encode()
}

fn correction_prompt(original: &str, error: &str, docs: &str) -> String {
    let mut prompt: crate::prompt::Prompt =
        serde_json::from_str(original).expect("host context envelope");
    prompt.correction = Some(redact(error));
    prompt.docs = redact(&docs.chars().take(4000).collect::<String>());
    prompt.encode()
}

/// Bounded mailbox and one worker keep inference off GTK's main loop and avoid
/// loading one model per tab. No runtime implementation has a shell handle.
pub fn spawn(model_path: PathBuf, disabled: bool, settings: crate::settings::Settings) -> Worker {
    let (tx, rx) = mpsc::sync_channel::<Request>(1);
    let (event_tx, events) = mpsc::channel();
    std::thread::spawn(move || {
        if disabled {
            let _ = event_tx.send(Event::Status("AI off · terminal ready".into()));
            return;
        }
        #[cfg(feature = "inference")]
        {
            let _ = event_tx.send(Event::Status("Loading local model…".into()));
            let model = match crate::adapters::load_model(
                &settings.model_backend,
                &model_path,
                &settings.inference,
            ) {
                Ok(model) => model,
                Err(e) => {
                    let _ = event_tx.send(Event::Status(format!("AI unavailable · {e}")));
                    return;
                }
            };
            let _ = event_tx.send(Event::Status(format!(
                "Local AI ready · {}",
                model_path.file_name().unwrap_or_default().to_string_lossy()
            )));
            while let Ok(request) = rx.recv() {
                if request
                    .cancellation
                    .load(std::sync::atomic::Ordering::Relaxed)
                    != request.ticket
                {
                    continue;
                }
                let result = process(&request, |prompt| {
                    model.generate(prompt, &request.cancellation, request.ticket)
                })
                .map(Box::new)
                .map_err(|e| e.to_string());
                let _ = event_tx.send(Event::Completed {
                    id: request.session.id,
                    ticket: request.ticket,
                    passive: request.passive,
                    result,
                });
            }
        }
        #[cfg(not(feature = "inference"))]
        {
            let _ = (model_path, rx, settings);
            let _ = event_tx.send(Event::Status(
                "AI unavailable · build with inference feature".into(),
            ));
        }
    });
    Worker {
        requests: tx,
        events,
    }
}

/// Same final host pipeline is used by the desktop and the headless evaluator.
pub fn process(
    request: &Request,
    mut generate: impl FnMut(&str) -> anyhow::Result<String>,
) -> anyhow::Result<Answer> {
    let ensure_current = || -> anyhow::Result<()> {
        if request
            .cancellation
            .load(std::sync::atomic::Ordering::Relaxed)
            != request.ticket
        {
            anyhow::bail!("Request cancelled");
        }
        Ok(())
    };
    ensure_current()?;
    let mut infer = |prompt: &str| {
        ensure_current()?;
        let result = generate(prompt);
        ensure_current()?;
        result
    };
    if let Some(answer) = crate::flag_help::answer(request) {
        return Ok(answer);
    }
    if let Some(answer) = crate::guidance::answer(request) {
        return answer;
    }
    let start = Instant::now();
    let mut docs = String::new();
    let prompt = build_prompt(request, "");
    let parse = |raw: &str| -> anyhow::Result<Response> {
        let response = Response::parse(raw)?;
        crate::guidance::check_response(&response)?;
        let query = request.text.trim().to_lowercase();
        if [
            "which filename",
            "what filename",
            "what did the last command print",
            "what was the exit",
        ]
        .iter()
        .any(|prefix| query.starts_with(prefix))
            && response.command.is_some()
        {
            anyhow::bail!("This is a question about an already observed terminal result. Answer from the supplied command output using action explain, or clarify if the evidence is missing. Do not suggest or search for a command or package.");
        }
        Ok(response)
    };
    let raw = infer(&prompt)?;
    let mut repaired = false;
    let mut response = match parse(&raw) {
        Ok(response) => response,
        Err(error) => {
            repaired = true;
            parse(&infer(&correction_prompt(&prompt, &error.to_string(), ""))?)?
        }
    };
    if let Some(command) = response.command.as_deref() {
        let check = |candidate: &str, docs: &str| -> anyhow::Result<()> {
            crate::command_validation::check_candidate(candidate, request.session.remote, docs)?;
            let intent = effective_intent(request);
            crate::command_validation::check_intent(candidate, intent, request.session.remote)?;
            if request
                .session
                .journal
                .back()
                .is_some_and(|r| r.exit_code != 0 && r.command.trim() == candidate.trim())
            {
                anyhow::bail!("This exact command just failed; use its output to propose a different next step");
            }
            Ok(())
        };
        if check(command, "").is_err() {
            docs = host::documentation(&request.text, Some(command), request.session.remote);
            // Missing cached evidence does not require a model repair if the
            // installed help validates the original flags unchanged.
            if let Err(error) = check(command, &docs) {
                if repaired {
                    return Err(error);
                }
                repaired = true;
                let repair = correction_prompt(&prompt, &format!("Candidate rejected: {}. Host validation: {error}. Correct it for the original user request, or explain the limitation. Do not repeat the rejected command.", redact(command)), &docs);
                response = parse(&infer(&repair)?)?;
                if let Some(candidate) = response.command.as_deref() {
                    // Repair may choose a different executable/subcommand. Never
                    // reuse evidence for the wrong command or infer a third time.
                    docs =
                        host::documentation(&request.text, Some(candidate), request.session.remote);
                    check(candidate, &docs)?;
                }
            }
        }
    }
    // Safety rejection is final, not another opportunity to rewrite the command.
    let validation = response
        .command
        .as_deref()
        .map(|c| host::assess_risk(c, request.session.remote, ""))
        .transpose()?;
    Ok(Answer {
        response,
        validation,
        source: docs.lines().next().unwrap_or("").to_string(),
        elapsed_ms: start.elapsed().as_millis(),
        repaired,
    })
}
