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
    pub candidate: Option<String>,
    pub response: Option<String>,
    pub context: Session,
    pub host: HostFacts,
    #[serde(default)]
    pub passive: bool,
    #[serde(default)]
    pub cancelled: bool,
}
pub fn evaluate(fixture: Fixture) -> anyhow::Result<serde_json::Value> {
    anyhow::ensure!(fixture.policy == VERSION, "Unsupported policy version");
    anyhow::ensure!(
        fixture.candidate.is_some() != fixture.response.is_some(),
        "Supply exactly one candidate or response"
    );
    let raw_response = fixture.response.is_some();
    let candidate = if let Some(raw) = fixture.response {
        match crate::host::Response::parse_assistant(&raw) {
            Ok(response) => match response.command {
                Some(command) => command,
                None => {
                    return Ok(
                        serde_json::json!({"response_schema":"valid","trace":null,"stageable":false}),
                    )
                }
            },
            Err(_) => {
                return Ok(
                    serde_json::json!({"response_schema":"invalid","trace":null,"stageable":false}),
                )
            }
        }
    } else {
        fixture.candidate.unwrap()
    };
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
    let trace = worker::check_candidate(&request, &candidate, &fixture.host);
    Ok(if raw_response {
        serde_json::json!({"response_schema":"valid","stageable":trace.stageable,"trace":trace})
    } else {
        serde_json::to_value(trace)?
    })
}
