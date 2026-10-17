"""GPU speech engine using local, pinned Chatterbox/Indic weights only."""
import copy
import json
import os
from pathlib import Path
import re
import threading
import gc
import functools
from safetensors.torch import load_file as safe_load_file
from feelings import parse_script, settings
from tensor_loading import stream_weights

from runtime_paths import RUNTIME
BASE = RUNTIME / "models" / "base"
INDIC = RUNTIME / "models" / "indic"
DEVICE = "cpu" if os.environ.get("OVS_CPU_ONLY") == "1" else "cuda"
os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                  HF_HUB_DISABLE_TELEMETRY="1", DO_NOT_TRACK="1",
                  TOKENIZERS_PARALLELISM="false")
os.environ["HF_HOME"] = str(RUNTIME / "hf-cache")

import numpy as np
import soundfile as sf
import torch
from chatterbox.mtl_tts import ChatterboxMultilingualTTS, Conditionals
from chatterbox.models.tokenizers import MTLTokenizer
import chatterbox.mtl_tts as multilingual_runtime
from tokenizers import Tokenizer

class EnglishTamilTokenizer(MTLTokenizer):
    def __init__(self, vocabulary):
        # Upstream eagerly initializes a Chinese segmenter which downloads a
        # separate model. English/Tamil do not use it, so load only the local
        # vocabulary and retain the original English/Tamil tokenization logic.
        self.tokenizer = Tokenizer.from_file(str(vocabulary))
        self.cangjie_converter = None
        self.check_vocabset_sot_eot()

multilingual_runtime.MTLTokenizer = EnglishTamilTokenizer
# Avoid whole-file copy-on-write mappings consuming Windows commit memory.
multilingual_runtime.load_safetensors = functools.partial(safe_load_file, backend='pread')

def clean_speech_tokens(tokens):
    # Upstream assumes exactly one SOS/EOS and crashes when sampling returns
    # repeated markers. Select the first complete span and discard special IDs.
    tokens = tokens.reshape(-1)
    start_markers = (tokens == 6561).nonzero(as_tuple=True)[0]
    start = int(start_markers[0].item()) + 1 if start_markers.numel() else 0
    tokens = tokens[start:]
    end_markers = (tokens == 6562).nonzero(as_tuple=True)[0]
    if end_markers.numel():
        tokens = tokens[:int(end_markers[0].item())]
    tokens = tokens[(tokens >= 0) & (tokens < 6561)]
    if not tokens.numel():
        raise RuntimeError('The voice model returned no speech. Try a longer sentence or a clearer reference.')
    return tokens

multilingual_runtime.drop_invalid_tokens = clean_speech_tokens

@torch.no_grad()
def load_local_model():
    # Upstream keeps the full T3 checkpoint alive while constructing S3Gen.
    # Load sequentially and release each state dictionary before the next model.
    with torch.device(DEVICE):
        ve = multilingual_runtime.VoiceEncoder()
    state = torch.load(BASE / 've.pt', map_location='cpu', weights_only=True, mmap=True)
    ve.load_state_dict(state)
    del state
    ve.eval()
    with torch.device(DEVICE):
        t3 = multilingual_runtime.T3(multilingual_runtime.T3Config.multilingual())
    stream_weights(t3, BASE / 't3_mtl23ls_v2.safetensors')
    if DEVICE == 'cuda':
        t3.to(dtype=torch.bfloat16)
    gc.collect()
    torch.cuda.empty_cache()
    t3.eval()
    with torch.device(DEVICE):
        s3gen = multilingual_runtime.S3Gen()
    state = torch.load(BASE / 's3gen.pt', map_location='cpu', weights_only=True, mmap=True)
    s3gen.load_state_dict(state)
    del state
    s3gen.eval()
    # Reduce peak GPU allocation by keeping acoustic flow on the GPU and
    # running the final waveform vocoder on CPU.
    s3gen.mel2wav.to('cpu')
    s3gen.trim_fade = s3gen.trim_fade.to('cpu')
    def cpu_vocoder(speech_feat, cache_source=None):
        if cache_source is None:
            cache_source = torch.zeros(1, 1, 0, dtype=torch.float32)
        return s3gen.mel2wav.inference(speech_feat=speech_feat.to('cpu'), cache_source=cache_source.to('cpu'))
    s3gen.hift_inference = cpu_vocoder
    conds = Conditionals.load(BASE / 'conds.pt', 'cpu').to(DEVICE)
    tokenizer = EnglishTamilTokenizer(BASE / 'grapheme_mtl_merged_expanded_v1.json')
    return ChatterboxMultilingualTTS(t3, s3gen, ve, tokenizer, DEVICE, conds=conds)

