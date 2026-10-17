# ZITTOMARK · Local Voice Studio

A Windows voice studio that generates speech in **English and Tamil**, designs expressive English voices, and converts recorded speech to a selected voice. Use its browser interface, or connect **Codex, Claude, another MCP client, a local script, or an HTTP tool**.

Speech runs on your computer after the initial package/model downloads. No cloud speech account, API key, monthly credits, or hosted service is required.

## Install on a friend's Windows PC

1. Install **64-bit Python 3.11** from [python.org](https://www.python.org/downloads/release/python-3119/) and [Git for Windows](https://git-scm.com/download/win). Enable Python's launcher/PATH options. Update the NVIDIA driver.
2. Download this repository using **Code → Download ZIP**, then extract it to a writable local folder. Keep all files together; avoid installing inside Program Files.
3. Double-click **`Setup.cmd`**. This installs a private Python environment and downloads the pinned English/Tamil models. Allow it to finish; the first setup needs internet access and several GB of downloads.
4. Double-click **`Start-Local-Voice.cmd`**. Open **http://127.0.0.1:7865/** if the browser does not open. Use **`Stop-Local-Voice.cmd`** when finished.
5. Optional: run **`Setup-Creative.cmd`** for English creative voice design and custom delivery tags. This adds a separate model/environment and substantial downloads.
6. Optional: run **`Setup-Agents.cmd`** for MCP support, then follow [Connect an AI tool](docs/AGENT_INTEGRATION.md).

### Hardware and storage

The supplied setup targets **64-bit Windows, an NVIDIA CUDA GPU, and Python 3.11**. It was exercised on an RTX 5060. Budget **40 GB of free disk space** for both speech environments, models, caches, and temporary creative-model shards; actual use depends on options and pip caches. Large models also use system memory/pagefile space. Performance and memory requirements vary; CPU compatibility fallback is slow and is not the supported first-install target. macOS, Linux, AMD, and Intel GPU installation are not packaged here.

The private runtime defaults to `%LOCALAPPDATA%\Zittomark\runtime`. Packages do not replace system Python packages. Generated audio, saved reference voices, logs, and settings live in this extracted app's `data` folder. Change **Save generations to** in the app to choose another local folder. Older generations stay where they were saved.

An optional `OVS_RUNTIME_ROOT` environment variable selects a different absolute runtime path; `OVS_PORT` selects a local port. Set these consistently when running setup, the studio, and the agent adapter. A short local runtime path helps avoid Windows path length errors. Copies using the same default port must not run simultaneously.

## Use the studio

- **Text to speech:** select English or Tamil, choose a built-in or saved reference voice, type text, and generate. Maximum 2,000 characters per request.
- **Feelings:** supported tags such as `[happy]`, `[sad]`, and `[neutral]` change the following section. In saved-voice mode these are approximate pitch/pace/delivery adjustments, not a guaranteed emotional performance.
- **Creative voice:** optional English model; describe timbre, mood and delivery, or use custom tags. Creative design does not use the saved-voice selector and does not guarantee the same identity across passages. It does not support Tamil in this app.
- **Voice conversion:** upload 1 second–5 minutes of audio, up to 128 MB, or record up to 30 seconds. The browser decodes supported formats to mono WAV. Conversion changes the voice directly; it does not translate the words. Use clean speech without music for better clarity.
- **Add a voice:** supply a clear, authorized 3–30 second recording. The first 15 seconds are retained as the reference. Similarity, pronunciation, pacing and nuance vary with model and recording quality.
- **Save folder:** the selected folder is shown in the app and persists across restarts. New speech and conversions save there as WAV plus JSON metadata. Settings do not move previous recordings.

**Open the app through its local web address.** Opening `web/index.html` as a file does not run the server and can show an unstyled or nonfunctional page. The file-entry script points to the default local server.

This is an independent local app, not ElevenLabs offline. No ElevenLabs/TTSVibes service code, commercial voice models, Natasha/Trickster samples, private references, generated recordings, credentials, or model weights are included. Built-in models download from their upstream authors during setup. Use voices and recordings you have permission to use.

## Codex, Claude and other tools

[Agent integration instructions](docs/AGENT_INTEGRATION.md) cover MCP, Codex configuration, Claude Desktop/Claude Code, the JSON command-line interface and REST API. MCP jobs return immediately with an ID; poll the job until it finishes, then use its `saved_path`.

```powershell
# Any local tool with Python/shell support can use the JSON CLI.
python studio_cli.py status
python studio_cli.py voices
python studio_cli.py generate --text "Hello from my local voice studio." --wait
python studio_cli.py generate --text "வணக்கம்" --language ta --voice ta_female --wait
python studio_cli.py convert "C:\Audio\performance.wav" --target english_default --wait
```

The CLI itself uses only Python's standard library. Conversion normalization uses the private speech environment installed by Setup. This is a local REST/MCP interface, not an OpenAI chat-completions endpoint. Cloud-only tools need a local bridge; the studio deliberately has no public listener or tunnel.

## Privacy and security

The server binds to `127.0.0.1`, validates Host/Origin, and requires a session token for writes. The adapter connects only to a literal loopback address, disables HTTP proxies and rejects redirects. Local inference blocks non-loopback network connections. Setup is online and downloads executable Python dependencies and model files; review the pinned lockfiles, manifests and [third-party notices](THIRD_PARTY.md). The session token is a browser-request protection, not user authentication: other processes on your Windows account can access this local service.

The adapter exposes only named speech, voice, folder and status actions; it has no arbitrary command execution tool. Your AI client can still receive the text, paths and tool results it requests; its own privacy settings apply. Generated connection snippets contain your local paths and are ignored by Git. No agent's global configuration is changed automatically.

Model downloads are revision-pinned and checked against file size and SHA-256. PyTorch/model loading still requires trusting upstream artifacts. Setup does not change firewall rules, create a service, enable remote access or install automatic startup. Stop the app before replacing its code.

## Checks and limitations

```powershell
# Use the installed classic environment for all speech-related tests.
& "$env:LOCALAPPDATA\Zittomark\runtime\.venv\Scripts\python.exe" -m unittest discover -s tests -v
& "$env:LOCALAPPDATA\Zittomark\runtime\.venv\Scripts\python.exe" doctor.py
```

See [Validation notes](docs/VALIDATION.md) for what was tested. A clean install on every Windows/GPU combination is not implied. The code is shared as source with setup scripts, not a standalone executable. [Development guidance](AGENTS.md) explains the structure and test commands.

MIT license for this application. Dependencies and models retain their own licenses; see [THIRD_PARTY.md](THIRD_PARTY.md).
