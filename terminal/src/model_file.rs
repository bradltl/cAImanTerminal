//! Hash and seal model bytes before the native parser sees them. Loading via a
//! retained memfd prevents symlink replacement and in-place edits during mmap.
use anyhow::{bail, Context, Result};
use sha2::{Digest, Sha256};
use std::{
    fs::{File, OpenOptions},
    io::{Read, Write},
    os::{
        fd::{AsRawFd, FromRawFd},
        unix::fs::OpenOptionsExt,
    },
    path::{Path, PathBuf},
};

pub const DEFAULT_SHA256: &str = "fdb77f88b8282cbb0e65f8362b5c11e8ea8648f1730661fb5592e5b6a633fb61";

pub struct VerifiedModel {
    file: File,
    pub sha256: String,
}
impl VerifiedModel {
    pub fn open(path: &Path, expected: &str) -> Result<Self> {
        if expected.len() != 64 || !expected.bytes().all(|b| b.is_ascii_hexdigit()) {
            bail!("Model SHA-256 must contain exactly 64 hexadecimal digits");
        }
        let path = path.canonicalize().context("Model file unavailable")?;
        let mut input = OpenOptions::new()
            .read(true)
            .custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK)
            .open(path)?;
        let metadata = input.metadata()?;
        if !metadata.is_file() || metadata.len() > 16 * 1024 * 1024 * 1024 {
            bail!("Model must be a regular GGUF file no larger than 16 GiB");
        }
        // SAFETY: static NUL-terminated name; ownership of the returned fd passes to File.
        let fd = unsafe {
            libc::memfd_create(
                c"caiman-model".as_ptr(),
                libc::MFD_CLOEXEC | libc::MFD_ALLOW_SEALING,
            )
        };
        if fd < 0 {
            return Err(std::io::Error::last_os_error().into());
        }
        let mut file = unsafe { File::from_raw_fd(fd) };
        let mut hash = Sha256::new();
        let mut buffer = [0; 65536];
        let mut count = 0u64;
        loop {
            let n = input.read(&mut buffer)?;
            if n == 0 {
                break;
            }
            count += n as u64;
            if count > metadata.len() {
                bail!("Model changed during verification");
            }
            hash.update(&buffer[..n]);
            file.write_all(&buffer[..n])?;
        }
        let sha256 = format!("{:x}", hash.finalize());
        if count != metadata.len() || !sha256.eq_ignore_ascii_case(expected) {
            bail!("Model identity mismatch; supply the trusted model SHA-256 in settings or --model-sha256");
        }
        // SAFETY: valid owned fd; seals are permanent and prohibit writes and resizing.
        if unsafe {
            libc::fcntl(
                fd,
                libc::F_ADD_SEALS,
                libc::F_SEAL_WRITE | libc::F_SEAL_GROW | libc::F_SEAL_SHRINK | libc::F_SEAL_SEAL,
            )
        } < 0
        {
            return Err(std::io::Error::last_os_error().into());
        }
        Ok(Self { file, sha256 })
    }
    pub fn path(&self) -> PathBuf {
        format!("/proc/self/fd/{}", self.file.as_raw_fd()).into()
    }
}
