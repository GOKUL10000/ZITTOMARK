"""Native Chatterbox speech-to-speech conversion using local S3Gen weights."""
import json
import os
from pathlib import Path
import sys

os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1', DO_NOT_TRACK='1')
from offline_network import enforce_local_network
from conversion_segments import encoding_windows
enforce_local_network()

def main():
    import numpy as np
    import soundfile as sf
    import torch
    import librosa
    from chatterbox.vc import ChatterboxVC
    from chatterbox.models.s3gen import S3Gen
    request = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    torch.set_num_threads(6)
    torch.manual_seed(42)
    if not torch.cuda.is_available():
        raise RuntimeError('The NVIDIA voice runtime is unavailable.')
    print('STUDIO:Loading the offline voice conversion model…', flush=True)
    from runtime_paths import RUNTIME
    base = RUNTIME / 'models' / 'base'
    with torch.device('cuda'):
        decoder = S3Gen()
    state = torch.load(base / 's3gen.pt', map_location='cpu', weights_only=True, mmap=True)
    decoder.load_state_dict(state, strict=True)
    del state
    decoder = decoder.to('cuda').eval().requires_grad_(False)
    conditioning = None
    if request.get('conditioning'):
        conditioning = torch.load(request['conditioning'], map_location='cpu', weights_only=True)['gen']
    model = ChatterboxVC(decoder, 'cuda', ref_dict=conditioning)
    torch.cuda.empty_cache()
    print('STUDIO:Converting your performance to the selected voice…', flush=True)
    with torch.inference_mode():
        if request.get('reference'):
            model.set_target_voice(request['reference'])
        source, _ = librosa.load(request['source'], sr=16000)
        source_frames = len(source)
        windows = list(encoding_windows(source_frames))
        encoded = []
        for number, (begin, end, first, count) in enumerate(windows, 1):
            print(f'STUDIO:Reading audio section {number} of {len(windows)}…', flush=True)
            section = torch.from_numpy(source[begin:end]).float().to('cuda')
            padded = decoder.tokenizer.pad([section], 16000)
            section_tokens, _ = decoder.tokenizer(padded)
            core = section_tokens[:, first:first + count]
            if core.shape[-1] != count:
                raise RuntimeError('An audio section was incomplete. Try another recording.')
            encoded.append(core.cpu())
            del section, padded, section_tokens, core
        tokens = torch.cat(encoded, dim=-1).to('cuda')
        del encoded, source
        # Decode bounded overlapping sections. Source encoding above is also
        # bounded, so a five-minute input never becomes one large GPU sequence.
        block, overlap = 150, 6  # 25 tokens/s: 6 seconds, 240 ms overlap.
        stride = block - overlap
        chunks = []
        starts = [start for start in range(0, tokens.shape[-1], stride) if start == 0 or start + overlap < tokens.shape[-1]]
        total_sections = next((i + 1 for i, start in enumerate(starts) if start + block >= tokens.shape[-1]), len(starts))
        for start in starts:
            print(f'STUDIO:Converting section {len(chunks) + 1} of {total_sections}…', flush=True)
            wav, _ = decoder.inference(speech_tokens=tokens[:, start:start + block], ref_dict=model.ref_dict)
            chunks.append(wav.detach().cpu().numpy().reshape(-1).astype('float32'))
            if start + block >= tokens.shape[-1]:
                break
        audio = chunks[0]
        fade_samples = round(overlap / 25 * model.sr)
        for chunk in chunks[1:]:
            length = min(fade_samples, len(audio), len(chunk))
            weight = np.linspace(0, 1, length, dtype='float32')
            transition = audio[-length:] * (1 - weight) + chunk[:length] * weight
            audio = np.concatenate((audio[:-length], transition, chunk[length:]))
        audio = audio[:round(source_frames * model.sr / 16000)]
        audio = np.asarray(model.watermarker.apply_watermark(audio, sample_rate=model.sr), dtype='float32')
    if not np.isfinite(audio).all() or len(audio) < model.sr // 2 or float(np.sqrt(np.mean(audio ** 2))) < .0001:
        raise RuntimeError('The model returned invalid audio. Try a clear speech clip.')
    peak = float(np.max(np.abs(audio)))
    if peak > .99:
        audio *= .99 / peak
    sf.write(request['output'], audio, model.sr, subtype='PCM_16')
    print('STUDIO:Converted audio is ready.', flush=True)

if __name__ == '__main__':
    main()
