"""Decode a chosen local file inside the speech environment; emit normalized WAV JSON."""
import argparse
import base64
import io
import json
import math
from pathlib import Path
import sys


def normalize(path, reference=False):
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly
    source = Path(path).resolve(strict=True)
    if not source.is_file() or source.stat().st_size > 128 * 1024 * 1024:
        raise ValueError('Choose an audio file up to 128 MB.')
    info = sf.info(source)
    minimum, maximum = (3, 30) if reference else (1, 300)
    if not minimum <= info.duration <= maximum or not 1 <= info.channels <= 8 or not 8000 <= info.samplerate <= 192000:
        raise ValueError(f'Use {minimum}–{maximum} seconds of audio, 1–8 channels, and 8–192 kHz.')
    # Bound memory before decoding, including unusually high channel counts/rates.
    if info.frames * info.channels > 60_000_000:
        raise ValueError('Decoded audio is too large. Export a mono or stereo WAV first.')
    audio, rate = sf.read(source, dtype='float32', always_2d=True)
    audio = np.mean(audio, axis=1)
    if not np.isfinite(audio).all():
        raise ValueError('The audio contains invalid samples.')
    divisor = math.gcd(rate, 24000)
    audio = resample_poly(audio, 24000 // divisor, rate // divisor)
    output = io.BytesIO()
    sf.write(output, audio, 24000, format='WAV', subtype='PCM_16')
    return dict(audio=base64.b64encode(output.getvalue()).decode('ascii'), seconds=len(audio) / 24000)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--reference', action='store_true')
    mode.add_argument('--conversion', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(normalize(args.path, args.reference)))
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
