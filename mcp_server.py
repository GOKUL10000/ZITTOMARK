"""MCP stdio bridge. Only JSON-RPC goes to stdout; no cloud services or API keys."""
from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from studio_client import StudioClient

server = MCPServer('zittomark', version='1.0.0', instructions=(
    'Local Windows speech studio. Start the studio, list voices, submit an asynchronous job, '
    'then poll get_job until done/error. Audio stays on this computer; return saved_path to the user. '
    'Only read or clone recordings the user selected and has permission to use. '
    'History and local paths are private: request them only when needed.'))
client = StudioClient()
READ = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False)


@server.tool(annotations=READ)
def studio_status() -> dict:
    """Get local service readiness without returning generation history or script text."""
    return client.status()


@server.tool(annotations=WRITE)
def start_studio() -> dict:
    """Start this checkout's installed studio locally, without opening a browser."""
    return client.start()


@server.tool(annotations=READ)
def list_voices() -> dict:
    """List voice IDs, feeling names, creative presets and conversion targets."""
    return client.voices()


@server.tool(annotations=WRITE)
def generate_speech(text: str, language: str = 'en', voice: str = 'english_default',
                    feeling: str = 'neutral', strength: float = 0.7, mode: str = 'classic',
                    description: str = '', seed: int = 42) -> dict:
    """Submit speech (1–2000 characters). English en or Tamil ta; use list_voices IDs.

    Creative mode requires its optional model and English. Description controls creative delivery.
    Returns a job ID immediately; poll get_job. One audio job runs at a time.
    """
    return client.generate(text, language, voice, feeling, strength, mode, description, seed)


@server.tool(annotations=READ)
def get_job(job_id: str) -> dict:
    """Poll a submitted UUID job; done includes result.saved_path and local audio_url."""
    return client.job(job_id)


@server.tool(annotations=WRITE)
def convert_audio(input_path: str, target_voice: str) -> dict:
    """Convert a user-selected local audio file (1–300 seconds, <=128 MB) to a listed target.

    WAV/FLAC recommended. Source performance guides emotion. Returns a job ID; poll get_job.
    """
    return client.convert(input_path, target_voice)


@server.tool(annotations=WRITE)
def add_reference_voice(name: str, input_path: str) -> dict:
    """Save a voice from a user-authorized local 3–30 second reference recording.

    The first 15 seconds of normalized audio are kept privately as the reference.
    """
    return client.add_voice(name, input_path)


@server.tool(annotations=READ)
def list_generations(limit: int = 10) -> dict:
    """Explicitly read recent private generation metadata, including text and saved paths."""
    return client.history(limit)


@server.tool(annotations=WRITE)
def set_output_folder(path: str) -> dict:
    """Change where future audio is saved. Use an absolute local folder the user chooses."""
    return client.request('/api/storage', {'directory': path})


if __name__ == '__main__':
    server.run(transport='stdio')
