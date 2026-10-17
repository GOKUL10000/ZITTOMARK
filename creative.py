"""Natural-language directions for the local Qwen VoiceDesign engine."""
import math
import re

PRESETS = {
    'soft_hypnotic': {'label': 'Soft hypnotic', 'description': 'An adult feminine voice with a warm, velvety lower register. Soft, breathy, gently whispered delivery, soothing and hypnotic, charming and subtly playful. Intimate ASMR storytelling, clear words and a relaxed pace.'},
    'shadow_spirit': {'label': 'Shadow spirit', 'description': 'An adult feminine shadow-spirit character. Low, airy, softly whispered voice, sly and impish, wickedly mischievous, playful and charming. Gentle, mysterious ASMR narration, with a smile in the voice, clear words and unhurried pacing.'},
    'gentle_meditation': {'label': 'Gentle meditation', 'description': 'An adult voice, warm, gentle and reassuring. Soft, steady, slow guided-meditation narration with clear words and a calm, natural cadence.'},
}
TAG = re.compile(r'\[([^\[\]\n]+)\]')

def parse_creative(text, description):
    description = str(description).strip()
    if not description or len(description) > 900:
        raise ValueError('Describe your voice in 1–900 characters.')
    if len(text) > 800:
        raise ValueError('Use up to 800 characters in Creative voice mode. Short passages give better control.')
    sections, tags, total_pause, end = [], [], 0, 0
    def speech(value):
        value = value.strip()
        if '[' in value or ']' in value:
            raise ValueError('Complete each direction tag, for example [whispery, playful].')
        if value:
            sections.append({'kind': 'speech', 'text': value,
                             'direction': description + (' Delivery for this passage: ' + ', '.join(tags) + '.' if tags else '')})
    for match in TAG.finditer(text):
        before = text[end:match.start()]
        speech(before)
        tag = match.group(1).strip()
        # Adjacent tags combine; a tag following spoken words starts a new direction.
        if before.strip() and not (tag.lower() == 'pause' or tag.lower().startswith('pause=')):
            tags = []
        if tag.lower() == 'reset':
            tags = []
        elif tag.lower() == 'pause' or tag.lower().startswith('pause='):
            try:
                duration = .5 if tag.lower() == 'pause' else float(tag.split('=', 1)[1])
            except ValueError:
                raise ValueError('Use [pause] or [pause=0.8].') from None
            if not math.isfinite(duration) or not .1 <= duration <= 3:
                raise ValueError('Each pause must be between 0.1 and 3 seconds.')
            total_pause += duration
            sections.append({'kind': 'pause', 'seconds': duration})
        else:
            if len(tag) > 180:
                raise ValueError('Keep each creative tag under 180 characters.')
            tags.append(tag)
        end = match.end()
    speech(text[end:])
    if not any(section['kind'] == 'speech' for section in sections):
        raise ValueError('Add words to speak after your direction tags.')
    if len(sections) > 8 or total_pause > 10:
        raise ValueError('Use up to 8 text/pause sections and 10 seconds of pauses in Creative voice mode.')
    return sections
