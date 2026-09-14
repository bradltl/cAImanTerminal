//! Supervised native inference. The child has no PTY handle; cancellation and
//! deadlines kill/reap it even when native decoding does not return.
use anyhow::{bail, Context, Result};
use std::{
    cell::RefCell,
    io::{BufRead, BufReader, Read, Write},
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    sync::{
        atomic::{AtomicU64, Ordering},
        mpsc::{self, Receiver},
    },
    time::{Duration, Instant},
};

struct Running {
    child: Child,
    replies: Receiver<Result<String, String>>,
}
impl Drop for Running {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}
pub struct ProcessModel {
    timings: RefCell<Option<crate::metrics::GenerationTimings>>,
    path: PathBuf,
    options: crate::settings::Inference,
    running: RefCell<Option<Running>>,
}
impl ProcessModel {
    pub fn new(path: &Path, options: &crate::settings::Inference) -> Result<Self> {
        options.validate()?;
        Ok(Self {
            timings: RefCell::new(None),
            path: path.canonicalize()?,
            options: options.clone(),
            running: RefCell::new(None),
        })
    }
    fn start(&self) -> Result<Running> {
        use std::os::unix::process::CommandExt;
        let mut command = Command::new(std::env::current_exe()?);
        command
            .arg("--model-worker")
            .arg("--model")
            .arg(&self.path)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null());
        // SAFETY: no allocation or locks after fork. The helper dies with its parent.
        let parent = unsafe { libc::getpid() };
        unsafe {
            command.pre_exec(move || {
                if libc::prctl(libc::PR_SET_PDEATHSIG, libc::SIGKILL) != 0
                    || libc::getppid() != parent
                {
                    return Err(std::io::Error::other("Model supervisor disappeared"));
                }
                Ok(())
            });
        }
        let mut child = command.spawn()?;
        let stdout = child.stdout.take().context("Missing model output pipe")?;
        let (tx, replies) = mpsc::sync_channel(1);
        std::thread::spawn(move || {
            let mut reader = BufReader::new(stdout);
            loop {
                let mut line = String::new();
                let result = reader.by_ref().take(32769).read_line(&mut line);
                match result {
                    Ok(0) => break,
                    Ok(_) if line.len() <= 32768 && line.ends_with('\n') => {
                        if tx.send(Ok(line)).is_err() {
                            break;
                        }
                    }
                    _ => {
                        let _ = tx.send(Err("Invalid or oversized model IPC response".into()));
                        break;
                    }
                }
            }
        });
        let mut running = Running { child, replies };
        writeln!(
            running.child.stdin.as_mut().unwrap(),
            "{}",
            serde_json::to_string(&self.options)?
        )?;
        Ok(running)
    }
    fn receive(
        &self,
        running: &Running,
        cancellation: &AtomicU64,
        ticket: u64,
        deadline: Instant,
    ) -> Result<String> {
        loop {
            if cancellation.load(Ordering::Relaxed) != ticket {
                bail!("Request cancelled");
            }
            if Instant::now() >= deadline {
                bail!("Model process exceeded its deadline");
            }
            match running.replies.recv_timeout(Duration::from_millis(20)) {
                Ok(Ok(line)) => return Ok(line),
                Ok(Err(error)) => bail!("{error}"),
                Err(mpsc::RecvTimeoutError::Timeout) => {}
                Err(_) => bail!("Model process exited unexpectedly"),
            }
        }
    }
    fn send(
        &self,
        running: &mut Running,
        message: &str,
        cancellation: &AtomicU64,
        ticket: u64,
        deadline: Instant,
    ) -> Result<()> {
        use std::os::fd::AsRawFd;
        let input = running.child.stdin.as_mut().context("Model input closed")?;
        let fd = input.as_raw_fd();
        // SAFETY: valid owned pipe fd; nonblocking writes are deadline supervised.
        unsafe {
            let flags = libc::fcntl(fd, libc::F_GETFL);
            if flags < 0 || libc::fcntl(fd, libc::F_SETFL, flags | libc::O_NONBLOCK) < 0 {
                return Err(std::io::Error::last_os_error().into());
            }
        }
        let mut bytes = message.as_bytes();
        while !bytes.is_empty() {
            if cancellation.load(Ordering::Relaxed) != ticket {
                bail!("Request cancelled");
            }
            if Instant::now() >= deadline {
                bail!("Model input exceeded its deadline");
            }
            match input.write(bytes) {
                Ok(0) => bail!("Model input closed"),
                Ok(n) => bytes = &bytes[n..],
                Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => {
                    let mut poll = libc::pollfd {
                        fd,
                        events: libc::POLLOUT,
                        revents: 0,
                    };
                    // SAFETY: valid stack poll descriptor; at most 20 ms.
                    unsafe {
                        libc::poll(&mut poll, 1, 20);
                    }
                }
                Err(e) => return Err(e.into()),
            }
        }
        Ok(())
    }
}
impl crate::adapters::ModelBackend for ProcessModel {
    fn timings(&self) -> Option<crate::metrics::GenerationTimings> {
        self.timings.borrow().clone()
    }
    fn generate(&self, prompt: &str, cancellation: &AtomicU64, ticket: u64) -> Result<String> {
        self.timings.borrow_mut().take();
        if prompt.len() > 32768 {
            bail!("Model prompt exceeds IPC limit");
        }
        let deadline = Instant::now() + Duration::from_secs(self.options.timeout_seconds);
        let mut state = self.running.borrow_mut();
        let result = (|| {
            if state.is_none() {
                *state = Some(self.start()?);
                let ready =
                    self.receive(state.as_ref().unwrap(), cancellation, ticket, deadline)?;
                let ready: std::result::Result<(), String> = serde_json::from_str(&ready)?;
                ready.map_err(anyhow::Error::msg)?;
            }
            let running = state.as_mut().unwrap();
            self.send(
                running,
                &format!("{}\n", serde_json::to_string(prompt)?),
                cancellation,
                ticket,
                deadline,
            )?;
            let line = self.receive(running, cancellation, ticket, deadline)?;
            let reply: ModelReply = serde_json::from_str(&line)?;
            *self.timings.borrow_mut() = Some(reply.timings);
            reply.result.map_err(anyhow::Error::msg)
        })();
        if result.is_err() {
            state.take();
        }
        result
    }
}

