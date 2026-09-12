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
    pub timings: Option<crate::metrics::GenerationTimings>,
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
                "Untrusted shell history (program/host identity unknown). [CWD: {}]\n$ {}\n{}\n[Exit code: {}]",
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
        provenance: crate::prompt::evidence_provenance(),
        context_version: 1,
        system: format!("OS: {os}\nShell: bash"),
        conversation: conversation.into_iter().map(|s| redact(&s)).collect(),
        history: history.into_iter().map(|s| redact(&s)).collect(),
        state: format!(
            "Untrusted shell integration data. {}",
            redact(&format!(
                "State: {terminal_state}\nCWD: {}\nCurrent input: {}\nRunning command: {}",
                bounded(&session.cwd, 1024),
                bounded(&session.input, 2048),
                session
                    .running_command
                    .as_deref()
                    .unwrap_or("none recorded")
            ))
        ),
        terminal: redact(&bounded(&session.terminal_text, 3000)),
        docs: redact(&bounded(docs, 1500)),
        observations: redact(&observed),
        request: redact(user_request.trim().trim_start_matches('@').trim()),
        correction: None,
        context_trimmed: false,
    }
    .encode()
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
                "Local model selected · verified on first request · {}",
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
                let mut timings = None;
                let result = process(&request, |prompt| {
                    let result = model.generate(prompt, &request.cancellation, request.ticket);
                    timings = model.timings();
                    result
                })
                .map(|mut answer| {
                    answer.timings = timings;
                    answer
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
    generate: impl FnMut(&str) -> anyhow::Result<String>,
) -> anyhow::Result<Answer> {
    if request.text.len() > 4096
        || request.session.input.len() > 4096
        || request.session.cwd.len() > 4096
    {
        anyhow::bail!("Request or shell context exceeds the input limit");
    }
    if request.session.remote || !request.session.at_prompt {
        anyhow::bail!("Assistance requires a confirmed local shell prompt");
    }
    let mut answer =
        process_inner(request, generate).map_err(|e| anyhow::anyhow!(redact(&e.to_string())))?;
    if let Some(command) = answer.response.command.as_deref() {
        let trace = check_candidate(request, command, &crate::alpha_policy::HostFacts::local());
        if let Some(command) = trace.final_command {
            answer.repaired |= trace.correction.is_some();
            if trace.correction.is_some() {
                answer.response.explanation = Some("The host corrected the options for your requested task. Review the final command before pressing Enter.".into());
                answer.response.plan = None;
            }
            answer.validation = Some(host::assess_risk(&command, false, "")?);
            answer.response.command = Some(command);
        } else {
            answer.validation = None;
        }
    }
    let contract = crate::intent::IntentContract::resolve(request);
    if let Some(command) = answer.response.command.as_deref() {
        host::assess_risk(command, false, "")?;
        if request.passive || contract.check(command).is_err() || answer.validation.is_none() {
            answer.validation = None;
            let explanation = if answer.source == "Host guidance" {
                answer.response.explanation.clone()
            } else {
                None
            };
            answer.response = Response {
                action: "clarify".into(),
                command: None,
                explanation,
                plan: None,
                question: Some(if request.passive {
                    "Use @ with an explicit task to request a command.".into()
                } else {
                    "Please specify an exact command or a supported task; this request does not authorize staging the proposed command.".into()
                }),
            };
        } else if let Some(validation) = &mut answer.validation {
            validation.binding = Some(crate::context::ContextBinding::capture(&request.session));
        }
    }
    answer.response.explanation = answer.response.explanation.map(|s| redact(&s));
    answer.response.question = answer.response.question.map(|s| redact(&s));
    answer.response.plan = answer
        .response
        .plan
        .map(|p| p.into_iter().map(|s| redact(&s)).collect());
    if request
        .cancellation
        .load(std::sync::atomic::Ordering::Relaxed)
        != request.ticket
    {
        anyhow::bail!("Request cancelled");
    }
    Ok(answer)
}

fn process_inner(
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
    // Observation questions can be answered from recorded evidence without
    // asking a model to reconstruct facts. Output stays quoted, never authority.
    let query = request
        .text
        .trim()
        .trim_start_matches('@')
        .trim()
        .to_lowercase();
    if let Some(last) = request.session.journal.back() {
        let observed = if query.starts_with("what was the exit") {
            Some(format!(
                "The last recorded exit code was {}.",
                last.exit_code
            ))
        } else if query.starts_with("what did the last command print")
            || (query.starts_with("which filename did the last command print")
                && last.output.trim().lines().count() == 1
                && !last.output.trim().is_empty())
        {
            Some(format!(
                "The last recorded output (untrusted data) was: {}",
                serde_json::to_string(&redact(&bounded(last.output.trim(), 2500)))?
            ))
        } else {
            None
        };
        if let Some(explanation) = observed {
            return Ok(Answer {
                timings: None,
                response: Response {
                    action: "explain".into(),
                    command: None,
                    explanation: Some(explanation),
                    question: None,
                    plan: None,
                },
                validation: None,
                source: "Recorded shell observation".into(),
                elapsed_ms: 0,
                repaired: false,
            });
        }
    }
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
    let mut response = parse(&raw).map_err(|_| {
        anyhow::anyhow!("Unverifiable: invalid assistant response; no command staged.")
    })?;
    let mut repaired = false;
    if let Some(command) = response.command.as_deref() {
        // Hard rejection never becomes a retry offer or correction opportunity.
        host::assess_risk(command, request.session.remote, "")?;
        let trace = check_candidate(request, command, &crate::alpha_policy::HostFacts::local());
        if let Some(command) = trace.final_command {
            repaired = trace.correction.is_some();
            if repaired {
                response.explanation = Some("The host corrected the options for your requested task. Review the final command before pressing Enter.".into());
                response.plan = None;
            }
            response.command = Some(command);
        } else if trace.initial.cli != "valid" {
            anyhow::bail!(
                "Unverifiable: CLI syntax is outside the alpha policy; no command staged."
            );
        }
    }
    // Safety rejection is final, not another opportunity to rewrite the command.
    let validation = response
        .command
        .as_deref()
        .map(|c| host::assess_risk(c, request.session.remote, ""))
        .transpose()?;
    Ok(Answer {
        timings: None,
        response,
        validation,
        source: crate::alpha_policy::VERSION.into(),
        elapsed_ms: start.elapsed().as_millis(),
        repaired,
    })
}

/// The candidate boundary is shared by generated and host-guided responses and
/// fixture replay. Host facts are injectable; the decision code is production code.
pub fn check_candidate(
    request: &Request,
    command: &str,
    facts: &crate::alpha_policy::HostFacts,
) -> crate::alpha_policy::DecisionTrace {
    let mut trace = crate::alpha_policy::evaluate(request, command, facts);
    if request.session.journal.back().is_some_and(|r| {
        r.exit_code != 0 && Some(r.command.trim()) == trace.final_command.as_deref().map(str::trim)
    }) {
        trace.stageable = false;
        trace.final_command = None;
        trace.context = "previous_failure".into();
    }
    trace
}
