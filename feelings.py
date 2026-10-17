"""App-level delivery presets and inline controls (not model text tokens)."""
import math
import re

FEELINGS = {
    "neutral": {"label": "Neutral", "description": "Natural, balanced delivery.", "exaggeration": 0.5, "pitch": 0.0, "rate": 1.0, "gain": 1.0},
    "happy": {"label": "Happy", "description": "A brighter, slightly quicker delivery.", "exaggeration": 0.85, "pitch": 1.1, "rate": 1.07, "gain": 1.04},
    "excited": {"label": "Excited", "description": "More energy, expression and pace.", "exaggeration": 1.0, "pitch": 1.5, "rate": 1.13, "gain": 1.08},
    "calm": {"label": "Calm", "description": "Softer expression and an unhurried pace.", "exaggeration": 0.3, "pitch": -0.25, "rate": 0.94, "gain": 0.95},
    "sad": {"label": "Sad", "description": "A softer, lower and slower delivery.", "exaggeration": 0.35, "pitch": -0.9, "rate": 0.9, "gain": 0.9},
    "serious": {"label": "Serious", "description": "A steadier, slightly lower delivery.", "exaggeration": 0.4, "pitch": -0.6, "rate": 0.98, "gain": 1.0},
}
TAG = re.compile(r"\[([^\[\]\n]+)\]")

def catalog():
    return [{"id": name, "label": value["label"], "description": value["description"]} for name, value in FEELINGS.items()]

def settings(feeling, strength, language="en"):
    if feeling not in FEELINGS:
        raise ValueError("Choose one of the available feelings.")
    strength = float(strength)
    if not math.isfinite(strength) or not 0 <= strength <= 1:
        raise ValueError("Feeling strength must be between 0 and 1.")
    preset = FEELINGS[feeling]
    # Keep the Tamil adaptation's native conditioning at its verified baseline.
    # Gentler pitch/pace changes help preserve its pronunciation and identity.
    delivery_strength = strength * (0.55 if language == "ta" else 1)
    return {"exaggeration": 0.5 if language == "ta" else 0.5 + (preset["exaggeration"] - 0.5) * strength,
            "pitch": preset["pitch"] * delivery_strength,
            "rate": 1 + (preset["rate"] - 1) * delivery_strength,
            "gain": 1 + (preset["gain"] - 1) * delivery_strength}

def parse_script(text, default_feeling="neutral"):
    if default_feeling not in FEELINGS:
        raise ValueError("Choose one of the available feelings.")
    current = default_feeling
    segments = []
    end = 0
    total_pause = 0
    def speech(value):
        value = value.strip()
        if "[" in value or "]" in value:
            raise ValueError("An inline tag is incomplete. Use a complete tag such as [happy].")
        if value:
            segments.append({"kind": "speech", "text": value, "feeling": current})
    for match in TAG.finditer(text):
        speech(text[end:match.start()])
        tag = match.group(1).strip().lower()
        if tag in FEELINGS:
            current = tag
        elif tag == "reset":
            current = default_feeling
        elif tag == "pause" or tag.startswith("pause="):
            try:
                duration = 0.5 if tag == "pause" else float(tag.split("=", 1)[1])
            except ValueError:
                raise ValueError("Use [pause] or a pause such as [pause=0.8].") from None
            if not math.isfinite(duration) or not 0.1 <= duration <= 3:
                raise ValueError("Each pause must be between 0.1 and 3 seconds.")
            total_pause += duration
            segments.append({"kind": "pause", "seconds": duration})
        else:
            raise ValueError(f"Unsupported tag [{tag}]. Use happy, excited, calm, sad, serious, neutral, reset or pause.")
        end = match.end()
    speech(text[end:])
    if not any(segment["kind"] == "speech" for segment in segments):
        raise ValueError("Add words to speak after the tags.")
    if len(segments) > 24 or total_pause > 15:
        raise ValueError("Use at most 24 text/pause sections and 15 seconds of pauses per generation.")
    return segments
