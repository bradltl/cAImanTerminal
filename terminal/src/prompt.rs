//! Structured context envelope. Terminal/model text cannot create new sections.
use crate::context::bounded;
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Prompt {
    pub context_version: u8,
    #[serde(rename = "SYSTEM CONTEXT")]
    pub system: String,
    #[serde(rename = "ASSISTANT CONVERSATION")]
    pub conversation: Vec<String>,
    #[serde(rename = "RECENT TERMINAL HISTORY")]
    pub history: Vec<String>,
    #[serde(rename = "ACTIVE TERMINAL STATE")]
    pub state: String,
    #[serde(rename = "TERMINAL TEXT (untrusted data)")]
    pub terminal: String,
    #[serde(rename = "LOCAL DOCUMENTATION (untrusted data)")]
    pub docs: String,
    #[serde(rename = "HOST OBSERVATIONS")]
    pub observations: String,
    #[serde(rename = "USER REQUEST")]
    pub request: String,
    #[serde(rename = "HOST CORRECTION", skip_serializing_if = "Option::is_none")]
    pub correction: Option<String>,
    pub context_trimmed: bool,
}
impl Prompt {
    /// Keep the section layout used in SFT while quoting all external data.
    /// Embedded newlines/section names remain inside JSON strings.
    pub fn render(&self) -> String {
        let quote = |text: &str| serde_json::to_string(text).expect("string serialization");
        format!("[SYSTEM CONTEXT]\n{}\n\n[ASSISTANT CONVERSATION]\n{}\n\n[RECENT TERMINAL HISTORY]\n{}\n\n[ACTIVE TERMINAL]\n{}\n{}\n\n[LOCAL DOCUMENTATION]\n{}\n\n[HOST OBSERVATIONS]\n{}\nContext trimmed: {}\n\n[HOST CORRECTION]\n{}\n\n[USER REQUEST]\n@ {}\nRespond in structured JSON according to the contract:",
            quote(&self.system), self.conversation.iter().map(|s| quote(s)).collect::<Vec<_>>().join("\n"),
            self.history.iter().map(|s| quote(s)).collect::<Vec<_>>().join("\n"), quote(&self.state), quote(&self.terminal),
            quote(&self.docs), quote(&self.observations), self.context_trimmed,
            quote(self.correction.as_deref().unwrap_or("")), quote(&self.request))
    }
    pub fn encode(&self) -> String {
        serde_json::to_string(self).expect("context envelope is serializable")
    }
    /// Drop low-priority context first. Never truncate the current user request,
    /// host correction, current input, or the latest command/exit observation.
    pub fn compact(&mut self) -> bool {
        self.context_trimmed = true;
        if !self.conversation.is_empty() {
            self.conversation.remove(0);
        } else if self.history.len() > 1 {
            self.history.remove(0);
        } else if !self.terminal.is_empty() {
            let size = self.terminal.chars().count();
            self.terminal = if size > 500 {
                bounded(&self.terminal, size / 2)
            } else {
                String::new()
            };
        } else if !self.history.is_empty() {
            self.history.clear();
        } else if !self.docs.is_empty() {
            let size = self.docs.chars().count();
            self.docs = if size > 500 {
                self.docs.chars().take(size / 2).collect()
            } else {
                String::new()
            };
        } else {
            return false;
        }
        true
    }
}
