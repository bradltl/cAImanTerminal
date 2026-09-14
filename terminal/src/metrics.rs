//! Bounded, memory-only aggregates. No commands, paths, prose or IDs are retained.
use serde::Serialize;

#[derive(Debug, Clone, Default, Serialize, serde::Deserialize)]
pub struct GenerationTimings {
    pub load_ms: f64,
    pub prepare_ms: f64,
    pub prefill_ms: f64,
    pub decode_ms: f64,
    pub first_token_ms: f64,
    pub input_tokens: usize,
    pub output_tokens: usize,
}

#[derive(Debug, Clone, Default, Serialize)]
pub struct PipelineTimings {
    pub worker_ms: f64,
    pub inference_round_trip_ms: f64,
    pub host_processing_ms: f64,
    pub candidate_validation_ms: f64,
    pub generation: Option<GenerationTimings>,
}

pub enum ValidatorOutcome {
    Verified,
    Clarification,
    Unverifiable,
    Rejected,
}

#[derive(Default, Serialize)]
pub struct Metrics {
    /// disk, memory, files, cwd, git, system-update, literal, explain/unknown.
    pub scenario_categories: [u64; 8],
    /// Verified, clarification/no command, unverifiable, hard rejection.
    pub validator_outcomes: [u64; 4],
    /// Normal, caution, elevated; only final validated candidates count.
    pub validated_risk: [u64; 3],
    pub requested: u64,
    pub deterministic: u64,
    pub model: u64,
    pub corrected: u64,
    pub verified: u64,
    pub rejected: u64,
    pub cancelled: u64,
    pub accepted: u64,
    pub edited: u64,
    pub dismissed: u64,
    pub executed_success: u64,
    pub executed_failure: u64,
    /// <=250, <=750, <=1500, <=3000, <=10000, >10000 milliseconds.
    pub latency_buckets: [u64; 6],
}
impl Metrics {
    pub fn validation(&mut self, outcome: ValidatorOutcome, risk: Option<&crate::host::Risk>) {
        let index = outcome as usize;
        self.validator_outcomes[index] = self.validator_outcomes[index].saturating_add(1);
        if let Some(risk) = risk {
            let index = match risk {
                crate::host::Risk::Normal => 0,
                crate::host::Risk::Caution => 1,
                crate::host::Risk::Elevated => 2,
            };
            self.validated_risk[index] = self.validated_risk[index].saturating_add(1);
        }
    }
    pub fn requested(&mut self, contract: &crate::intent::IntentContract) {
        use crate::intent::IntentContract;
        let category = match contract {
            IntentContract::Alternatives(commands) => {
                match commands.first().map(String::as_str).unwrap_or("") {
                    "df -h" => 0,
                    "free -h" => 1,
                    "ls" | "ls -R" => 2,
                    "pwd" => 3,
                    "git status" => 4,
                    "pacman -Syu" | "sudo pacman -Syu" => 5,
                    _ => 7,
                }
            }
            IntentContract::ReadFile(_) => 2,
            IntentContract::ExactCommand(_) => 6,
            IntentContract::ExplainOrClarify => 7,
        };
        self.requested = self.requested.saturating_add(1);
        self.scenario_categories[category] = self.scenario_categories[category].saturating_add(1);
    }
    pub fn completed(
        &mut self,
        elapsed_ms: u128,
        deterministic: bool,
        corrected: bool,
        verified: bool,
    ) {
        if deterministic {
            self.deterministic = self.deterministic.saturating_add(1);
        } else {
            self.model = self.model.saturating_add(1);
        }
        if corrected {
            self.corrected = self.corrected.saturating_add(1);
        }
        if verified {
            self.verified = self.verified.saturating_add(1);
        } else {
            self.rejected = self.rejected.saturating_add(1);
        }
        let bucket = [250, 750, 1500, 3000, 10000]
            .iter()
            .position(|limit| elapsed_ms <= *limit)
            .unwrap_or(5);
        self.latency_buckets[bucket] = self.latency_buckets[bucket].saturating_add(1);
    }
    pub fn export(&self) -> String {
        serde_json::to_string_pretty(self).expect("fixed aggregate schema")
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn export_is_fixed_numeric_aggregate_and_retention_is_constant_space() {
        let mut metrics = Metrics::default();
        for _ in 0..10000 {
            metrics.completed(800, false, false, true);
            metrics.validation(ValidatorOutcome::Verified, Some(&crate::host::Risk::Normal));
        }
        let value: serde_json::Value = serde_json::from_str(&metrics.export()).unwrap();
        assert!(value.as_object().unwrap().values().all(|v| v.is_u64()
            || v.as_array()
                .is_some_and(|a| [3, 4, 6, 8].contains(&a.len()) && a.iter().all(|n| n.is_u64()))));
        assert_eq!(metrics.latency_buckets[2], 10000);
        assert_eq!(metrics.validator_outcomes, [10000, 0, 0, 0]);
        assert_eq!(metrics.validated_risk, [10000, 0, 0]);
        assert!(metrics.export().len() < 1024);
    }
}
