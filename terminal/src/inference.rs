use crate::settings::{AccelerationBackend, AccelerationStatus, Inference, InferenceRuntime};
use anyhow::{bail, Context, Result};
use llama_cpp_2::{
    context::params::LlamaContextParams,
    llama_backend::LlamaBackend,
    llama_batch::LlamaBatch,
    model::{params::LlamaModelParams, AddBos, LlamaChatMessage, LlamaChatTemplate, LlamaModel},
    sampling::LlamaSampler,
    LlamaBackendDeviceType,
};
use std::{
    num::NonZeroU32,
    path::Path,
    sync::atomic::{AtomicU64, Ordering},
    time::{Duration, Instant},
};

pub struct LocalModel {
    template: LlamaChatTemplate,
    timings: std::cell::RefCell<crate::metrics::GenerationTimings>,
    model: LlamaModel,
    _verified: crate::model_file::VerifiedModel,
    backend: LlamaBackend,
    options: crate::settings::Inference,
    runtime: InferenceRuntime,
}

fn select_acceleration(
    options: &Inference,
    devices: &[llama_cpp_2::LlamaBackendDevice],
) -> (InferenceRuntime, Option<usize>) {
    let device = options
        .gpu_offload
        .then(|| {
            devices.iter().find_map(|device| {
                // Software Vulkan renderers can be enumerated as CPU devices. They
                // do not establish hardware acceleration and are not selected.
                if !matches!(
                    device.device_type,
                    LlamaBackendDeviceType::Gpu | LlamaBackendDeviceType::IntegratedGpu
                ) {
                    return None;
                }
                let backend = match device.backend.as_str() {
                    "Vulkan" if cfg!(feature = "gpu-vulkan") => AccelerationBackend::Vulkan,
                    "CUDA" if cfg!(feature = "gpu-cuda") => AccelerationBackend::Cuda,
                    _ => return None,
                };
                Some((backend, device.index))
            })
        })
        .flatten();
    let runtime = InferenceRuntime {
        backend: device.map_or(AccelerationBackend::Cpu, |(backend, _)| backend),
        status: if !options.gpu_offload {
            AccelerationStatus::CpuDisabled
        } else if device.is_some() {
            AccelerationStatus::OffloadRequested
        } else {
            AccelerationStatus::CpuUnavailable
        },
        requested_gpu_layers: if options.gpu_offload {
            options.gpu_layers
        } else {
            0
        },
    };
    (runtime, device.map(|(_, index)| index))
}

fn load_with_fallback<T>(
    runtime: &mut InferenceRuntime,
    mut load: impl FnMut(bool) -> Result<T>,
) -> Result<T> {
    let offload = runtime.status == AccelerationStatus::OffloadRequested;
    match load(offload) {
        Err(_) if offload => {
            // Only model/context preparation is retried, never generation. Both
            // attempts use the same already-verified sealed model descriptor.
            runtime.backend = AccelerationBackend::Cpu;
            runtime.status = AccelerationStatus::CpuFallback;
            load(false)
        }
        result => result,
    }
}

fn context_params(options: &Inference, offload: bool) -> LlamaContextParams {
    LlamaContextParams::default()
        .with_n_ctx(NonZeroU32::new(options.context_tokens))
        .with_n_threads(options.threads)
        .with_n_threads_batch(options.threads)
        .with_offload_kqv(offload)
        .with_op_offload(offload)
}

