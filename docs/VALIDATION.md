# Validation scope

## Automatic installer update · 20 October 2026

The Windows installer was exercised in a **new isolated runtime folder on the author's NVIDIA Windows PC**. It downloaded the checksum-verified uv helper, obtained its own private Python 3.11.15, created new classic/creative/MCP environments, and fetched/installed the locked dependencies with hash checking enabled. The two source packages built successfully from pinned ZIP archives without requiring Git.

All three environments passed dependency compatibility checks. The complete installer verified model files, prepared creative shards, and passed the GPU/model doctor. Existing pinned model files were reused through test-local hard links to avoid downloading many GB of identical weights again; this was **not a fresh model download or a clean installation on a second PC**. Shared model source files were not modified. No personal reference recordings were copied into the new runtime or published.

Checks completed:

- **30 automated tests passed**, including helper tamper rejection, checksum-lock coverage, custom index isolation, owned-app identity, feeling/tag parsing, normalized audio limits, long-conversion window coverage, persistent output paths and model sharding.
- The native batch bootstrap downloaded private Python with `--no-bin --no-registry`; repeated adapter installation reused the verified runtime and dependencies. Injected custom uv download/index settings were cleared by the installer.
- `Install.cmd --plan` displayed information without downloads or file changes.
- The Python launcher started/reused/stopped the test app on port 7866. It required no PowerShell execution-policy bypass. Cross-site browser reads of API state were rejected.
- An official MCP SDK client listed all nine tools and generated speech, polled completion and converted the generated audio through the fresh environments. Both WAV files were saved. The adapter's `start_studio`, status and voices calls also passed.
- Short Tamil and creative English jobs produced finite, non-silent 24 kHz audio using the fresh speech environments. This confirms generation/output validation, not independent listening/transcription accuracy or guaranteed voice similarity.
- Native `.cmd` start/stop commands passed using the fresh private runtime.
- Machine-specific connection snippets, private audio, weights, environments, logs and test reports were excluded by the source-package allowlist and Git ignore rules.

The original five-minute conversion path was previously exercised with a full 300-second recording. This release retains that bounded conversion implementation; the installer update did not repeat the full five-minute GPU conversion.

Codex/Claude connection instructions follow their official MCP documentation. Protocol tests do not establish that both vendor clients are registered on every user's PC; follow the connection checks in AGENT_INTEGRATION.md. Global agent settings were not edited automatically.

## Limits

No independent security audit, dependency-safety guarantee, OS sandbox, support for every GPU/driver combination, or clean second-PC installation is claimed. Review [SECURITY.md](../SECURITY.md). The supported packaged target is Windows 10/11 x64 with a working NVIDIA driver. This repository supplies source and an automatic dependency installer, not a self-contained offline executable.
