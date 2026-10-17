"""Check the local MCP protocol; optionally exercise real generation and conversion."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import time
from mcp import Client, StdioServerParameters
from runtime_paths import APP


def payload(result):
    if result.is_error:
        raise RuntimeError(str(result.content))
    if result.structured_content is not None:
        return result.structured_content
    return json.loads(next(part.text for part in result.content if part.type == 'text'))


async def main(generate):
    parameters = StdioServerParameters(command=sys.executable, args=[str(APP/'mcp_server.py')],
        env=dict(os.environ), cwd=APP)
    async with Client(parameters) as client:
        listing = await client.list_tools()
        expected = {'studio_status','start_studio','list_voices','generate_speech','get_job',
                    'convert_audio','add_reference_voice','list_generations','set_output_folder'}
        if {tool.name for tool in listing.tools} != expected:
            raise RuntimeError('Unexpected tool list.')
        status = payload(await client.call_tool('studio_status', {}))
        voices = payload(await client.call_tool('list_voices', {}))
        print(json.dumps({'mcp_tools':len(expected),'studio_ready':status['offline'],
            'voices':len(voices['voices'])}), flush=True)
        if not generate: return
        async def wait(job):
            deadline = time.monotonic() + 1200
            while time.monotonic() < deadline:
                state = payload(await client.call_tool('get_job', {'job_id':job['id']}))
                if state['status'] == 'error': raise RuntimeError(state['message'])
                if state['status'] == 'done':
                    path = Path(state['result']['saved_path'])
                    if not path.is_file() or path.stat().st_size <= 44: raise RuntimeError('Saved audio is missing.')
                    return state['result']
                await asyncio.sleep(2)
            raise TimeoutError('Job still running: ' + job['id'])
        speech = await wait(payload(await client.call_tool('generate_speech',
            {'text':'Welcome to your local voice studio.'})))
        converted = await wait(payload(await client.call_tool('convert_audio',
            {'input_path':speech['saved_path'],'target_voice':'ta_male'})))
        print(json.dumps({'speech_saved':True,'speech_seconds':speech['seconds'],
            'conversion_saved':True,'conversion_seconds':converted['seconds']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate', action='store_true', help='Also generate short speech and convert its voice; writes local audio.')
    args = parser.parse_args()
    asyncio.run(main(args.generate))