#[derive(serde::Serialize, serde::Deserialize)]
#[serde(deny_unknown_fields)]
struct ModelReply {
    result: std::result::Result<String, String>,
    timings: crate::metrics::GenerationTimings,
}

#[cfg(feature = "inference")]
pub fn serve(path: &Path) -> Result<()> {
    let mut input = std::io::stdin().lock();
    let mut line = String::new();
    input.by_ref().take(4097).read_line(&mut line)?;
    if line.len() > 4096 {
        bail!("Oversized model options");
    }
    let options = serde_json::from_str(&line)?;
    let mut output = std::io::stdout().lock();
    let model = crate::inference::LocalModel::load_with_options(path, options);
    let ready: std::result::Result<(), String> = model
        .as_ref()
        .map(|_| ())
        .map_err(|e| crate::context::redact(&e.to_string()));
    writeln!(output, "{}", serde_json::to_string(&ready)?)?;
    output.flush()?;
    let model = model?;
    loop {
        line.clear();
        if input.by_ref().take(65537).read_line(&mut line)? == 0 {
            break;
        }
        if line.len() > 65536 {
            bail!("Oversized model request");
        }
        let prompt: String = serde_json::from_str(&line)?;
        let result = model
            .generate(&prompt, &AtomicU64::new(0), 0)
            .map_err(|e| e.to_string());
        writeln!(
            output,
            "{}",
            serde_json::to_string(&ModelReply {
                result,
                timings: model.timings()
            })?
        )?;
        output.flush()?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn hung_crashed_and_cancelled_child_are_bounded_and_reaped() {
        let model = ProcessModel::new(
            Path::new("/bin/sleep"),
            &crate::settings::Inference::default(),
        )
        .unwrap();
        let child = Command::new("/bin/sleep")
            .arg("30")
            .stdin(Stdio::piped())
            .spawn()
            .unwrap();
        let pid = child.id();
        let (tx, replies) = mpsc::sync_channel(1);
        let mut running = Running { child, replies };
        let now = Instant::now();
        assert!(model
            .receive(
                &running,
                &AtomicU64::new(0),
                0,
                now + Duration::from_millis(40)
            )
            .is_err());
        assert!(model
            .receive(
                &running,
                &AtomicU64::new(1),
                0,
                now + Duration::from_secs(10)
            )
            .is_err());
        assert!(model
            .send(
                &mut running,
                &"x".repeat(1_000_000),
                &AtomicU64::new(0),
                0,
                Instant::now() + Duration::from_millis(40)
            )
            .is_err());
        drop(tx);
        assert!(model
            .receive(
                &running,
                &AtomicU64::new(0),
                0,
                now + Duration::from_secs(10)
            )
            .is_err());
        drop(running);
        assert!(now.elapsed() < Duration::from_secs(2));
        // SAFETY: querying the reaped child pid only, never signaling it.
        assert_eq!(unsafe { libc::kill(pid as i32, 0) }, -1);
    }
}
