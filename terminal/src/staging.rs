//! The single assistant-to-terminal staging boundary. Model bytes go only to
//! the private Readline data file; the terminal accepts a closed enum of keys.
use crate::{
    context::{ContextBinding, Session},
    terminal_backend::{IntegrationKey, TerminalSurface},
};
use std::path::Path;

pub struct StageAttempt<'a> {
    pub command: &'a str,
    pub binding: &'a ContextBinding,
    pub ticket: u64,
    pub current_ticket: u64,
    pub alive: bool,
    pub passive: bool,
}

pub fn stage(
    surface: &impl TerminalSurface,
    dir: &Path,
    session: &Session,
    attempt: StageAttempt<'_>,
) -> anyhow::Result<()> {
    anyhow::ensure!(
        attempt.alive
            && !attempt.passive
            && attempt.ticket == attempt.current_ticket
            && attempt.binding.matches(session),
        "Stale or unauthorized staging attempt"
    );
    crate::shell::write_stage_bound(
        dir,
        attempt.command,
        &session.input,
        &session.cwd,
        session.prompt_generation,
    )?;
    surface.send_integration_key(IntegrationKey::Stage);
    Ok(())
}