class VoiceEngine:
    def __init__(self):
        self.model = None
        self.lock = threading.Lock()
        self.builtin = {}
        self.load_report = {}

    @torch.no_grad()
    def load(self, status=lambda _: None):
        if self.model is not None:
            return
        status("Loading the offline voice model…")
        if DEVICE == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("The NVIDIA speech runtime is unavailable. Restart the app and check your GPU driver.")
        torch.set_num_threads(min(8, os.cpu_count() or 4))
        # Construct the large model directly on the GPU. Building full random
        # CPU copies before moving them doubles the loading peak on Windows.
        model = load_local_model()
        self.builtin["english_default"] = copy.deepcopy(model.conds)
        model.tokenizer = EnglishTamilTokenizer(INDIC / "tokenizer" / "extended_tokenizer.json")
        # Restricted deserialization: never execute Python objects from a checkpoint.
        checkpoint = torch.load(INDIC / "checkpoints" / "best.pt", map_location="cpu", weights_only=True, mmap=True)
        if "text_emb_weight" in checkpoint:
            emb = checkpoint["text_emb_weight"]
            head = checkpoint["text_head_weight"]
            model.t3.text_emb = torch.nn.Embedding.from_pretrained(emb.to(DEVICE), freeze=True)
            model.t3.text_head = torch.nn.Linear(head.shape[1], head.shape[0], bias=False).to(DEVICE)
            model.t3.text_head.weight.data.copy_(head.to(DEVICE))
        state = checkpoint.get("lora_state_dict", {})
        applied = 0
        # The distributed checkpoint contains PEFT A/B matrices, not merged
        # transformer weights. Merge every pair using its published alpha/rank.
        # The upstream convenience loader silently skips these differently
        # named keys; validating the merge is essential for Tamil generation.
        pairs = [name for name in state if ".lora_A.default.weight" in name]
        if pairs:
            with torch.no_grad():
                for name in pairs:
                    other = name.replace(".lora_A.default.weight", ".lora_B.default.weight")
                    if other not in state:
                        raise RuntimeError("Incomplete Tamil voice adapter.")
                    module_name = name.removeprefix("base_model.model.").replace(".lora_A.default.weight", "")
                    layer = model.t3.tfmr.get_submodule(module_name)
                    a, b = state[name].float(), state[other].float()
                    # Model card: rank 32 and alpha 64 (scaling = 2).
                    if a.shape[0] != 32:
                        raise RuntimeError("Unexpected Tamil adapter rank.")
                    delta = (b @ a) * (64.0 / a.shape[0])
                    if layer.weight.shape != delta.shape:
                        raise RuntimeError("Tamil adapter shape does not match the voice engine.")
                    layer.weight.add_(delta.to(device=layer.weight.device, dtype=layer.weight.dtype))
                    applied += 1
        elif "model_state_dict" in checkpoint:
            result = model.t3.load_state_dict(checkpoint["model_state_dict"], strict=False)
            applied = len(checkpoint["model_state_dict"]) - len(result.unexpected_keys)
        else:
            raise RuntimeError("The Tamil adapter format needs repair; no unverified adapter was loaded.")
        self.load_report = {"adapter_tensors_applied": applied, "checkpoint_keys": list(checkpoint), "gpu": torch.cuda.get_device_name(0) if DEVICE == "cuda" else "CPU compatibility"}
        del checkpoint, state
        for voice in ("ta_female", "ta_male"):
            self.builtin[voice] = Conditionals.load(INDIC / "conds" / f"{voice}.pt", "cpu").to(DEVICE)
        # Keep the autoregressive model compact on the 8 GB laptop GPU.
        # The acoustic decoder stays in float32 for its FFT/vocoder operations.
        if DEVICE == 'cuda':
            model.t3.to(dtype=torch.bfloat16)
            original_inference = model.t3.inference
            def compact_inference(*args, **kwargs):
                with torch.autocast('cuda', dtype=torch.bfloat16):
                    return original_inference(*args, **kwargs)
            model.t3.inference = compact_inference
        self.model = model
        torch.cuda.empty_cache()
        status("Voice model ready")

    @staticmethod
    def split_text(text, limit=160):
        text = re.sub(r"\s+", " ", text).strip()
        sentences = re.split(r"(?<=[.!?।])\s+", text)
        chunks, current = [], ""
        for sentence in sentences:
            for word in sentence.split():
                if len(current) + len(word) + 1 > limit and current:
                    chunks.append(current)
                    current = ""
                current = f"{current} {word}".strip()
            if current:
                chunks.append(current)
                current = ""
        return chunks

    @torch.no_grad()
    def synthesize(self, text, language, voice, reference, expression, seed, status, feeling="neutral"):
        sections = parse_script(text, feeling)
        with self.lock:
            self.load(status)
            model = self.model
            if reference:
                model.prepare_conditionals(str(reference), exaggeration=0.5)
            else:
                model.conds = copy.deepcopy(self.builtin[voice])
            torch.manual_seed(seed)
            torch.cuda.manual_seed_all(seed) if DEVICE == "cuda" else None
            chunks = []
            for section in sections:
                if section["kind"] == "pause":
                    chunks.append(section)
                else:
                    chunks.extend({"kind": "speech", "text": part, "feeling": section["feeling"]}
                                  for part in self.split_text(section["text"]))
            audio = []
            speech_total = sum(chunk["kind"] == "speech" for chunk in chunks)
            spoken = 0
            for i, chunk in enumerate(chunks):
                if chunk["kind"] == "pause":
                    audio.append(np.zeros(round(chunk["seconds"] * model.sr), dtype=np.float32))
                    continue
                spoken += 1
                style = settings(chunk["feeling"], expression, language)
                status(f"Generating speech {spoken} of {speech_total} · {chunk['feeling'].title()}…")
                wav = model.generate(chunk["text"], language_id=language, exaggeration=style["exaggeration"],
                                     cfg_weight=0.3 if language == "ta" else 0.5,
                                     temperature=0.7, min_p=0.05)
                samples = wav.detach().cpu().numpy().reshape(-1).astype(np.float32)
                if style["pitch"] or style["rate"] != 1 or style["gain"] != 1:
                    import librosa
                    if style["pitch"]:
                        samples = librosa.effects.pitch_shift(samples, sr=model.sr, n_steps=style["pitch"])
                    if style["rate"] != 1:
                        samples = librosa.effects.time_stretch(samples, rate=style["rate"])
                    samples = np.asarray(samples * style["gain"], dtype=np.float32)
                    # Delivery effects can weaken a previously embedded mark.
                    # Apply the model's watermarker again after these effects.
                    samples = np.asarray(model.watermarker.apply_watermark(samples, sample_rate=model.sr), dtype=np.float32)
                if not np.isfinite(samples).all() or len(samples) < model.sr // 4:
                    raise RuntimeError("The model did not produce valid speech. Try a shorter sentence.")
                audio.append(samples)
                if i + 1 < len(chunks) and chunks[i + 1]["kind"] == "speech":
                    audio.append(np.zeros(int(0.18 * model.sr), dtype=np.float32))
            combined = np.concatenate(audio)
            peak = float(np.max(np.abs(combined)))
            if peak > 0.99:
                combined *= 0.99 / peak
            return combined, model.sr
