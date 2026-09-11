use anyhow::{bail, Result};
use std::{
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    os::unix::{
        ffi::OsStrExt,
        fs::{FileTypeExt, OpenOptionsExt},
    },
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
pub struct EventReader {
    pipe: File,
    nonce: String,
    sequence: u64,
    pending: Vec<u8>,
}
impl EventReader {
    pub fn create(dir: &Path) -> Result<Self> {
        let path = dir.join("events");
        let cpath = std::ffi::CString::new(path.as_os_str().as_bytes())?;
        // SAFETY: valid NUL terminated path; kernel creates a private bounded FIFO.
        if unsafe { libc::mkfifo(cpath.as_ptr(), 0o600) } != 0 {
            return Err(std::io::Error::last_os_error().into());
        }
        let pipe = OpenOptions::new()
            .read(true)
            .write(true)
            .custom_flags(libc::O_NONBLOCK | libc::O_NOFOLLOW)
            .open(&path)?;
        if !pipe.metadata()?.file_type().is_fifo() {
            bail!("Invalid event channel");
        }
        let mut random = [0; 32];
        File::open("/dev/urandom")?.read_exact(&mut random)?;
        let nonce = random
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect::<String>();
        fs::write(dir.join("nonce"), format!("{nonce}\n"))?;
        Ok(Self {
            pipe,
            nonce,
            sequence: 0,
            pending: Vec::new(),
        })
    }
    pub fn poll(&mut self, _path: &Path) -> Result<Vec<ShellEvent>> {
        let mut bytes = [0; 8192];
        match self.pipe.read(&mut bytes) {
            Ok(count) => self.pending.extend_from_slice(&bytes[..count]),
            Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => {}
            Err(e) => return Err(e.into()),
        }
        let mut result = Vec::new();
        loop {
            let ends: Vec<_> = self
                .pending
                .iter()
                .enumerate()
                .filter(|(_, b)| **b == 0)
                .take(6)
                .map(|(i, _)| i)
                .collect();
            if ends.len() < 6 {
                break;
            }
            if ends[5] >= 4096 {
                bail!("Oversized shell integration record");
            }
            let mut start = 0;
            let fields: Vec<_> = ends
                .iter()
                .map(|end| {
                    let s = std::str::from_utf8(&self.pending[start..*end]).map(str::to_owned);
                    start = end + 1;
                    s
                })
                .collect();
            self.pending.drain(..start);
            let fields = fields
                .into_iter()
                .collect::<std::result::Result<Vec<_>, _>>()?;
            let sequence: u64 = fields[1].parse()?;
            if fields[0] != self.nonce || sequence != self.sequence + 1 {
                bail!("Unauthenticated or out-of-order shell event");
            }
            self.sequence = sequence;
            if fields[2] == "overflow" {
                bail!("Shell input or directory exceeds the integration limit; open a new tab to resume assistance");
            }
            if !["prompt", "start", "request", "input", "staged"].contains(&fields[2].as_str()) {
                bail!("Unknown shell event");
            }
            result.push(ShellEvent {
                kind: fields[2].clone(),
                status: fields[3].parse()?,
                cwd: fields[4].clone(),
                text: fields[5].clone(),
            });
        }
        if self.pending.len() > 4096 {
            self.pending.clear();
            bail!("Oversized shell integration record");
        }
        Ok(result)
    }
}

/// A staged command is data read by a Readline widget. It is never evaluated,
/// sourced, or sent to the PTY as command bytes. Enter is a separate user action.
pub fn write_stage(
    dir: &Path,
    command: &str,
    expected_input: &str,
    expected_cwd: &str,
) -> Result<()> {
    crate::host::assess_risk(command, false, "")?;
    if expected_input.contains(['\n', '\r', '\0']) {
        bail!("Cannot replace a multiline input");
    }
    if expected_cwd.chars().any(char::is_control) {
        bail!("Cannot stage in a directory with control characters");
    }
    let mut file = tempfile::NamedTempFile::new_in(dir)?;
    write!(file, "{expected_cwd}\n{expected_input}\n{command}\n")?;
    file.persist(dir.join("stage"))?;
    Ok(())
}

pub const BASH_INTEGRATION: &str = include_str!("../resources/bash-integration.bash");
