//! Versioned replay of the worker's deterministic candidate boundary.
use crate::{
    alpha_policy::{HostFacts, VERSION},
    context::Session,
    worker::{self, Request},
};
use serde::Deserialize;
use std::sync::{atomic::AtomicU64, Arc};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Fixture {
    pub policy: String,
    pub request: String,
    pub candidate: String,
    pub context: Session,
    pub host: HostFacts,
    #[serde(default)]
    pub passive: bool,
    #[serde(default)]
    pub cancelled: bool,
}
pub fn evaluate(fixture: Fixture) -> anyhow::Result<crate::alpha_policy::DecisionTrace> {
    anyhow::ensure!(fixture.policy == VERSION, "Unsupported policy version");
    let ticket = fixture.context.request_id;
    let request = Request {
        session: fixture.context,
        text: fixture.request,
        passive: fixture.passive,
        ticket,
        cancellation: Arc::new(AtomicU64::new(if fixture.cancelled {
            ticket.wrapping_add(1)
        } else {
            ticket
        })),
    };
    Ok(worker::check_candidate(
        &request,
        &fixture.candidate,
        &fixture.host,
    ))
}
