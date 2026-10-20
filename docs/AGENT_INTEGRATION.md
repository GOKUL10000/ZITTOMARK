# Connect an AI tool

First install and start the speech app using the README. Both `Install.cmd` and the smaller `Setup.cmd` profile include MCP automatically. To add only MCP to an existing installation, run `Setup-Agents.cmd`. A **separate** `agent-venv` uses the pinned official Python MCP SDK; no AI client's global settings are changed automatically. The initial bootstrap obtains private Python automatically without requiring a manual Python/Git installation.

Setup generates three local snippets in **`data/agent-config`**, with the correct absolute paths for this PC. Regenerate them by running `agent_config.py` if you move the repository or change its runtime/port. Do not share these machine-specific snippets as your friend's settings; your friend runs their own setup.

## Codex

Open `data/agent-config/codex-config.toml` and copy its `mcp_servers.zittomark` section and environment subsection into your existing Codex `config.toml` (normally `%USERPROFILE%\.codex\config.toml`). Merge the section without replacing your other settings. Restart/reconnect Codex, then inspect its MCP tools (`codex mcp list` in the CLI, or `/mcp` in an interactive Codex session).

The generated section uses this structure:

```toml
[mcp_servers.zittomark]
command = "C:/path/to/runtime/agent-venv/Scripts/python.exe"
args = ["C:/path/to/ZITTOMARK/mcp_server.py"]
startup_timeout_sec = 20
tool_timeout_sec = 180
```

Use the generated file for real paths and its environment entries. Codex also supports `codex mcp add` for stdio commands; see [official Codex MCP instructions](https://learn.chatgpt.com/docs/extend/mcp).

## Claude Desktop

Merge the `zittomark` entry from `data/agent-config/claude-desktop-config.json` into the `mcpServers` object in `%APPDATA%\Claude\claude_desktop_config.json`. Keep other servers and settings. Restart Claude Desktop and check that ZITTOMARK tools appear.

```json
{
  "mcpServers": {
    "zittomark": {
      "command": "C:/path/to/runtime/agent-venv/Scripts/python.exe",
      "args": ["C:/path/to/ZITTOMARK/mcp_server.py"]
    }
  }
}
```

## Claude Code

Use the actual absolute paths from the generated JSON:

```powershell
claude mcp add --transport stdio zittomark -- "C:/path/to/runtime/agent-venv/Scripts/python.exe" "C:/path/to/ZITTOMARK/mcp_server.py"
claude mcp list
```

If using a nondefault runtime/port, include the generated `env` values in the client's configuration, or use Claude's documented `--env NAME=value` options before the server name. Follow [Claude Code's official MCP documentation](https://code.claude.com/docs/en/mcp) for configuration scope and client permissions.

## Any other MCP client

Choose a **local stdio server**. Use the `command`, `args`, and `env` from `data/agent-config/mcp-config.json`. The bridge uses the [official MCP protocol](https://modelcontextprotocol.io/docs/develop/build-server), not vendor-specific chat APIs. A tool must support local MCP stdio to connect directly. Do not paste the local web URL into an MCP HTTP URL field; the HTTP server is the app's REST API.

Available tools:

| Tool | Purpose |
| --- | --- |
| `start_studio` | Start this installed app without opening the browser |
| `studio_status` | Read readiness and busy status |
| `list_voices` | Read voice IDs, conversion targets, feelings, presets |
| `generate_speech` | Submit English/Tamil speech or English creative design |
| `convert_audio` | Convert a selected local 1–300 second audio file |
| `get_job` | Poll until `done` or `error`; get the output path |
| `add_reference_voice` | Save a selected, authorized 3–30 second recording |
| `list_generations` | Explicitly read recent private metadata, text and paths |
| `set_output_folder` | Change the destination for future generations |

Example instruction for your agent:

> Use ZITTOMARK. Start the studio if needed, list its voices, and generate “Welcome to my studio” using the English original voice with a happy feeling. Poll the job until it finishes and give me the saved WAV path.

For conversions, explicitly provide the local file path and target voice. For creative delivery, choose `mode="creative"`, `language="en"`, and a description such as “A sly, playful storyteller with a low, whispery voice and clearly articulated words.” Feelings and similarity are approximate; see the README.

Jobs are asynchronous so generation does not keep an MCP tool call open for several minutes. Call `get_job` at sensible intervals (for example every 2–5 seconds). Only one audio job runs at once; a second submission returns a busy error. Job state is in memory and disappears when the app restarts; completed recordings remain on disk and in history. For an independent studio session, start it with `Start-Local-Voice.cmd` before connecting. A client's process cleanup on disconnect can stop a studio it launched.

## Command line and HTTP tools

`studio_cli.py` provides JSON commands for a local agent with shell access. It uses standard-library HTTP and needs no MCP installation. Run `python studio_cli.py --help`; the README includes examples. `--wait` polls up to 30 minutes. Errors go to stderr and use a nonzero exit code.

For HTTP integrations, see [API reference](API.md) and [OpenAPI specification](openapi.json), also served at `/api/openapi.json`. POST requests need `X-Studio-Token`; `studio_client.py` handles bootstrapping and refreshing it. Do not log or share it. Local audio normalization uses the installed classic environment. WAV/FLAC are recommended for agent uploads; formats depend on libsndfile support. The browser supports additional formats through browser decoding.

The service remains loopback-only. A cloud-only AI website cannot directly read your PC's local files or reach its `127.0.0.1` address. Use that product's supported local client/bridge rather than exposing the studio publicly. No OpenAI, Anthropic, ElevenLabs or other cloud API credentials are needed by this app.

## Verify your connection

After connecting, request `studio_status` and `list_voices`. Then submit one short speech job, poll it, and confirm the WAV exists at `result.saved_path`. These calls verify both registration and generation. A config snippet alone does not prove that a particular client's connection works. The repository's MCP protocol test uses the official SDK; actual Codex/Claude registration depends on your installed client and configuration.

You can also run the included protocol check using the agent environment:

```powershell
& "$env:LOCALAPPDATA\Zittomark\runtime\agent-venv\Scripts\python.exe" agent_smoke.py
# Optional real speech + conversion check, which saves two local audio files:
& "$env:LOCALAPPDATA\Zittomark\runtime\agent-venv\Scripts\python.exe" agent_smoke.py --generate
```
