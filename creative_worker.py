"""Isolated one-job inference worker; exits to release all GPU memory."""
import json
import os
from pathlib import Path
import sys

os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1', DO_NOT_TRACK='1', TOKENIZERS_PARALLELISM='false')
from offline_network import enforce_local_network
enforce_local_network()

def main():
    import numpy as np
    import soundfile as sf
    import torch
    import safetensors
    # Windows charges whole copy-on-write mmap files against its commit limit.
    # The official pread backend reads each tensor on demand instead.
    from qwen_tts import Qwen3TTSModel
    def low_memory_open(*args, **kwargs):
        kwargs['backend'] = 'pread'
        return safetensors.safe_open(*args, **kwargs)
    # Apply after Qwen's imports have completed to avoid lazy-module aliases.
    sys.modules['transformers.modeling_utils'].safe_open = low_memory_open
    sys.modules['transformers.modeling_utils'].caching_allocator_warmup = lambda *args, **kwargs: None
    from runtime_paths import RUNTIME
    request = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    torch.set_num_threads(6)
    torch.manual_seed(request['seed'])
    model = Qwen3TTSModel.from_pretrained(
        str(RUNTIME / 'models' / 'qwen-design-sharded'),
        device_map='cuda:0', dtype=torch.bfloat16, attn_implementation='sdpa', local_files_only=True)
    print('Creative voice model loaded; shaping your performance…', flush=True)
    chunks, rate = [], 24000
    previous_speech = False
    with torch.inference_mode():
        for index, section in enumerate(request['sections']):
            if section['kind'] == 'pause':
                chunks.append(np.zeros(round(section['seconds'] * rate), dtype=np.float32))
                previous_speech = False
                continue
            if previous_speech:
                chunks.append(np.zeros(round(.18 * rate), dtype=np.float32))
            print(f'Creating creative passage {index + 1} of {len(request["sections"])}…', flush=True)
            wavs, rate = model.generate_voice_design(text=section['text'], language='English',
                instruct=section['direction'], max_new_tokens=1200)
            chunks.append(np.asarray(wavs[0], dtype=np.float32).reshape(-1))
            previous_speech = True
    audio = np.concatenate(chunks)
    if not np.isfinite(audio).all() or not len(audio) or float(np.sqrt(np.mean(audio ** 2))) < .0001:
        raise RuntimeError('The voice model returned empty or invalid audio. Try another description.')
    peak = float(np.max(np.abs(audio)))
    if peak > .99:
        audio *= .99 / peak
    sf.write(request['output'], audio, rate, subtype='PCM_16')
    print('Creative audio saved.', flush=True)

if __name__ == '__main__':
    main()
