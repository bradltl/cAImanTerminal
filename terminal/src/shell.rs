use anyhow::{bail, Result};
use std::{
    fs::{self, File},
    io::{Read, Seek, SeekFrom},
    path::Path,
};

#[derive(Debug, PartialEq, Eq)]
pub struct ShellEvent {
    pub kind: String,
    pub status: i32,
    pub cwd: String,
    pub text: String,
}

/// NUL-delimited records preserve tabs/newlines in paths and command text.
#[derive(Default)]
pub struct EventReader {
    offset: u64,
    pending: Vec<u8>,
}
impl EventReader {
    pub fn poll(&mut self, path: &Path) -> Result<Vec<ShellEvent>> {
        let mut file = File::open(path)?;
        file.seek(SeekFrom::Start(self.offset))?;
        let count = file.take(65536).read_to_end(&mut self.pending)?;
        self.offset += count as u64;
        let mut result = Vec::new();
        loop {
            let ends: Vec<_> = self
                .pending
                .iter()
                .enumerate()
                .filter(|(_, b)| **b == 0)
                .take(4)
                .map(|(i, _)| i)
                .collect();
            if ends.len() < 4 {
                break;
            }
            let mut start = 0;
            let fields: Vec<_> = ends
                .iter()
                .map(|end| {
                    let s = String::from_utf8_lossy(&self.pending[start..*end]).into_owned();
                    start = end + 1;
                    s
                })
                .collect();
            self.pending.drain(..start);
            result.push(ShellEvent {
                kind: fields[0].clone(),
                status: fields[1].parse().unwrap_or(-1),
                cwd: fields[2].clone(),
                text: fields[3].clone(),
            });
        }
        if self.pending.len() > 65536 {
            self.pending.clear();
            bail!("Oversized shell integration record");
        }
        Ok(result)
    }
}

/// A staged command is data read by a Readline widget. It is never evaluated,
/// sourced, or sent to the PTY as command bytes. Enter is a separate user action.
pub fn write_stage(dir: &Path, command: &str, expected_input: &str) -> Result<()> {
    if command.is_empty() || command.len() > 4096 || command.chars().any(char::is_control) {
        bail!("Only a single printable command can be staged");
    }
    if expected_input.contains(['\n', '\r', '\0']) {
        bail!("Cannot replace a multiline input");
    }
    fs::write(
        dir.join("stage.tmp"),
        format!("{expected_input}\n{command}\n"),
    )?;
    fs::rename(dir.join("stage.tmp"), dir.join("stage"))?;
    Ok(())
}

pub const BASH_INTEGRATION: &str = include_str!("../resources/bash-integration.bash");
