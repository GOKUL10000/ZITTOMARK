# Working with ZITTOMARK

This is a Windows, local-only speech application. Read README.md and docs/AGENT_INTEGRATION.md before configuring or using it. To control the installed app, prefer its named MCP tools or `studio_cli.py`; do not invent a cloud speech endpoint.

## Source map

- `server.py`: loopback HTTP/UI, job dispatch and voice metadata.
- `engine.py`, `classic_worker.py`: English/Tamil Chatterbox generation.
- `creative_worker.py`, `creative.py`: optional Qwen English design and direction parsing.
- `conversion_worker.py`, `conversion_audio.py`, `conversion_segments.py`: direct speech conversion and bounded long-audio handling.
- `output_storage.py`: persistent local output paths and previous-folder history.
- `web/`: static interface; serve it through the Python server.
- `runtime_paths.py`, setup/launch scripts: portable per-user runtime and lifecycle.
- `studio_client.py`, `studio_cli.py`, `mcp_server.py`: shared HTTP client, JSON CLI and official MCP stdio adapter.

## Development rules

Keep the loopback bind, Host/Origin/session-token protections, and offline inference guard. Do not open public ports, add tunneling, run arbitrary agent-provided shell commands, or log session tokens. Use separate classic, creative and MCP environments so their dependencies do not conflict. Setup/downloads can be online; inference must stay local.

Never commit `data/`, recordings, generated audio, saved voice metadata, machine-specific agent snippets, local paths/usernames, model weights, venvs, logs, caches, or credentials. Models use revision/size/hash manifests and download separately. Do not bundle commercial voice samples or claim exact likeness/emotion.

Use UUID job IDs and structured arguments, bound uploaded audio/text, preserve all words in long conversions, and return concrete saved output paths. Ask for file/reference choices when missing; use only recordings the user authorizes. Do not modify agent global settings unless the user requests that registration.

Run the classic Python environment with `-m unittest discover -s tests -v`, run `doctor.py`, and verify changed routes/tools. Unit tests use workspace-local temporary directories. MCP stdout must contain only protocol traffic; diagnostics belong on stderr. Live smoke checks use `OVS_PORT=7866` to avoid interrupting an existing app on 7865; stop only the app copy you started.
