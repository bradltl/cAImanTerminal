# Optional local GPU acceleration

GPU offloading is an opt-in performance option for the existing verified local
GGUF pipeline. CPU remains the default and does not require a GPU SDK. It does
not change assistance policy, output validation, explicit acceptance, or the
requirement for a separate physical Enter to execute a staged command.

## Build and enable

The pinned `llama-cpp-2 = 0.1.156` exposes Vulkan and CUDA features; cAIman selects
them at build time without changing dependency versions or downloading a model.
The ordinary build is unchanged:

```sh
cargo build --release --locked
```

For Linux Vulkan, install the Vulkan loader/development headers, `glslc`, and
SPIR-V headers, plus the normal native build dependencies. Debian/Ubuntu package
names are `libvulkan-dev glslc spirv-headers`. A compatible local GPU driver is
also required at runtime; verify its availability with `vulkaninfo` (often in a
separate `vulkan-tools` package). This follows the
[upstream llama.cpp Vulkan build instructions](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md#vulkan).

```sh
cargo build --release --locked --features gpu-vulkan
```

For a separately provisioned NVIDIA CUDA toolkit and driver:

```sh
cargo build --release --locked --features gpu-cuda
```

CUDA compiler/driver compatibility remains a host installation requirement;
consult the [upstream CUDA build instructions](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md#cuda).
Prefer one backend per build. Enabling both selects the first compatible hardware
GPU in the native backend's enumeration; multi-GPU placement is not exposed.

Open Settings → Model & runtime, enable **GPU offloading when available**, set
**Requested GPU layers**, save, and relaunch. Settings show compiled backend
capability only; opening the window does not initialize a driver or load weights.
The equivalent persisted fields inside `inference` are:

```json
{
  "gpu_offload": true,
  "gpu_layers": 32
}
```

Old settings retain CPU behavior. The layer count must be 1–256 (default 32);
disable offloading for CPU-only operation. A larger request is not necessarily
faster and may exceed available memory. Layer placement is ultimately chosen by
llama.cpp, so the configured count is not an actual-offload measurement.

## Selection, fallback, and trust boundary

Only a compiled Vulkan/CUDA backend reporting a GPU or integrated GPU is selected.
Software Vulkan renderers reporting a CPU are not treated as GPU acceleration.
Missing backend/device uses CPU, with GPU model layers and context operation/KQV
offload disabled. The explicitly disabled setting does the same even in a
GPU-capable build.

The helper first verifies and seals the model file, then loads it on the selected
device. A recoverable GPU model-load or empty-context allocation error triggers
one CPU preparation attempt with that same verified descriptor, before any prompt
is decoded. Native driver crashes, hangs, or later generation allocation failures
remain bounded supervised failures; no automatic model inference retry is added.
The native library cannot safely recover from every driver failure in-process.
Missing mandatory GPU shared libraries can prevent a GPU-built executable from
starting at all; keep a CPU build available on such hosts.

Weights remain resident in the supervised helper. Each request creates fresh KV
state. Model-file verification, host checks, cancellation, timeout supervision,
request isolation, and local-only operation remain in effect. No SDK, driver,
model, or remote inference service is downloaded or contacted by cAIman.

`ModelBackend::runtime()` returns no selection before model load. After loading,
the helper reports content-free `InferenceRuntime` metadata across its existing
bounded IPC: backend, status, and requested layers. Status distinguishes disabled
CPU, unavailable GPU, requested offload, and CPU fallback. “Offload requested” is
deliberate wording: no measurement of actual per-tensor placement or GPU activity
is exposed by this integration. A deterministic answer may not load a model at
all and must not be reported as GPU inference.
Headless `--ask` includes this metadata as `runtime`, or `null` when no model was
loaded; its normal deterministic path is tested with deliberately invalid model
bytes to ensure it cannot falsely report GPU/model use.

## Verification and performance comparison

```sh
cargo test --locked --no-default-features --test settings_contract
cargo test --locked --lib inference::tests
cargo test --locked --lib model_process::tests
cargo test --locked --no-default-features --features gpu-vulkan --lib inference::tests
cargo test --locked --features gpu-vulkan --test gpu_runtime -- --ignored --nocapture
```

Tests cover default/migrated preferences, bounds, persistence, unknown fields,
explicit opt-in, real-versus-software device classification, unsupported backend
fallback, GPU preparation failure followed by CPU preparation, and no repeated
CPU failure retry. Existing supervised cancellation/deadline checks are retained.
The ignored `gpu_runtime` smoke loads the digest-verified GGUF with CPU and
requested GPU settings, validates the same synthetic request in two sessions per
mode, and checks pre-decode cancellation. It never executes a suggested command.

Hardware acceptance additionally requires running the verified model on an actual
device with offloading enabled and disabled, checking runtime selection, validating
the same response corpus, and exercising cancellation and cross-session isolation.
Do not infer correctness parity or acceleration from a successful feature build.

Use the benchmark's `CAYMAN_BENCH_MODEL_PATH=1` to measure actual generation rather
than deterministic shortcuts, and `CAYMAN_BENCH_GPU_OFFLOAD=1` with
`CAYMAN_BENCH_GPU_LAYERS=32` to request offload. Compare the same release build,
verified model, corpus, and context/output settings; report loading, prompt
processing, decoding, failures, and complete validated-response latency separately.
The benchmark's requested mode and compiled-backend fields are configuration, not
proof of device use. Latency is diagnostic, not an alpha release threshold; do not
count failed or unverifiable responses as useful fast answers.

The implementation environment has the Vulkan loader and `glslc`, but its SDK
headers and `/dev/dri` hardware device are absent. Initial feature compilation
correctly failed with missing Vulkan headers. Building official Vulkan-Headers
v1.4.357 and SPIRV-Headers vulkan-sdk-1.4.341.0 into a temporary local prefix then
allowed the Vulkan feature to compile and its selection/fallback unit tests to
pass. No system package installation was needed. A dedicated PR/branch CI job
builds the Vulkan feature with development packages and runs those tests; it is
not a hardware benchmark.

The verified-model smoke passed in both CPU-only and Vulkan-linked builds, each
with disabled-offload and requested-but-unavailable modes, two independently
validated synthetic sessions per mode, and cancellation checks. Physical GPU
inference, CUDA compilation,
numerical parity, and speedup are not claimed. See
[alpha conformance](14_Alpha_Conformance.md) for the correctness-first acceptance
policy.
