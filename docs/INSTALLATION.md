# Easy Windows installation

1. On the repository page, select **Code → Download ZIP**.
2. Extract the ZIP. Open the extracted folder, not the compressed ZIP view.
3. Double-click **Install.cmd**. Read the download plan and choose **Y**.
4. Wait for **Installation complete**, then double-click **Start-Local-Voice.cmd**.

Python, Git and a PowerShell policy change are not prerequisites. The installer downloads a checked helper, obtains private Python, creates three isolated environments, installs the checked packages, verifies models and runs the GPU/model doctor. Your friend does not need your recordings, local settings or model copies.

## Requirements you still need

- Windows 10/11 on a 64-bit x86 PC; Windows ARM is not packaged here.
- NVIDIA GPU with a working driver. The installer checks this and stops with a message if unavailable. Get driver updates from NVIDIA or the PC maker; the installer does not silently modify drivers.
- Internet during setup, a writable local folder and enough local disk space. Full installation checks for 40 GB free, basic for 20 GB, and adapter-only for 2 GB. Temporary/cache space is included in that budget; long recordings consume additional space over time.
- Windows' built-in curl, tar and certificate/hash utility. If a managed PC blocks them, follow the organization's approved installation process.

## Profiles

| Open/run | Included |
| --- | --- |
| `Install.cmd` | English/Tamil speech, conversion, creative English, MCP |
| `Setup.cmd` or `Install.cmd --basic` | English/Tamil speech, conversion, MCP |
| `Setup-Creative.cmd` | Full profile; also adds creative mode to a basic installation |
| `Setup-Agents.cmd` or `Install.cmd --agents-only` | MCP adapter only; does not install speech models |
| `Install.cmd --plan` | Explanation only; no downloads or changes |

The full/basic profiles generate connection snippets automatically. Follow [AGENT_INTEGRATION.md](AGENT_INTEGRATION.md) to connect Codex, Claude or another client. An adapter-only install needs an existing speech runtime before it can generate audio.

Advanced users can supply `--yes` to accept the displayed installation plan without the confirmation prompt. `OVS_RUNTIME_ROOT` selects an absolute local Windows runtime path; use a short folder such as `C:\VoiceRuntime` if the default is unsuitable. Use the same runtime and port when installing, starting and configuring the adapter. The default is `%LOCALAPPDATA%\Zittomark\runtime`; no system Python, PATH, registry, firewall or agent settings are changed.

## Progress and retry

The terminal shows the current stage. Package/model downloads can take several minutes. The detailed log is `data/logs/install.log`; the latest result is `data/installation.json`. These files can contain local paths and should not be posted publicly without redaction.

If setup is interrupted, close only its installer window and rerun the same profile. Verified cached packages and models are reused; model downloads resume where supported. An integrity mismatch stops installation instead of executing the unverified artifact. Read the error before retrying; do not disable checksum checks or switch to an untrusted mirror to make it proceed.

If startup reports a port conflict, close the other app copy or use a different `OVS_PORT` consistently. Open the local URL shown by the launcher rather than opening `web/index.html` directly. Stop the studio before replacing its code or changing the installed speech packages. Your personal recordings/settings stay in `data`, and chosen output folders are preserved.

See [SECURITY.md](../SECURITY.md) for downloads, trust decisions and remaining privacy limits. A successful installation is not an independent security audit or proof that every dependency is safe.
