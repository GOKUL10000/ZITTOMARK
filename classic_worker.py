"""One-job Chatterbox inference isolated from the local UI server."""
import json
import os
from pathlib import Path
import sys
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1', DO_NOT_TRACK='1')
from offline_network import enforce_local_network
enforce_local_network()

if __name__ == '__main__':
    request = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    if request.get('cpu_only'):
        os.environ['OVS_CPU_ONLY'] = '1'
    from engine import VoiceEngine
    import soundfile as sf
    engine = VoiceEngine()
    audio, rate = engine.synthesize(request['text'], request['language'], request['voice_id'],
        Path(request['reference']) if request.get('reference') else None, request['expression'],
        request['seed'], lambda message: print('STUDIO:' + message, flush=True), feeling=request['feeling'])
    sf.write(request['output'], audio, rate, subtype='PCM_16')
    print('STUDIO:Audio saved.', flush=True)
