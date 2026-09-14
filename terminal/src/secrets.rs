//! Shared detection for model inputs, responses and the final staging gate.
use regex::Regex;
use std::{borrow::Cow, sync::LazyLock};

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
    const NEEDLE: &[u8] = b"PRIVATEKEY-----";
    let mut matched = 0;
    for c in text.chars().filter(|c| !c.is_whitespace()) {
        if c == char::from(NEEDLE[matched]) {
            matched += 1;
            if matched == NEEDLE.len() {
                return true;
            }
        } else {
            matched = usize::from(c == 'P');
        }
    }
    false
}

pub fn contains(text: &str) -> bool {
    private_key(text) || PATTERNS.iter().any(|p| p.is_match(text))
}

pub fn redact(text: &str) -> String {
    redact_cow(text).into_owned()
}

pub(crate) fn redact_cow(text: &str) -> Cow<'_, str> {
    if private_key(text) {
        return "[private key material withheld]".into();
    }
    let mut result = Cow::Borrowed(text);
    for pattern in PATTERNS.iter() {
        if let Cow::Owned(replaced) = pattern.replace_all(result.as_ref(), "[secret redacted]") {
            result = Cow::Owned(replaced);
        }
    }
    result
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

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn clean_text_is_borrowed_and_key_detection_preserves_whitespace_semantics() {
        assert!(matches!(
            redact_cow("ordinary compiler output"),
            Cow::Borrowed(_)
        ));
        for text in [
            "PRIVATEKEY-----",
            "P R I V A T E\nK E Y - - - - -",
            "PPRIVATEKEY-----",
        ] {
            assert!(private_key(text));
        }
        assert!(!private_key("PRIVATEKEY----"));
        assert_eq!(redact("password=synthetic"), "[secret redacted]");
    }
}
