const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="studio-token"]').content;
let state = {voices: [], history: [], feelings: []}, language = 'en', busy = false;
let storageDirty = false, storageSaving = false;
function creativeMode() { return $('voiceMode').value === 'creative'; }
const examples = {en: 'Welcome to my offline voice studio. I can create natural speech on my own computer, in English and Tamil.', ta: 'வணக்கம்! இது எனது குரல் அரங்கம். இணைய இணைப்பு இல்லாமல், எனது கணினியிலேயே தமிழ் குரலை உருவாக்க முடியும்.'};
async function api(path, body) {
  const response = await fetch(path, body ? {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Studio-Token': token}, body: JSON.stringify(body)} : {});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Please try again.');
  return data;
}
function message(text, error = false) {
  $('statusMessage').hidden = !text;
  $('statusMessage').textContent = text;
  $('statusMessage').classList.toggle('error', error);
}
function storageMessage(text, error = false) {
  $('storageStatus').textContent = text;
  $('storageStatus').classList.toggle('error', error);
}
function updateStorageControls() {
  $('generationFolder').disabled = busy || storageSaving;
  $('saveGenerationFolder').disabled = busy || storageSaving || !storageDirty;
  $('openGenerationFolder').disabled = storageSaving || !state.storage;
}
function renderStorage() {
  if (!state.storage) return;
  if (!storageDirty) $('generationFolder').value = state.storage.generation_directory;
  $('generationFolder').title = state.storage.generation_directory;
  $('storageCurrentPath').textContent = 'Current folder: ' + state.storage.generation_directory;
  if (state.storage.warning) storageMessage(state.storage.warning, true);
  updateStorageControls();
}
async function saveGenerationFolder() {
  if (busy || storageSaving || !storageDirty) return;
  storageSaving = true; updateStorageControls();
  storageMessage('Checking your folder…');
  try {
    const response = await api('/api/storage', {directory:$('generationFolder').value});
    state.storage = response.storage; storageDirty = false; await refresh();
    storageMessage('Folder saved. New generations will appear here automatically.');
  } catch (error) { storageMessage(error.message, true); }
  finally { storageSaving = false; updateStorageControls(); }
}
async function openGenerationFolder() {
  try { await api('/api/storage/open', {}); storageMessage('Opened the current save folder.'); }
  catch (error) { storageMessage(error.message, true); }
}
function updateVoices(selected) {
  const keep = selected || $('voiceSelect').value;
  $('voiceSelect').replaceChildren();
  state.voices.filter(v => v.language === language || v.custom).forEach(v => {
    const option = new Option(v.name, v.id);
    $('voiceSelect').add(option);
  });
  if ([...$('voiceSelect').options].some(v => v.value === keep)) $('voiceSelect').value = keep;
  updateVoiceNote();
}
function updateVoiceNote() {
  const voice = state.voices.find(v => v.id === $('voiceSelect').value);
  $('voiceNote').textContent = voice?.reference_source ? 'Uses your supplied English Trickster sample (3.7 seconds). ' + (language === 'ta' ? 'Tamil pronunciation and character detail may change. A clear Tamil performance in Voice conversion gives you control over the delivery.' : 'Voice matching is approximate; the sample’s complete acting style is not copied.') : voice?.custom ? 'Your saved reference recording. A same-language recording usually gives the best result.' : 'A ready-to-use voice. Add a recording to use your own.';
}
function setLanguage(value) {
  language = value;
  document.querySelectorAll('[data-language]').forEach(b => b.classList.toggle('active', b.dataset.language === language));
  $('speechText').lang = language;
  updateVoices();
  updateFeelingNote();
  if (language === 'ta') $('voiceMode').value = 'classic';
  updateMode();
}
function updateCount() { $('charCount').textContent = `${$('speechText').value.length.toLocaleString()} / ${creativeMode() ? '800' : '2,000'}`; }
function feelingName(id) { return state.feelings.find(feeling => feeling.id === id)?.label || 'Neutral'; }
function voiceTitle(result) {
  if (result.mode === 'creative') {
    const preset = Object.values(state.creative_presets || {}).find(item => item.description === result.voice_description);
    if (preset) return preset.label;
  }
  return result.voice;
}
function updatePresetSelection() {
  document.querySelectorAll('[data-preset]').forEach(button => button.classList.toggle('active', state.creative_presets?.[button.dataset.preset]?.description === $('voiceDescription').value));
}
function deliveryLabel(result) {
  if (result.mode === 'conversion') return 'Voice conversion';
  if (result.mode === 'creative') return 'Creative directions';
  const moods = [...new Set((result.delivery_sections || []).filter(section => section.kind === 'speech').map(section => feelingName(section.feeling)))];
  return moods.length ? moods.join(' / ') : feelingName(result.feeling);
}
function updateMode() {
  const creative = creativeMode();
  $('creativeSettings').hidden = !creative;
  $('classicSettings').hidden = creative;
  $('customTagRow').hidden = !creative;
  $('speechText').maxLength = creative ? 800 : 2000;
  $('tagHelp').textContent = creative ? 'Write your own tags: [whispery, playful] or [moody, calm]. Tags affect the next passage; [reset] returns to your voice description.' : 'Tags change the following words. Use [neutral] to return to a natural tone.';
  $('modeNote').textContent = creative ? 'English · Designs a new character voice from your words. Saved recordings are used in Saved voice mode.' : 'English + Tamil · Built-in voices or your saved reference recording.';
  $('voiceMode').querySelector('option[value="creative"]').disabled = language !== 'en' || !state.creative_ready;
  renderFeelings(); updateCount(); updatePresetSelection();
}
function updateFeelingNote() {
  const feeling = state.feelings.find(item => item.id === $('feelingSelect').value);
  const expressiveTags = /\[(happy|excited|calm|sad|serious)\]/i.test($('speechText').value);
  const neutral = (!feeling || feeling.id === 'neutral') && !expressiveTags;
  $('expression').disabled = neutral;
  $('expressionValue').textContent = neutral ? 'Not used' : `${Math.round(+$('expression').value * 100)}%`;
  document.querySelector('.emotion-note').textContent = 'Feelings make modest changes to expression, pitch and pace. For detailed acting, record the performance and use Voice conversion. The complete reference performance is not copied by text-to-speech.';
  $('feelingDescription').textContent = (feeling?.description || 'Natural, balanced delivery.') + (neutral ? ' Strength has no effect on Neutral. Choose a feeling or insert a feeling tag to use it.' : language === 'ta' ? ' Tamil uses gentler changes to protect clarity.' : '');
}
function insertTag(tag) {
  const editor = $('speechText');
  const start = editor.selectionStart;
  const before = start && !/\s/.test(editor.value[start - 1]) ? ' ' : '';
  const insertion = `${before}[${tag}] `;
  if (editor.value.length + insertion.length > editor.maxLength) { message('There is no room for another tag. Shorten the text first.', true); return; }
  // Insert before a highlighted phrase rather than deleting the selected words.
  editor.setRangeText(insertion, start, start, 'end');
  editor.focus(); updateCount(); updateFeelingNote();
}
function renderFeelings() {
  const selected = $('feelingSelect').value || 'neutral';
  $('feelingSelect').replaceChildren(...state.feelings.map(feeling => new Option(feeling.label, feeling.id)));
  $('feelingSelect').value = selected;
  $('feelingTags').replaceChildren();
  const choices = creativeMode() ? ['whispery', 'playful', 'hypnotic', 'moody', 'gentle', 'happy', 'sad', 'reset', 'pause'].map(id => ({id, label:id})) : [...state.feelings.filter(feeling => feeling.id !== 'neutral'), {id: 'neutral', label: 'Neutral'}, {id: 'pause', label: 'Pause'}];
  choices.forEach(feeling => {
    const button = document.createElement('button'); button.type = 'button'; button.className = 'tag-button';
    button.textContent = `[${feeling.id}]`; button.title = `Insert ${feeling.label.toLowerCase()} tag`;
    button.addEventListener('click', () => insertTag(feeling.id)); $('feelingTags').append(button);
  });
  updateFeelingNote();
}
function showAudio(result, autoplay = false) {
  $('resultSection').hidden = false;
  $('audioPlayer').src = result.audio_url;
  $('resultTitle').textContent = voiceTitle(result);
  $('resultDetails').textContent = `${result.mode === 'conversion' ? 'Original language' : result.language === 'ta' ? 'Tamil' : 'English'} · ${deliveryLabel(result)} · ${result.seconds}s · WAV · ${result.sample_rate.toLocaleString()} Hz`;
  $('resultSavedPath').textContent = result.saved_path ? 'Saved to: ' + result.saved_path : '';
  $('downloadAudio').href = result.audio_url;
  $('downloadAudio').download = `voice-${result.language}-${result.id.slice(0,8)}.wav`;
  if (autoplay) $('audioPlayer').play().catch(() => {});
}
function renderHistory() {
  $('historyList').replaceChildren();
  if (!state.history.length) {
    const empty = document.createElement('div'); empty.className = 'empty-state';
    empty.textContent = 'Your generated audio will appear here.'; $('historyList').append(empty); return;
  }
  state.history.forEach(item => {
    const row = document.createElement('div'); row.className = 'history-row';
    const play = document.createElement('button'); play.className = 'play-button'; play.textContent = '▶'; play.title = 'Play audio'; play.addEventListener('click', () => showAudio(item, true));
    const text = document.createElement('div'); text.className = 'history-text';
    const title = document.createElement('strong'); title.textContent = item.text;
    const detail = document.createElement('small'); detail.textContent = `${voiceTitle(item)} · ${deliveryLabel(item)} · ${item.seconds}s · ${new Date(item.created).toLocaleString()}`;
    text.append(title, detail);
    const link = document.createElement('a'); link.className = 'history-download'; link.href = item.audio_url; link.download = `voice-${item.language}-${item.id.slice(0,8)}.wav`; link.textContent = '↓ WAV';
    row.append(play, text, link); $('historyList').append(row);
  });
}
async function refresh() { state = await api('/api/state'); updateVoices(); updateMode(); renderHistory(); renderStorage(); if (typeof renderConversionTargets === 'function') renderConversionTargets(); }
async function generate() {
  if (busy) return;
  const text = $('speechText').value.trim();
  if (!text) { message('Add some text to create your audio.', true); $('speechText').focus(); return; }
  busy = true; $('generate').disabled = true; $('generate').textContent = 'Creating your audio…';
  if (typeof updateConversionControls === 'function') updateConversionControls();
  try {
    message('Preparing your audio. The first generation also loads the voice model.');
    const task = await api('/api/generate', {text, language, voice: $('voiceSelect').value, feeling: $('feelingSelect').value, expression: +$('expression').value, seed: 42, mode: $('voiceMode').value, description: $('voiceDescription').value});
    while (true) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      const job = await api(`/api/jobs/${task.id}`);
      message(job.message);
      if (job.status === 'error') throw new Error(job.message);
      if (job.status === 'done') { showAudio(job.result); await refresh(); message('Your audio is ready. Preview it below or save the WAV file.'); break; }
    }
  } catch (error) { message(error.message, true); }
  finally { busy = false; $('generate').disabled = false; $('generate').textContent = 'Generate speech ↗'; if (typeof updateConversionControls === 'function') updateConversionControls(); }
}
function openVoice() { $('voiceFormStatus').textContent = ''; $('voiceDialog').showModal(); }
async function addVoice(event) {
  event.preventDefault();
  const file = $('voiceFile').files[0];
  if (!file || file.size > 24 * 1024 * 1024) { $('voiceFormStatus').textContent = 'Choose a recording smaller than 24 MB.'; return; }
  $('saveVoice').disabled = true;
  $('voiceFormStatus').textContent = 'Saving your voice locally…';
  try {
    const encoded = await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result.split(',')[1]); reader.onerror = reject; reader.readAsDataURL(file); });
    const voice = await api('/api/voices', {name: $('voiceName').value, audio: encoded});
    await refresh(); updateVoices(voice.id); $('voiceDialog').close(); $('voiceForm').reset();
    if (typeof renderConversionTargets === 'function') renderConversionTargets(voice.id);
    message(`“${voice.name}” is ready. Choose a language, add your text, and generate speech.`);
  } catch (error) { $('voiceFormStatus').textContent = error.message; }
  finally { $('saveVoice').disabled = false; }
}
document.querySelectorAll('[data-language]').forEach(b => b.addEventListener('click', () => setLanguage(b.dataset.language)));
$('generationFolder').addEventListener('input', () => { storageDirty = $('generationFolder').value !== state.storage?.generation_directory; storageMessage(storageDirty ? 'Choose Save folder to use this path.' : ''); updateStorageControls(); });
$('generationFolder').addEventListener('keydown', event => { if (event.key === 'Enter') { event.preventDefault(); saveGenerationFolder(); } });
$('saveGenerationFolder').addEventListener('click', saveGenerationFolder);
$('openGenerationFolder').addEventListener('click', openGenerationFolder);
$('voiceMode').addEventListener('change', updateMode);
$('voiceDescription').addEventListener('input', () => { updatePresetSelection(); try { localStorage.setItem('creativeVoiceDescription', $('voiceDescription').value); } catch {} });
$('addCustomTag').addEventListener('click', () => { const tag = $('customTag').value.trim().replace(/[\[\]]/g, ''); if (tag) { insertTag(tag); $('customTag').value = ''; } });
$('customTag').addEventListener('keydown', event => { if (event.key === 'Enter') { event.preventDefault(); $('addCustomTag').click(); } });
document.querySelectorAll('[data-preset]').forEach(button => button.addEventListener('click', () => { const preset = state.creative_presets[button.dataset.preset]; if (preset) { $('voiceDescription').value = preset.description; updatePresetSelection(); try { localStorage.setItem('creativeVoiceDescription', preset.description); } catch {} } }));
$('speechText').addEventListener('input', () => { updateCount(); updateFeelingNote(); });
$('voiceSelect').addEventListener('change', updateVoiceNote);
$('expression').addEventListener('input', () => $('expressionValue').textContent = `${Math.round(+$('expression').value * 100)}%`);
$('feelingSelect').addEventListener('change', updateFeelingNote);
$('insertExample').addEventListener('click', () => { $('speechText').value = creativeMode() ? '[whispery, sly, playful] The shadows have a secret, and tonight, I may just share it with you. [pause=0.8] [gentle, calm] Follow the lantern and listen to the quiet.' : examples[language]; updateCount(); updateFeelingNote(); });
$('generate').addEventListener('click', generate);
$('addVoiceNav').addEventListener('click', openVoice); $('addVoiceTop').addEventListener('click', openVoice);
$('closeVoice').addEventListener('click', () => $('voiceDialog').close());
$('voiceForm').addEventListener('submit', addVoice);
try {
  const savedDescription = localStorage.getItem('creativeVoiceDescription');
  const replacedDescription = 'An adult masculine fantasy trickster with a low, gravelly, slightly raspy voice and a rich nasal resonance. Sly, impish and comically grumpy, with a mischievous grin in the voice. Exaggerated theatrical rises and falls, wry humor, elastic pacing and crisp, intelligible words. Playful storybook villain energy, not shouting.';
  if (savedDescription === replacedDescription) localStorage.removeItem('creativeVoiceDescription');
  else if (savedDescription) $('voiceDescription').value = savedDescription.slice(0, 900);
} catch {}
refresh().catch(error => message(error.message, true));
