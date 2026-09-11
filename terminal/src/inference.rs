use anyhow::{bail, Context, Result};
use llama_cpp_2::{
    context::params::LlamaContextParams,
    llama_backend::LlamaBackend,
    llama_batch::LlamaBatch,
    model::{params::LlamaModelParams, AddBos, LlamaChatMessage, LlamaModel},
    sampling::LlamaSampler,
};
use std::{
    num::NonZeroU32,
    path::Path,
    sync::atomic::{AtomicU64, Ordering},
    time::{Duration, Instant},
};

pub struct LocalModel {
    model: LlamaModel,
    _verified: crate::model_file::VerifiedModel,
    backend: LlamaBackend,
    options: crate::settings::Inference,
}
impl LocalModel {
    /// Use the real tokenizer and chat template, including system instructions.
    /// Reserve 396 tokens for generation/template overhead in the 4096-token KV.
    pub fn prepare_prompt(&self, input: &str) -> Result<(String, usize, bool)> {
        let mut envelope: crate::prompt::Prompt =
            serde_json::from_str(input).context("Expected a structured host context envelope")?;
        let template = self
            .model
            .chat_template(None)
            .context("GGUF has no supported chat template")?;
        loop {
            let rendered = self.model.apply_chat_template(
                &template,
                &[
                    LlamaChatMessage::new(
                        "system".into(),
                        include_str!("../resources/system.txt").into(),
                    )?,
                    LlamaChatMessage::new("user".into(), envelope.render())?,
                ],
                true,
            )?;
            let count = self.model.str_to_token(&rendered, AddBos::Never)?.len();
            if count <= self.options.context_tokens as usize - self.options.output_tokens - 140 {
                return Ok((rendered, count, envelope.context_trimmed));
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
        let model = LlamaModel::load_from_file(
            &backend,
            verified.path(),
            &LlamaModelParams::default().with_n_gpu_layers(0),
        )?;
        Ok(Self {
            model,
            _verified: verified,
            backend,
            options,
        })
    }
    pub fn generate(&self, input: &str, cancellation: &AtomicU64, ticket: u64) -> Result<String> {
        let started = Instant::now();
        if cancellation.load(Ordering::Relaxed) != ticket {
            bail!("Request cancelled");
        }
        let (prompt, _, _) = self.prepare_prompt(input)?;
        let tokens = self.model.str_to_token(&prompt, AddBos::Never)?;
        // Fresh KV state prevents leakage between tabs. The expensive model
        // weights stay loaded for the lifetime of the single inference worker.
        let params = LlamaContextParams::default()
            .with_n_ctx(NonZeroU32::new(self.options.context_tokens))
            .with_n_threads(self.options.threads)
            .with_n_threads_batch(self.options.threads);
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
            // sample() already accepts the token in this pinned llama.cpp API.
            // Accepting twice advances grammar state twice and can abort in C++.
            if self.model.is_eog_token(token) {
                return Ok(result);
            }
            result.push_str(&self.model.token_to_piece(token, &mut decoder, true, None)?);
            if serde_json::from_str::<serde_json::Value>(&result).is_ok() {
                return Ok(result);
            }
            batch.clear();
            batch.add(token, position as i32, &[0], true)?;
            ctx.decode(&mut batch)?;
        }
        bail!("Model response exceeded the generation limit")
    }
}
