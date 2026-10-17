"""Validate browser-normalized conversion uploads before they reach a model."""
import base64
import io
import math
import re

MAX_SOURCE_SECONDS = 300

def decode_source(encoded):
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly
    if not isinstance(encoded, str) or len(encoded) > 24 * 1024 * 1024 * 4 // 3 + 4:
        raise ValueError('Choose an audio file smaller than 24 MB.')
    try:
        raw = base64.b64decode(encoded, validate=True)
        if raw[:4] != b'RIFF' or raw[8:12] != b'WAVE':
            raise ValueError('Use the studio upload or recorder to prepare a WAV clip.')
        info = sf.info(io.BytesIO(raw))
        if not 8000 <= info.samplerate <= 192000 or info.channels not in (1, 2):
            raise ValueError('Use a mono or stereo recording at a standard sample rate.')
        if not 1 <= info.duration <= MAX_SOURCE_SECONDS + .01:
            raise ValueError('Use an audio clip between 1 second and 5 minutes long.')
        audio, rate = sf.read(io.BytesIO(raw), frames=round(info.samplerate * (MAX_SOURCE_SECONDS + .01)) + 1,
                              dtype='float32', always_2d=True)
        if not 1 <= len(audio) / rate <= MAX_SOURCE_SECONDS + .01:
            raise ValueError('Use an audio clip between 1 second and 5 minutes long.')
    except ValueError:
        raise
    except Exception:
        raise ValueError('This audio could not be read. Try another WAV, MP3 or M4A file.') from None
    audio = np.mean(audio, axis=1)
    if not np.isfinite(audio).all() or float(np.sqrt(np.mean(audio ** 2))) < .0005:
        raise ValueError('This clip is silent, too quiet or invalid. Try a clear speech recording.')
    divisor = math.gcd(rate, 24000)
    audio = resample_poly(audio, 24000 // divisor, rate // divisor).astype('float32')
    return np.clip(audio, -1, 1), 24000

def source_label(value):
    value = re.split(r'[/\\]', str(value))[-1]
    return re.sub(r'[\x00-\x1f\x7f]', '', value).strip()[:100] or 'Audio recording'
