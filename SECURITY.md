# Security and trust boundaries

ZITTOMARK is a local application that downloads third-party code and model files during installation. **No independent security audit has been completed.** Checksums and passing tests establish artifact identity and tested behavior; they do not establish that all upstream code is harmless. Repository stars or forks are not a security certification.

## What the installer changes

Double-click `Install.cmd`, read its plan, and choose whether to continue. The default profile installs English/Tamil speech, conversion, creative English and MCP support. `--basic` omits creative English; `--agents-only` installs just the adapter. `--plan` displays information without downloading or changing files. `--yes` is an explicit noninteractive acceptance of the displayed install plan.

- Downloads a specific Windows x64 **uv 0.11.7** archive from Astral's official GitHub release and checks both the archive and executable against SHA-256 values in `bootstrap-lock.json` before executing it.
- Uses that pinned uv to obtain a private **Python 3.11.15** distribution from Astral's `python-build-standalone`. Python download integrity metadata is supplied by the pinned manager. Python is installed with `--no-bin --no-registry`; it does not replace system Python or add global executable aliases.
- Installs separate speech, creative and MCP environments under `%LOCALAPPDATA%\Zittomark\runtime` (or an explicit `OVS_RUNTIME_ROOT`). Package versions, source archives and accepted artifact hashes are committed in `requirements-*.lock`.
- Requires hashes with dependency resolution disabled; source build tools are also hash pinned. No Git executable is required. Two upstream packages build from pinned, checksum-verified GitHub ZIP archives. Building/installing those packages still executes third-party code. Build isolation is disabled so their build backends come from the reviewed build lock rather than an additional unpinned build environment.
- Uses a single explicit PyPI index and direct hash-checked official PyTorch CUDA wheel URLs. Local pip/uv index overrides are removed from installer subprocess environments. It does not use an additional general-purpose package index.
- Downloads revision/size/SHA-256-pinned models separately from Hugging Face. Model deserialization must still be treated as a trust decision. The app uses restricted PyTorch checkpoint loading where supported.
- Stores local logs and an installation status report in the app's ignored `data` folder. Rerunning reuses verified downloads; there is no automatic update service.

The installer/launchers **do not use PowerShell `ExecutionPolicy Bypass`, change execution policy, edit firewall settings, add a scheduled task/service, require administrator rights, or register an AI agent globally**. Windows' bundled curl, tar and certificate/hash utility are used for bootstrapping. A working NVIDIA GPU driver is a hardware prerequisite; GPU drivers are not silently downloaded or installed. A system where company policy blocks this software should use its approved IT process.

## Review of the reported concerns

| Area | Current behavior | Remaining limitation |
| --- | --- | --- |
| Installation scripts | Native batch bootstrap plus Python installer/launchers; no execution-policy changes | Downloaded executables and Python packages execute with your Windows user permissions |
| Third-party code | Versions, source revisions and hashes pinned; explicit indexes; pinned build tools | An authentic upstream package can still contain vulnerabilities or malicious code; hashes are not an audit |
| Local data | Loopback listener, Host/Origin checks, cross-site browser-read checks and session-token protection for writes | The session token is **not user authentication**. Other processes running as your Windows account can fetch the page/token, text, history, audio and paths, or read your files directly |
| Community verification | Source, lockfiles and tests are published for review | No independent security audit is claimed; popularity metrics do not prove safety |
| External network | Setup deliberately downloads dependencies/models; speech inference uses offline settings plus a Python network guard | The guard is **not an operating-system sandbox** and cannot constrain every native library or child process. OS-level isolation/firewalling is a separate user/admin decision |
| Malicious behavior | The app's intended actions are local speech processing, selected-file reading, saving audio and fixed lifecycle actions | This project cannot guarantee the safety of every dependency or prove the absence of hidden behavior through tests alone |

## Local use and agent access

The server binds to `127.0.0.1`; it has no public URL, cloud upload feature or remote-access tunnel. Do not expose its port to a network. It is intended for a single trusted Windows user, not a shared/multiuser server. Protect your Windows account and the recording/output folders. An external program with that user's file access is outside the app's security boundary.

MCP is a local stdio adapter with named tools. An AI client can receive generation text, paths and metadata it requests; that client's own cloud/privacy settings apply even though speech computation is local. Only use recordings you have permission to use. Do not commit private voices, generated audio, logs or local connection snippets.

For OS-level containment, use a user/admin-managed environment whose GPU and storage support the workload; no sandbox setup is implied by this installer. Offline use is possible after setup, but the project does not claim to be an audited sandboxed appliance.

## Reporting a problem

Do not post credentials, session tokens, private audio or personal paths in a public issue. If GitHub's private vulnerability-reporting feature is enabled for this repository, use it for sensitive security findings; otherwise contact the maintainer through an appropriate private channel before disclosing private details. No private reporting channel or audit service is promised by this file.

References: [Astral uv Python management](https://docs.astral.sh/uv/guides/install-python/), [pinned uv release](https://github.com/astral-sh/uv/releases/tag/0.11.7), and the model/dependency sources in [THIRD_PARTY.md](THIRD_PARTY.md).
