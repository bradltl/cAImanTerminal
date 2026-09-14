//! Incremental framing only. The production response parser remains authoritative.
#[derive(Default)]
pub(crate) struct JsonObject {
    started: bool,
    depth: usize,
    string: bool,
    escaped: bool,
    complete: bool,
}
impl JsonObject {
    pub fn push(&mut self, piece: &str) -> anyhow::Result<bool> {
        for byte in piece.bytes() {
            if self.complete {
                anyhow::ensure!(byte.is_ascii_whitespace(), "Trailing model response data");
            } else if self.string {
                if self.escaped {
                    self.escaped = false;
                } else if byte == b'\\' {
                    self.escaped = true;
                } else if byte == b'"' {
                    self.string = false;
                }
            } else if !self.started {
                if byte.is_ascii_whitespace() {
                    continue;
                }
                anyhow::ensure!(byte == b'{', "Model response must be an object");
                self.started = true;
                self.depth = 1;
            } else {
                match byte {
                    b'"' => self.string = true,
                    b'{' | b'[' => self.depth += 1,
                    b'}' | b']' => {
                        self.depth -= 1;
                        self.complete = self.depth == 0;
                    }
                    _ => (),
                }
            }
        }
        Ok(self.complete)
    }
}

pub(crate) fn validate_complete(text: String) -> anyhow::Result<String> {
    crate::host::Response::parse_assistant(&text)
        .map_err(|_| anyhow::anyhow!("Unverifiable: model completed an invalid response"))?;
    Ok(text)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn quotes_escapes_nested_data_and_chunk_boundaries_do_not_end_the_root() {
        let text = r#"{"action":"explain","explanation":"a } [ \\" b","plan":["nested { data"]}"#;
        // Generate JSON to avoid hand-written escaping being the test oracle.
        let text = serde_json::json!({"action":"explain","explanation":text,"plan":["{", "}"]})
            .to_string();
        let mut frame = JsonObject::default();
        for (index, c) in text.chars().enumerate() {
            assert_eq!(
                frame.push(&c.to_string()).unwrap(),
                index + 1 == text.chars().count()
            );
        }
        assert!(validate_complete(text).is_ok());
        assert!(frame.push(" {}").is_err());
    }
    #[test]
    fn closed_object_is_not_a_valid_response_until_required_fields_pass() {
        for text in [
            r#"{"action":"suggest_command"}"#,
            r#"{"action":"execute","command":"ls"}"#,
            r#"{"action":"suggest_command","command":"ls"}"#,
            r#"{"action":"suggest_command","command":"ls","explanation":"  "}"#,
            "{",
            "{} {}",
        ] {
            assert!(validate_complete(text.into()).is_err());
        }
        assert!(validate_complete(r#"{"action":"suggest_command","command":"ls","explanation":"Lists the current directory entries."}"#.into()).is_ok());
        assert!(JsonObject::default().push("[]").is_err());
    }
}
