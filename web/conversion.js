let currentView = 'tts';
const capture = {starting:false, recording:false, ticket:0, chunks:[], frames:0};
let conversionSource = null, conversionPreview = null, sourcePreparing = false;

function conversionMessage(text, error = false) {
  $('conversionStatus').textContent = text;
  $('conversionStatus').classList.toggle('error', error);
}
function updateConversionControls() {
  if (typeof updateStorageControls === 'function') updateStorageControls();
  const occupied = busy || capture.starting || capture.recording || sourcePreparing;
  $('convertVoice').disabled = occupied || !conversionSource || !state.conversion_ready;
  $('sourceFile').disabled = occupied;
  $('recordSource').disabled = occupied;
  $('targetVoice').disabled = occupied;
  $('conversionAddVoice').disabled = occupied;
  $('clearSource').disabled = occupied;
  $('generate').disabled = busy || capture.recording || capture.starting;
  $('stopRecording').hidden = !capture.recording && !capture.starting;
  $('recordSource').hidden = capture.recording || capture.starting;
}
function renderConversionTargets(selected) {
  const keep = selected || $('targetVoice').value;
  const groups = new Map();
  $('targetVoice').replaceChildren();
  (state.conversion_targets || []).forEach(voice => {
    if (!groups.has(voice.kind)) { const group = document.createElement('optgroup'); group.label = voice.kind; groups.set(voice.kind, group); $('targetVoice').append(group); }
    groups.get(voice.kind).append(new Option(voice.name, voice.id));
  });
  if ([...$('targetVoice').options].some(option => option.value === keep)) $('targetVoice').value = keep;
  updateConversionControls();
}
function showView(view) {
  if (view !== 'conversion' && (capture.recording || capture.starting)) stopRecording();
  currentView = view;
  $('ttsWorkspace').hidden = view !== 'tts';
  $('conversionWorkspace').hidden = view !== 'conversion';
  $('pageTitle').textContent = view === 'conversion' ? 'Voice conversion' : 'Text to speech';
  $('workspaceTitle').textContent = $('pageTitle').textContent;
  $('pageDescription').textContent = view === 'conversion' ? 'Your words and performance. A different voice.' : 'Natural speech in English and Tamil, powered by your PC.';
  document.querySelectorAll('[data-view]').forEach(button => {
    button.classList.toggle('selected', button.dataset.view === view);
    button.setAttribute('aria-current', button.dataset.view === view ? 'page' : 'false');
  });
}
function setConversionSource(file, duration) {
  if (conversionPreview) URL.revokeObjectURL(conversionPreview);
  conversionSource = file;
  conversionPreview = URL.createObjectURL(file);
  $('sourceAudio').src = conversionPreview;
  $('sourcePreview').hidden = false;
  $('sourceName').textContent = file.name;
  $('sourceDetails').textContent = `${duration.toFixed(1)} seconds · Ready to convert`;
  conversionMessage('Preview your original audio, choose a target voice, then convert.');
  updateConversionControls();
}
async function loadSourceFile(file) {
  if (!file) return;
  if (file.size > 128 * 1024 * 1024) { conversionMessage('Choose an audio file smaller than 128 MB.', true); return; }
  sourcePreparing = true; updateConversionControls();
  conversionMessage('Preparing your audio on this PC…');
  let context;
  try {
    context = new AudioContext({sampleRate:24000});
    const audio = await context.decodeAudioData(await file.arrayBuffer());
    if (audio.duration < 1 || audio.duration > 300.01) throw new Error('Choose a clip between 1 second and 5 minutes long.');
    const samples = new Float32Array(audio.length);
    for (let channel = 0; channel < audio.numberOfChannels; channel++) {
      const values = audio.getChannelData(channel);
      for (let i = 0; i < samples.length; i++) samples[i] += values[i] / audio.numberOfChannels;
    }
    const wav = new File([encodeMonoWav(samples, audio.sampleRate)], file.name, {type:'audio/wav'});
    setConversionSource(wav, audio.duration);
  } catch (error) {
    conversionMessage(error.message.includes('between 1 second and 5 minutes') ? error.message : 'This browser could not read the audio. Try WAV, MP3 or M4A.', true);
  } finally {
    if (context) await context.close().catch(() => {});
    sourcePreparing = false; $('sourceFile').value = ''; updateConversionControls();
  }
}
async function startRecording() {
  if (busy || capture.starting || capture.recording) return;
  if (!navigator.mediaDevices?.getUserMedia) { conversionMessage('Microphone access is unavailable in this browser. Upload audio, or open the studio in Chrome or Edge.', true); return; }
  capture.starting = true; const ticket = ++capture.ticket; updateConversionControls();
  conversionMessage('Allow microphone access in your browser to begin recording.');
  let context, stream;
  try {
    context = new AudioContext({sampleRate:24000});
    await context.resume();
    stream = await navigator.mediaDevices.getUserMedia({audio:{channelCount:1, echoCancellation:false, noiseSuppression:false, autoGainControl:false}});
    if (ticket !== capture.ticket || currentView !== 'conversion') { stream.getTracks().forEach(track => track.stop()); await context.close(); return; }
    capture.context = context; capture.stream = stream; capture.chunks = []; capture.frames = 0;
    capture.input = context.createMediaStreamSource(stream);
    capture.processor = context.createScriptProcessor(4096, 1, 1);
    capture.mute = context.createGain(); capture.mute.gain.value = 0;
    capture.recording = true; capture.starting = false;
    capture.processor.onaudioprocess = event => {
      if (!capture.recording) return;
      const input = event.inputBuffer.getChannelData(0);
      const remaining = Math.round(context.sampleRate * 30) - capture.frames;
      const chunk = input.slice(0, Math.min(input.length, remaining));
      capture.chunks.push(chunk); capture.frames += chunk.length;
      let energy = 0; for (const sample of chunk) energy += sample * sample;
      $('inputLevel').value = Math.min(1, Math.sqrt(energy / Math.max(1, chunk.length)) * 4);
      $('recordingTime').textContent = `${(capture.frames / context.sampleRate).toFixed(1)} / 30s`;
      if (capture.frames >= context.sampleRate * 30) stopRecording();
    };
    capture.input.connect(capture.processor); capture.processor.connect(capture.mute); capture.mute.connect(context.destination);
    stream.getAudioTracks().forEach(track => { track.onended = () => { if (capture.recording) stopRecording(); }; });
    $('recordingIndicator').hidden = false;
    conversionMessage('Recording… Speak naturally. Select Stop recording when finished.');
    updateConversionControls();
  } catch (error) {
    if (stream) stream.getTracks().forEach(track => track.stop());
    if (context) await context.close().catch(() => {});
    if (ticket !== capture.ticket) return;
    conversionMessage(error.name === 'NotAllowedError' ? 'Microphone permission was denied. Allow access in your browser, or upload an audio file.' : 'The microphone could not start. Check that it is connected, or upload audio.', true);
    capture.starting = false; capture.recording = false; updateConversionControls();
  }
}
function stopRecording(discard = false) {
  ++capture.ticket;
  const wasStarting = capture.starting;
  capture.starting = false;
  if (!capture.recording) { if (wasStarting && !discard) conversionMessage('Recording cancelled.'); updateConversionControls(); return; }
  capture.recording = false;
  if (capture.processor) { capture.processor.onaudioprocess = null; capture.processor.disconnect(); }
  capture.input?.disconnect(); capture.mute?.disconnect();
  capture.stream?.getTracks().forEach(track => { track.onended = null; track.stop(); });
  const rate = capture.context.sampleRate;
  capture.context.close().catch(() => {});
  $('recordingIndicator').hidden = true; $('inputLevel').value = 0;
  if (!discard && capture.frames >= rate) {
    const samples = new Float32Array(capture.frames); let offset = 0;
    for (const chunk of capture.chunks) { samples.set(chunk, offset); offset += chunk.length; }
    setConversionSource(new File([encodeMonoWav(samples, rate)], 'Microphone recording.wav', {type:'audio/wav'}), capture.frames / rate);
  } else if (!discard) conversionMessage('Record at least one second of clear speech.', true);
  capture.chunks = []; capture.frames = 0;
  capture.context = capture.stream = capture.processor = capture.input = capture.mute = null;
  updateConversionControls();
}
function clearConversionSource() {
  if (busy || capture.recording || capture.starting) return;
  if (conversionPreview) URL.revokeObjectURL(conversionPreview);
  conversionSource = conversionPreview = null;
  $('sourceAudio').removeAttribute('src'); $('sourceAudio').load();
  $('sourcePreview').hidden = true; conversionMessage(''); updateConversionControls();
}
async function convertVoice() {
  if (busy || !conversionSource || capture.recording || capture.starting) return;
  busy = true; updateConversionControls(); $('convertVoice').textContent = 'Converting your voice…';
  try {
    conversionMessage('Preparing your recording for offline conversion…');
    const audio = await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result.split(',')[1]); reader.onerror = reject; reader.readAsDataURL(conversionSource); });
    const task = await api('/api/convert', {audio, target:$('targetVoice').value, name:conversionSource.name});
    while (true) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      const job = await api('/api/jobs/' + task.id);
      conversionMessage(job.message);
      if (job.status === 'error') throw new Error(job.message);
      if (job.status === 'done') {
        showAudio(job.result); await refresh();
        conversionMessage('Your converted voice is ready. Preview it below or save the WAV file.');
        $('resultSection').scrollIntoView({behavior:'smooth', block:'nearest'}); break;
      }
    }
  } catch (error) { conversionMessage(error.message, true); }
  finally { busy = false; $('convertVoice').textContent = 'Convert voice ↗'; updateConversionControls(); }
}
document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => showView(button.dataset.view)));
$('sourceFile').addEventListener('change', event => loadSourceFile(event.target.files[0]));
$('recordSource').addEventListener('click', startRecording);
$('stopRecording').addEventListener('click', () => stopRecording());
$('clearSource').addEventListener('click', clearConversionSource);
$('convertVoice').addEventListener('click', convertVoice);
$('conversionAddVoice').addEventListener('click', openVoice);
window.addEventListener('beforeunload', () => { stopRecording(true); if (conversionPreview) URL.revokeObjectURL(conversionPreview); });
if (state.conversion_targets) renderConversionTargets();
