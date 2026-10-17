"""Bound source encoding memory while retaining context at section boundaries."""
from math import ceil

TOKEN_HOP = 640  # 16 kHz / 25 acoustic tokens per second.

def encoding_windows(frame_count, core_tokens=600, context_tokens=12):
    """Yield (sample_start, sample_end, first_token, token_count).

    Cores cover the source once. Each encoder input includes up to 480 ms of
    context on either side, and is padded to a whole acoustic token by caller.
    """
    if frame_count <= 0 or core_tokens <= 0 or context_tokens < 0:
        raise ValueError('Invalid source encoding dimensions.')
    total_tokens = ceil(frame_count / TOKEN_HOP)
    for core_start in range(0, total_tokens, core_tokens):
        core_end = min(core_start + core_tokens, total_tokens)
        begin = max(0, core_start - context_tokens)
        end = min(total_tokens, core_end + context_tokens)
        yield begin * TOKEN_HOP, min(frame_count, end * TOKEN_HOP), core_start - begin, core_end - core_start
