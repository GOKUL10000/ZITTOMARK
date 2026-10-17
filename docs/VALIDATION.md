# Validation scope

The sharing build is checked with pinned, already installed Python/model environments on its author's Windows NVIDIA PC. This verifies portable paths, prerequisites, API behavior and the stdio protocol; it does not replace a clean install on a different PC.

Automated tests cover voice tags, custom creative directions, audio normalization and duration limits, long conversion window coverage, persistent output paths, local HTTP client restrictions and model sharding. The agent protocol smoke test initializes an official MCP SDK client, lists the tools and calls the local app. Live checks submit short speech/conversion jobs and verify saved audio.

Sharing-build checks completed on Windows:

- All **26 unit tests passed** using the classic environment.
- PowerShell scripts parsed; prerequisite checking passed under Windows PowerShell 5.1, which the `.cmd` launchers use.
- The GPU/model doctor passed using the pinned installed environments, including creative readiness.
- The official MCP SDK client listed all **nine tools**, called status/voices, submitted speech, polled completion, and converted its generated recording to a built-in target voice. Both WAV files were saved.
- Short Tamil and creative English jobs produced finite, non-silent 24 kHz audio in the portable checkout.
- Generated Codex TOML and Claude JSON configuration snippets parsed and agreed on the adapter executable. They were not installed into the user's global AI-client settings.
- The separate agent environment installed from its lock file using Windows PowerShell. Its MCP client successfully called `start_studio`, status and voices; startup logs use files to avoid inherited Windows pipe handles keeping the tool call open.
- The repository/ZIP allowlist excludes private data, recordings, model weights, caches, logs and local connection snippets.

The source application's five-minute conversion path was previously exercised with a full 300-second recording. This release retains that same bounded conversion implementation. Five-minute processing time varies with hardware. No private test recordings, generated files or machine-specific reports are published.

Codex and Claude connection instructions follow their official MCP documentation. A protocol test does not establish that both vendor clients have been registered on every user's computer; follow the connection checks in AGENT_INTEGRATION.md. Fresh package/model downloads and clean installation on a second PC have not been independently tested.
