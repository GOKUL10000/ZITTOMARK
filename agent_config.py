"""Generate connection snippets locally; never edit an agent's global settings."""
import json
from runtime_paths import APP, RUNTIME


def configs():
    python = (RUNTIME / 'agent-venv' / 'Scripts' / 'python.exe').as_posix()
    script = (APP / 'mcp_server.py').as_posix()
    environment = {'OVS_RUNTIME_ROOT': str(RUNTIME)}
    import os
    for key in ('OVS_URL', 'OVS_PORT'):
        if key in os.environ: environment[key] = os.environ[key]
    entry = dict(command=python, args=[script], env=environment)
    codex = ('[mcp_servers.zittomark]\ncommand = ' + json.dumps(python) + '\nargs = [' +
        json.dumps(script) + ']\nstartup_timeout_sec = 20\ntool_timeout_sec = 180\n' +
        '[mcp_servers.zittomark.env]\n' + ''.join(key + ' = ' + json.dumps(value) + '\n' for key, value in environment.items()))
    return codex, {'mcpServers': {'zittomark': entry}}


if __name__ == '__main__':
    target = APP / 'data' / 'agent-config'
    target.mkdir(parents=True, exist_ok=True)
    codex, generic = configs()
    (target / 'codex-config.toml').write_text(codex, encoding='utf-8')
    (target / 'claude-desktop-config.json').write_text(json.dumps(generic, indent=2), encoding='utf-8')
    (target / 'mcp-config.json').write_text(json.dumps(generic, indent=2), encoding='utf-8')
    print('Connection snippets saved to ' + str(target))
