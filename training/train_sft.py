#!/usr/bin/env python3
"""
SFT Fine-Tuning Pipeline for Qwen 2.5 0.5B Instruct using TRL and PEFT LoRA.
Trains on training_dataset/trl_train.jsonl, evaluates on training_dataset/trl_eval.jsonl,
merges the LoRA adapter, exports to GGUF, and computes SHA-256 for Cayman Terminal.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig, PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer

def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def main():
    parser = argparse.ArgumentParser(description="SFT Fine-tuning for Qwen 2.5 0.5B")
    parser.add_argument("--model_id", type=str, default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--train_file", type=str, default="training_dataset/trl_train.jsonl")
    parser.add_argument("--eval_file", type=str, default="training_dataset/trl_eval.jsonl")
    parser.add_argument("--output_dir", type=str, default="checkpoints/qwen2.5-0.5b-sft")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=4)
    parser.add_argument("--grad_accum", type=int, default=2)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--lora_r", type=int, default=16)
    parser.add_argument("--lora_alpha", type=int, default=32)
    parser.add_argument("--max_length", type=int, default=512)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto",
                        help="Use CUDA when available, otherwise CPU; cuda fails if unavailable.")
    parser.add_argument("--cpu_threads", type=int, default=None,
                        help="PyTorch CPU compute threads; benchmark several values on hybrid CPUs.")
    parser.add_argument("--gradient_checkpointing", action="store_true",
                        help="Recompute activations to save memory at the cost of training speed.")
    parser.add_argument("--benchmark_steps", type=int, default=0,
                        help="Run this many optimizer steps without evaluation, saving, or export.")
    parser.add_argument("--gguf_out", type=str, default="models/qwen2.5-0.5b-instruct-sft.gguf")
    args = parser.parse_args()

    if args.cpu_threads is not None and args.cpu_threads < 1:
        parser.error("--cpu_threads must be at least 1")
    if args.benchmark_steps < 0:
        parser.error("--benchmark_steps must be nonnegative")
    if args.device == "cuda" and not torch.cuda.is_available():
        parser.error("CUDA was requested but is unavailable. Check the GPU, driver, and PyTorch build.")
    use_cuda = args.device != "cpu" and torch.cuda.is_available()
    # TRL defaults to BF16 even on CPUs that emulate it extremely slowly.
    use_bf16 = use_cuda and torch.cuda.is_bf16_supported()
    use_fp16 = use_cuda and not use_bf16
    if args.cpu_threads is not None:
        torch.set_num_threads(args.cpu_threads)

    print(f"=== Cayman Terminal SFT Training Pipeline ===")
    print(f"Base Model:     {args.model_id}")
    print(f"Train File:     {args.train_file}")
    print(f"Eval File:      {args.eval_file}")
    print(f"Output Dir:     {args.output_dir}")
    print(f"Target GGUF:    {args.gguf_out}")
    print(f"Hyperparams:    epochs={args.epochs}, lr={args.lr}, batch_size={args.batch_size}, grad_accum={args.grad_accum}, r={args.lora_r}")
    print(f"Device:         {torch.cuda.get_device_name() if use_cuda else 'CPU (no GPU training)'}")
    print(f"Precision:      {'BF16' if use_bf16 else 'FP16' if use_fp16 else 'FP32'}")
    print(f"CPU threads:    {torch.get_num_threads()}")
    print(f"Checkpointing:  {args.gradient_checkpointing}")
    if args.benchmark_steps:
        print(f"Benchmark:      {args.benchmark_steps} optimizer steps; no evaluation, saving, or export")

    # 1. Load Dataset
    print("\n[1/5] Loading datasets...")
    data_files = {"train": args.train_file}
    if not args.benchmark_steps and os.path.exists(args.eval_file):
        data_files["eval"] = args.eval_file
    ds = load_dataset("json", data_files=data_files)
    train_ds = ds["train"]
    eval_ds = ds.get("eval")
    print(f"  Train samples: {len(train_ds)}")
    if eval_ds:
        print(f"  Eval samples:  {len(eval_ds)}")

    # 2. Load Tokenizer & Model
    print("\n[2/5] Initializing tokenizer and base model...")
    tokenizer = AutoTokenizer.from_pretrained(args.model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        # FP16 autocast keeps FP32 weights for gradient scaling; BF16 needs no scaler.
        dtype=torch.bfloat16 if use_bf16 else torch.float32,
        low_cpu_mem_usage=True,
        attn_implementation="sdpa",
    )
    model.config.use_cache = False

    # 3. Setup LoRA Config
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
    )

    # 4. Configure SFTTrainer
    training_args = SFTConfig(
        output_dir=args.output_dir,
        use_cpu=not use_cuda,
        bf16=use_bf16,
        fp16=use_fp16,
        gradient_checkpointing=args.gradient_checkpointing,
        optim="adamw_torch_fused" if use_cuda else "adamw_torch",
        learning_rate=args.lr,
        num_train_epochs=args.epochs,
        max_steps=args.benchmark_steps if args.benchmark_steps else -1,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        max_length=args.max_length,
        logging_steps=1 if args.benchmark_steps else 10,
        eval_strategy="epoch" if eval_ds else "no",
        save_strategy="no" if args.benchmark_steps else "epoch",
        save_total_limit=1,
        warmup_steps=10,
        lr_scheduler_type="cosine",
        report_to="none",
        dataloader_num_workers=0,
        dataloader_pin_memory=use_cuda,
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        peft_config=lora_config,
        processing_class=tokenizer,
    )

    print(f"  Trainer device: {trainer.args.device}; model device: {next(trainer.model.parameters()).device}")
    print("\n[3/5] Starting SFT training loop...")
    start_time = time.time()
    train_result = trainer.train()
    elapsed = time.time() - start_time
    print(f"  Training finished in {elapsed:.1f}s!")
    print(f"  Train metrics: {train_result.metrics}")
    if args.benchmark_steps:
        print("\nBenchmark complete. Adapter, merged model, and GGUF were not saved.")
        return

    # Save adapter
    adapter_dir = os.path.join(args.output_dir, "adapter")
    print(f"\n  Saving LoRA adapter to {adapter_dir}...")
    trainer.save_model(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)

    # 5. Merge adapter into base model
    print("\n[4/5] Merging LoRA adapter into base model weights...")
    merged_dir = os.path.join(args.output_dir, "merged")
    del model
    del trainer
    torch.cuda.empty_cache() if torch.cuda.is_available() else None

    base_model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        dtype=torch.float32,
        low_cpu_mem_usage=True,
    )
    peft_model = PeftModel.from_pretrained(base_model, adapter_dir)
    merged_model = peft_model.merge_and_unload()
    merged_model.save_pretrained(merged_dir)
    tokenizer.save_pretrained(merged_dir)
    print(f"  Merged model saved to {merged_dir}")

    # 6. Export to GGUF
    print(f"\n[5/5] Exporting merged model to GGUF ({args.gguf_out})...")
    Path(args.gguf_out).parent.mkdir(parents=True, exist_ok=True)
    convert_cmd = [
        sys.executable,
        "tools/llama.cpp/convert_hf_to_gguf.py",
        merged_dir,
        "--outfile",
        args.gguf_out,
        "--outtype",
        "q8_0",
    ]
    res = subprocess.run(convert_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error during GGUF conversion:\n{res.stderr}")
        sys.exit(1)

    print(f"✔ GGUF conversion successful: {args.gguf_out}")
    sha256 = compute_sha256(args.gguf_out)
    size_mb = os.path.getsize(args.gguf_out) / (1024 * 1024)
    print(f"  File size: {size_mb:.1f} MB")
    print(f"  SHA-256:   {sha256}")
    print("\nAll done! SFT model is ready for benchmarking.")

if __name__ == "__main__":
    main()
