use serde::{Deserialize, Serialize};
use std::collections::VecDeque;

/// The journal is memory-only. Redaction happens at the model boundary, including
/// commands and requests, because secrets can appear anywhere in terminal text.
pub fn redact(text: &str) -> String {
    crate::secrets::redact(text)
}

pub fn bounded(text: &str, chars: usize) -> String {
    let start = text
        .char_indices()
        .rev()
        .nth(chars)
        .map_or(0, |(i, c)| i + c.len_utf8());
    text[start..].to_owned()
}

fn redacted_tail(text: &str, chars: usize) -> String {
    // Detect secrets on the original text: trimming first can remove password=
    // or a PEM header while retaining its value. Borrow clean inputs until the
    // bounded tail is copied, instead of cloning the entire output repeatedly.
    bounded(&crate::secrets::redact_cow(text), chars)
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommandRecord {
    pub command: String,
    pub cwd: String,
    pub exit_code: i32,
    pub output: String,
    pub timestamp: u64,
    pub ai_origin: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContextBinding {
    id: u64,
    revision: u64,
    request_id: u64,
    prompt_generation: u64,
    cwd: String,
    input: String,
    remote: bool,
    at_prompt: bool,
}
impl ContextBinding {
    pub fn capture(session: &Session) -> Self {
        Self {
            id: session.id,
            revision: session.revision,
            request_id: session.request_id,
            prompt_generation: session.prompt_generation,
            cwd: session.cwd.clone(),
            input: session.input.clone(),
            remote: session.remote,
            at_prompt: session.at_prompt,
        }
    }
    pub fn matches(&self, session: &Session) -> bool {
        self == &Self::capture(session) && session.at_prompt && !session.remote
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Session {
    pub id: u64,
    pub cwd: String,
    pub remote: bool,
    pub at_prompt: bool,
    pub revision: u64,
    #[serde(default)]
    pub request_id: u64,
    /// Sequence of the last authenticated original-shell prompt, not OSC state.
    #[serde(default)]
    pub prompt_generation: u64,
    pub input: String,
    /// A bounded, redacted snapshot of this tab's live terminal, captured at request time.
    #[serde(default)]
    pub terminal_text: String,
    #[serde(default)]
    pub running_command: Option<String>,
    pub intent: Option<String>,
    pub journal: VecDeque<CommandRecord>,
    pub conversation: VecDeque<String>,
}
impl Session {
    pub fn new(id: u64, cwd: String) -> Self {
        Self {
            id,
            cwd,
            remote: false,
            at_prompt: false,
            revision: 0,
            request_id: 0,
            prompt_generation: 0,
            input: String::new(),
            terminal_text: String::new(),
            running_command: None,
            intent: None,
            journal: VecDeque::new(),
            conversation: VecDeque::new(),
        }
    }
    pub fn edit(&mut self, input: String) {
        if self.input != input {
            self.revision += 1;
            self.input = input;
        }
    }
    pub fn remember(&mut self, text: String) {
        if let Some(intent) = text.strip_prefix("User: ") {
            if ![
                "continue",
                "explain the error",
                "explain that error",
                "explain this error",
            ]
            .contains(&intent.trim().to_lowercase().as_str())
            {
                self.intent = Some(redacted_tail(intent, 1000));
            }
        }
        self.conversation.push_back(redacted_tail(&text, 1000));
        while self.conversation.len() > 4 {
            self.conversation.pop_front();
        }
    }
    pub fn capture_terminal(&mut self, text: &str, running: Option<&str>) {
        self.terminal_text = redacted_tail(text.trim_end(), 3000);
        self.running_command = running.map(|command| redacted_tail(command, 500));
    }
    pub fn record(&mut self, mut record: CommandRecord) {
        record.cwd = redacted_tail(&record.cwd, 1024);
        record.command = redacted_tail(&record.command, 2048);
        record.output = redacted_tail(&record.output, 2500);
        self.journal.push_back(record);
        while self.journal.len() > 8 {
            self.journal.pop_front();
        }
    }
    pub fn model_context(&self) -> serde_json::Value {
        static OS_RELEASE: std::sync::LazyLock<String> = std::sync::LazyLock::new(|| {
            std::fs::read_to_string("/etc/os-release").unwrap_or_default()
        });
        serde_json::json!({
            "session": self.id, "shell": "bash", "cwd": redact(&self.cwd),
            "environment": if self.remote { "remote; OS and installed tools unknown" } else { "local" },
            "platform": if self.remote { "" } else { OS_RELEASE.as_str() },
            "recent_commands": self.journal.iter().rev().take(3).collect::<Vec<_>>(),
            "conversation": self.conversation,
            "intent": self.intent,
            "terminal_text": redact(&self.terminal_text),
            "input": redact(&self.input),
            "at_prompt": self.at_prompt,
            "running_command": self.running_command.as_deref().map(redact),
        })
    }
}
