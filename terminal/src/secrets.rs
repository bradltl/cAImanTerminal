//! Shared detection for model inputs, responses and the final staging gate.
use regex::Regex;
use std::sync::LazyLock;

static PATTERNS: LazyLock<Vec<Regex>> = LazyLock::new(|| {
    [
        r#"(?i)[\w-]*(?:token|password|passwd|secret|api[_-]?key)[\w-]*\s*(?:[=:]|\s)\s*(?:"[^"]*"|'[^']*'|[^\s,;]+)"#,
        r"(?:gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|glpat-[A-Za-z0-9_-]+|xox[baprs]-[A-Za-z0-9-]+|sk-[A-Za-z0-9_-]{12,}|AKIA[A-Z0-9]{16})",
        r#"(?i)(?:Bearer|Basic)\s+[^\s'"]+"#,
        r"[a-zA-Z][a-zA-Z0-9+.-]*://[^\s/:]+:[^\s/@]+@[^\s]+",
        r"(?:^|\s)-u\s+[^\s:]+:[^\s]+",
        r"(?i)\b(?:mysql|mysqldump|mariadb)\b[^\r\n]*\s-p[^\s]+",
    ].iter().map(|p| Regex::new(p).expect("static secret pattern")).collect()
});

fn private_key(text: &str) -> bool {
    let compact: String = text.chars().filter(|c| !c.is_whitespace()).collect();
    compact.contains("PRIVATEKEY-----")
}

pub fn contains(text: &str) -> bool {
    private_key(text) || PATTERNS.iter().any(|p| p.is_match(text))
}

pub fn redact(text: &str) -> String {
    if private_key(text) {
        return "[private key material withheld]".into();
    }
    PATTERNS.iter().fold(text.to_owned(), |s, p| {
        p.replace_all(&s, "[secret redacted]").into_owned()
    })
}

pub fn check_command(text: &str) -> anyhow::Result<()> {
    if contains(text) || text.contains("[secret redacted]") {
        anyhow::bail!(
            "Credential-bearing commands cannot be staged; use an interactive credential prompt"
        );
    }
    Ok(())
}

/// Report serialization must not expose raw candidates rejected by the gate.
pub fn sanitize_json(value: serde_json::Value) -> serde_json::Value {
    match value {
        serde_json::Value::String(text) => serde_json::Value::String(redact(&text)),
        serde_json::Value::Array(items) => {
            serde_json::Value::Array(items.into_iter().map(sanitize_json).collect())
        }
        serde_json::Value::Object(items) => serde_json::Value::Object(
            items
                .into_iter()
                .map(|(key, value)| (key, sanitize_json(value)))
                .collect(),
        ),
        other => other,
    }
}
