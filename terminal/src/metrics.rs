//! Bounded, memory-only aggregates. No API accepts commands, paths, prose or IDs.
use serde::Serialize;

#[derive(Default, Serialize)]
pub struct Metrics {
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
        }
        let value: serde_json::Value = serde_json::from_str(&metrics.export()).unwrap();
        assert!(value.as_object().unwrap().values().all(|v| v.is_u64()
            || v.as_array()
                .is_some_and(|a| a.len() == 6 && a.iter().all(|n| n.is_u64()))));
        assert_eq!(metrics.latency_buckets[2], 10000);
        assert!(metrics.export().len() < 1024);
    }
}
