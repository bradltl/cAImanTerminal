use std::{
    path::PathBuf,
    sync::{atomic::AtomicU64, Arc},
};
fn main() -> anyhow::Result<()> {
    let mut model: Option<PathBuf> = None;
    let mut disabled = false;
    let mut theme = None;
    let mut ask = None;
    let mut audit = None;
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--model" => {
                model = Some(
                    args.next()
                        .ok_or_else(|| anyhow::anyhow!("--model requires a local GGUF path"))?
                        .into(),
                )
            }
            "--no-ai" => disabled = true,
            "--theme" => {
                let id = args.next().ok_or_else(|| {
                    anyhow::anyhow!("--theme requires a theme ID; use --list-themes")
                })?;
                if caiman_terminal::theme::find(&id).is_none() {
                    anyhow::bail!("Unknown theme '{id}'; use --list-themes");
                }
                theme = Some(id);
            }
            "--list-themes" => {
                for theme in caiman_terminal::theme::all() {
                    println!("{:<20} {}", theme.id, theme.name);
                }
                return Ok(());
            }
            "--version" | "-V" => {
                println!("cAIman Terminal {}", env!("CARGO_PKG_VERSION"));
                return Ok(());
            }

            "--audit-report" => {
                audit = Some(args.next().ok_or_else(|| {
                    anyhow::anyhow!("--audit-report requires a JSON benchmark path")
                })?)
            }
            "--ask" => {
                ask = Some(
                    args.next()
                        .ok_or_else(|| anyhow::anyhow!("--ask requires a question"))?,
                )
            }
            "--help" | "-h" => {
                println!("{}\ncAIman Terminal 0.1\n\n  --model PATH  Local GGUF (default: SFT v2)\n  --no-ai       Plain terminal, no model load\n  --ask TEXT    Headless final-pipeline inference; never executes commands\n  --audit-report PATH  Replay a saved benchmark through host validation\n  --theme ID    Theme override for this window\n  --list-themes List bundled theme IDs\n  --version     Print version\n\nManual: man caiman-terminal", include_str!("../resources/caiman.txt"));
                return Ok(());
            }
            _ => anyhow::bail!("Unknown option: {arg}"),
        }
    }
    if let Some(path) = audit {
        let report = serde_json::from_str(&std::fs::read_to_string(path)?)?;
        let audit = caiman_terminal::host::audit_report(&report)?;
        println!("{}", serde_json::to_string_pretty(&audit)?);
        if audit["critical_cases_still_stageable"]
            .as_u64()
            .unwrap_or(0)
            != 0
        {
            anyhow::bail!("Critical host safety replay failed");
        }
        return Ok(());
    }
    let mut settings = caiman_terminal::settings::load(&caiman_terminal::settings::path()?)?;
    let model = model.unwrap_or_else(|| settings.resolved_model());
    disabled |= !settings.ai_enabled;
    if let Some(id) = &theme {
        settings.theme = id.clone();
    }
    if disabled && ask.is_some() {
        anyhow::bail!("--no-ai cannot be combined with --ask");
    }
    if let Some(text) = ask {
        #[cfg(feature = "inference")]
        {
            let hash = caiman_terminal::host::model_hash(&model)?;
            let runtime = caiman_terminal::adapters::load_model(
                &settings.model_backend,
                &model,
                &settings.inference,
            )?;
            let mut session = caiman_terminal::context::Session::new(
                0,
                std::env::current_dir()?.display().to_string(),
            );
            session.at_prompt = true;
            let request = caiman_terminal::worker::Request {
                session,
                text,
                ticket: 0,
                cancellation: Arc::new(AtomicU64::new(0)),
                passive: false,
            };
            let answer = caiman_terminal::worker::process(&request, |p| {
                runtime.generate(p, &request.cancellation, 0)
            })?;
            println!(
                "{}",
                serde_json::to_string_pretty(
                    &serde_json::json!({"model": model, "sha256": hash, "schema": "cayman-response-v1", "response": answer.response, "validation": answer.validation, "source": answer.source, "repaired": answer.repaired, "elapsed_ms": answer.elapsed_ms})
                )?
            );
            return Ok(());
        }
        #[cfg(not(feature = "inference"))]
        {
            let _ = (text, AtomicU64::new(0), Arc::new(()));
            anyhow::bail!("Built without inference");
        }
    }
    #[cfg(feature = "desktop")]
    caiman_terminal::ui::run(model, disabled, settings);
    #[cfg(not(feature = "desktop"))]
    {
        let _ = (model, disabled, theme, settings);
        anyhow::bail!("Build with desktop feature to open the terminal");
    }
    #[allow(unreachable_code)]
    Ok(())
}
