//! Host boundary: OS facts, trusted executable resolution, bounded help probes.
use anyhow::{bail, Result};
use std::{
    io::Read,
    path::{Path, PathBuf},
    process::{Command, Stdio},
    time::{Duration, Instant},
};
pub trait HostPlatform: Sync {
    fn id(&self) -> &'static str;
    fn detect(&self) -> crate::command_validation::Host;
    fn executable(&self, name: &str) -> Option<PathBuf>;
    fn probe(&self, name: &str, args: &[&str]) -> Result<String>;
}
pub struct Linux;
impl HostPlatform for Linux {
    fn id(&self) -> &'static str {
        "linux"
    }
    fn detect(&self) -> crate::command_validation::Host {
        crate::command_validation::Host::from_os_release(
            &std::fs::read_to_string("/etc/os-release").unwrap_or_default(),
        )
    }
    fn executable(&self, name: &str) -> Option<PathBuf> {
        use std::os::unix::fs::PermissionsExt;
        if name.contains('/') {
            return None;
        }
        ["/usr/bin", "/bin"]
            .iter()
            .map(|dir| Path::new(dir).join(name))
            .find(|path| {
                std::fs::metadata(path)
                    .is_ok_and(|m| m.is_file() && m.permissions().mode() & 0o111 != 0)
            })
    }
    fn probe(&self, name: &str, args: &[&str]) -> Result<String> {
        linux_probe(name, args)
    }
}
pub fn local() -> &'static dyn HostPlatform {
    &Linux
}

/// A changed executable invalidates help evidence after package upgrades.
pub fn command_fingerprint(name: &str) -> String {
    let Some(path) = local().executable(name) else {
        return "missing".into();
    };
    let metadata = std::fs::metadata(&path).ok();
    format!(
        "{}:{:?}:{:?}",
        path.display(),
        metadata.as_ref().map(|m| m.len()),
        metadata.and_then(|m| m.modified().ok())
    )
}
fn linux_probe(exe: &str, args: &[&str]) -> Result<String> {
    let mut output = tempfile::tempfile()?;
    let mut command = Command::new(format!("/usr/bin/{exe}"));
    use std::os::unix::process::CommandExt;
    command
        .args(args)
        .current_dir("/")
        .env_clear()
        .env("PATH", "/usr/bin:/bin")
        .env("LC_ALL", "C")
        .env("TERM", "dumb")
        .env("PAGER", "cat")
        .env("CLOUDSDK_PAGER", "cat")
        .env("GH_PAGER", "cat")
        .env("CLOUDSDK_CORE_DISABLE_PROMPTS", "1")
        .stdin(Stdio::null())
        .stdout(output.try_clone()?)
        .stderr(Stdio::null())
        .process_group(0);
    // SAFETY: only async-signal-safe setrlimit runs between fork and exec.
    unsafe {
        command.pre_exec(|| {
            let limit = libc::rlimit {
                rlim_cur: 65536,
                rlim_max: 65536,
            };
            if libc::setrlimit(libc::RLIMIT_FSIZE, &limit) != 0 {
                return Err(std::io::Error::last_os_error());
            }
            Ok(())
        });
    }
    let mut child = command.spawn()?;
    // Avoid a process-global SIGCHLD handler competing with GTK/model children.
    let deadline = Instant::now() + Duration::from_secs(2);
    let status = loop {
        if let Some(status) = child.try_wait()? {
            break Some(status);
        }
        if Instant::now() >= deadline {
            break None;
        }
        std::thread::sleep(Duration::from_millis(10));
    };
    // Include any descendants a help wrapper may have created in cleanup.
    unsafe {
        libc::kill(-(child.id() as i32), libc::SIGKILL);
    }
    if status.is_none() {
        let _ = child.wait();
        bail!("Documentation probe timed out");
    }
    if !status.unwrap().success() {
        bail!("Documentation probe failed");
    }
    use std::io::{Seek, SeekFrom};
    output.seek(SeekFrom::Start(0))?;
    let mut result = String::new();
    output.take(65536).read_to_string(&mut result)?;
    Ok(result)
}

pub fn evidence_key(name: &str) -> String {
    let epoch = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
        / 300;
    format!("{}:{epoch}", command_fingerprint(name))
}