impl LocalModel {
    /// Use the real tokenizer and chat template, including system instructions.
    /// Reserve 396 tokens for generation/template overhead in the 4096-token KV.
    pub fn prepare_prompt(&self, input: &str) -> Result<(String, usize, bool)> {
        let (rendered, tokens, trimmed) = self.prepare_tokens(input)?;
        Ok((rendered, tokens.len(), trimmed))
    }
    fn prepare_tokens(
        &self,
        input: &str,
    ) -> Result<(String, Vec<llama_cpp_2::token::LlamaToken>, bool)> {
        let mut envelope: crate::prompt::Prompt =
            serde_json::from_str(input).context("Expected a structured host context envelope")?;
        loop {
            let rendered = self.model.apply_chat_template(
                &self.template,
                &[
                    LlamaChatMessage::new(
                        "system".into(),
                        include_str!("../resources/system.txt").into(),
                    )?,
                    LlamaChatMessage::new("user".into(), envelope.render())?,
                ],
                true,
            )?;
            let tokens = self.model.str_to_token(&rendered, AddBos::Never)?;
            if tokens.len()
                <= self.options.context_tokens as usize - self.options.output_tokens - 140
            {
                return Ok((rendered, tokens, envelope.context_trimmed));
            }
            if !envelope.compact() {
                bail!("The current request and required host context exceed the model token budget. Shorten this request; opening a new tab is not necessary.");
            }
        }
    }
    pub fn load(path: &Path) -> Result<Self> {
        Self::load_with_options(path, crate::settings::Inference::default())
    }
    pub fn load_with_options(path: &Path, options: crate::settings::Inference) -> Result<Self> {
        let loaded = Instant::now();
        options.validate()?;
        let verified = crate::model_file::VerifiedModel::open(
            path,
            options
                .model_sha256
                .as_deref()
                .unwrap_or(crate::model_file::DEFAULT_SHA256),
        )?;
        let mut backend = LlamaBackend::init()?;
        backend.void_logs();
        let devices = if options.gpu_offload && backend.supports_gpu_offload() {
            llama_cpp_2::list_llama_ggml_backend_devices()
        } else {
            Vec::new()
        };
        let (mut runtime, selected_device) = select_acceleration(&options, &devices);
        let model = load_with_fallback(&mut runtime, |offload| {
            // Explicit device selection prevents a disabled or unavailable GPU
            // preference from accidentally inheriting native auto-placement.
            let selected: Vec<_> = selected_device.filter(|_| offload).into_iter().collect();
            let params = LlamaModelParams::default()
                .with_n_gpu_layers(if offload { options.gpu_layers } else { 0 })
                .with_devices(&selected)?;
            let model = LlamaModel::load_from_file(&backend, verified.path(), &params)?;
            if offload {
                // Check the requested context allocation before the first token.
                // Drop this empty context; requests still get independent KV.
                let _preflight = model.new_context(&backend, context_params(&options, true))?;
            }
            Ok(model)
        })?;
        Ok(Self {
            template: model
                .chat_template(None)
                .context("GGUF has no supported chat template")?,
            timings: std::cell::RefCell::new(crate::metrics::GenerationTimings {
                load_ms: loaded.elapsed().as_secs_f64() * 1000.0,
                ..Default::default()
            }),
            model,
            _verified: verified,
            backend,
            options,
            runtime,
        })
    }
    pub fn generate(&self, input: &str, cancellation: &AtomicU64, ticket: u64) -> Result<String> {
        let started = Instant::now();
        let load_ms = self.timings.borrow().load_ms;
        *self.timings.borrow_mut() = crate::metrics::GenerationTimings {
            load_ms,
            ..Default::default()
        };
        if cancellation.load(Ordering::Relaxed) != ticket {
            bail!("Request cancelled");
        }
        let (_, tokens, _) = self.prepare_tokens(input)?;
        self.timings.borrow_mut().input_tokens = tokens.len();
        self.timings.borrow_mut().prepare_ms = started.elapsed().as_secs_f64() * 1000.0;
        let prefill = Instant::now();
        // Fresh KV state prevents leakage between tabs. The expensive model
        // weights stay loaded for the lifetime of the single inference worker.
        let params = context_params(
            &self.options,
            self.runtime.status == AccelerationStatus::OffloadRequested,
        );
        let mut ctx = self.model.new_context(&self.backend, params)?;
        let mut batch = LlamaBatch::new(512, 1);
        for (chunk_index, chunk) in tokens.chunks(512).enumerate() {
            if started.elapsed() > Duration::from_secs(self.options.timeout_seconds) {
                bail!(
                    "Local inference exceeded {} seconds",
                    self.options.timeout_seconds
                );
            }
            if cancellation.load(Ordering::Relaxed) != ticket {
                bail!("Request cancelled");
            }
            batch.clear();
            for (i, token) in chunk.iter().enumerate() {
                let pos = chunk_index * 512 + i;
                batch.add(*token, pos as i32, &[0], pos == tokens.len() - 1)?;
            }
            ctx.decode(&mut batch)?;
        }
        self.timings.borrow_mut().prefill_ms = prefill.elapsed().as_secs_f64() * 1000.0;
        let decoding = Instant::now();
        let mut sampler = LlamaSampler::chain_simple([
            LlamaSampler::grammar(
                &self.model,
                include_str!("../resources/response.gbnf"),
                "root",
            )?,
            LlamaSampler::greedy(),
        ]);
        let mut decoder = encoding_rs::UTF_8.new_decoder();
        let mut result = String::new();
        let mut frame = crate::response_stream::JsonObject::default();
        for position in tokens.len()..tokens.len() + self.options.output_tokens {
            if cancellation.load(Ordering::Relaxed) != ticket {
                bail!("Request cancelled");
            }
            if started.elapsed() > Duration::from_secs(self.options.timeout_seconds) {
                bail!(
                    "Local inference exceeded {} seconds",
                    self.options.timeout_seconds
                );
            }
            let token = sampler.sample(&ctx, batch.n_tokens() - 1);
            let mut timing = self.timings.borrow_mut();
            timing.decode_ms = decoding.elapsed().as_secs_f64() * 1000.0;
            if timing.output_tokens == 0 {
                timing.first_token_ms = started.elapsed().as_secs_f64() * 1000.0;
            }
            timing.output_tokens += 1;
            drop(timing);
            // sample() already accepts the token in this pinned llama.cpp API.
            // Accepting twice advances grammar state twice and can abort in C++.
            if self.model.is_eog_token(token) {
                return crate::response_stream::validate_complete(result);
            }
            let piece = self.model.token_to_piece(token, &mut decoder, true, None)?;
            result.push_str(&piece);
            anyhow::ensure!(result.len() <= 16384, "Model response exceeds byte limit");
            if frame.push(&piece)? {
                return crate::response_stream::validate_complete(result);
            }
            batch.clear();
            batch.add(token, position as i32, &[0], true)?;
            ctx.decode(&mut batch)?;
        }
        bail!("Model response exceeded the generation limit")
    }
    pub fn timings(&self) -> crate::metrics::GenerationTimings {
        self.timings.borrow().clone()
    }
    pub fn runtime(&self) -> &InferenceRuntime {
        &self.runtime
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn device(
        backend: &str,
        device_type: LlamaBackendDeviceType,
    ) -> llama_cpp_2::LlamaBackendDevice {
        llama_cpp_2::LlamaBackendDevice {
            index: 7,
            name: "synthetic".into(),
            description: "synthetic".into(),
            backend: backend.into(),
            memory_total: 1024,
            memory_free: 1024,
            device_type,
        }
    }

    #[test]
    fn gpu_selection_requires_opt_in_compiled_backend_and_hardware() {
        let mut options = Inference::default();
        let devices = [device("Vulkan", LlamaBackendDeviceType::IntegratedGpu)];
        let (runtime, selected) = select_acceleration(&options, &devices);
        assert_eq!(runtime.status, AccelerationStatus::CpuDisabled);
        assert_eq!(runtime.requested_gpu_layers, 0);
        assert_eq!(selected, None);
        options.gpu_offload = true;
        assert_eq!(
            select_acceleration(&options, &devices).1,
            cfg!(feature = "gpu-vulkan").then_some(7)
        );
        for devices in [
            vec![],
            vec![device("Vulkan", LlamaBackendDeviceType::Cpu)],
            vec![device("unknown", LlamaBackendDeviceType::Gpu)],
        ] {
            let (runtime, selected) = select_acceleration(&options, &devices);
            assert_eq!(runtime.status, AccelerationStatus::CpuUnavailable);
            assert_eq!(selected, None);
        }
        for (backend, compiled) in [
            ("Vulkan", cfg!(feature = "gpu-vulkan")),
            ("CUDA", cfg!(feature = "gpu-cuda")),
        ] {
            let (runtime, selected) =
                select_acceleration(&options, &[device(backend, LlamaBackendDeviceType::Gpu)]);
            assert_eq!(selected, compiled.then_some(7));
            assert_eq!(
                runtime.status,
                if compiled {
                    AccelerationStatus::OffloadRequested
                } else {
                    AccelerationStatus::CpuUnavailable
                }
            );
        }
        let cpu = context_params(&options, false);
        assert!(!cpu.offload_kqv());
        assert!(!cpu.op_offload());
        let gpu = context_params(&options, true);
        assert!(gpu.offload_kqv());
        assert!(gpu.op_offload());
    }

    #[test]
    fn allocation_fallback_precedes_generation_and_never_retries_cpu_failure() {
        let mut runtime = InferenceRuntime {
            backend: AccelerationBackend::Vulkan,
            status: AccelerationStatus::OffloadRequested,
            requested_gpu_layers: 32,
        };
        let mut attempts = Vec::new();
        let mut successful = runtime.clone();
        let gpu_model = load_with_fallback(&mut successful, |offload| {
            attempts.push(offload);
            Ok("GPU model")
        })
        .unwrap();
        assert_eq!(gpu_model, "GPU model");
        assert_eq!(attempts, [true]);
        assert_eq!(successful, runtime);
        attempts.clear();
        let model = load_with_fallback(&mut runtime, |offload| {
            attempts.push(offload);
            anyhow::ensure!(!offload, "synthetic GPU allocation failure");
            Ok("CPU model")
        })
        .unwrap();
        assert_eq!(model, "CPU model");
        assert_eq!(attempts, [true, false]);
        assert_eq!(runtime.backend, AccelerationBackend::Cpu);
        assert_eq!(runtime.status, AccelerationStatus::CpuFallback);
        assert!(runtime.description().contains("CPU fallback"));
        attempts.clear();
        let result: Result<()> = load_with_fallback(&mut runtime, |offload| {
            attempts.push(offload);
            bail!("synthetic CPU failure")
        });
        assert!(result.is_err());
        assert_eq!(attempts, [false]);
    }
}
