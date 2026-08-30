// App wiring: UI events, settings modal, recording, transcription.

import { MicRecorder, blobToWav } from './audio.js';
import { transcribeBlob, discoverModels } from './transcription.js';
import { loadSettings, saveSettings, resolveProviderConfig } from './settings.js';
import { providerProfiles, PROVIDER_ORDER, getProviderProfile } from './providers.js';
import { promptForModel } from './model-picker.js';

const recorder = new MicRecorder();
let settings = loadSettings();

const $ = (id) => document.getElementById(id);

function updateConnectionBadge(text, ok) {
  $('connectionDot').className = `h-2 w-2 rounded-full ${ok ? 'bg-emerald-400' : 'bg-slate-500'}`;
  $('activeModelLabel').textContent = text;
}

function refreshProviderUi() {
  const profile = getProviderProfile(settings.provider);
  const config = resolveProviderConfig(settings);
  $('providerSelect').value = settings.provider;
  $('apiKeyInput').value = settings.apiKey;
  $('baseUrlInput').value = settings.baseUrl || profile.url || '';
  $('modelLabel').textContent = config.model || 'not set';
  $('apiKeyRow').classList.toggle('hidden', !profile.apiKeyRequired);
  $('baseUrlRow').classList.toggle('hidden', settings.provider === 'local');
  updateConnectionBadge(`${profile.label} · ${config.model || 'no model'}`, Boolean(config.model));
}

function openSettings() {
  refreshProviderUi();
  $('settingsModal').classList.remove('hidden');
  $('settingsModal').classList.add('flex');
}

function closeSettings() {
  $('settingsModal').classList.add('hidden');
  $('settingsModal').classList.remove('flex');
}

async function pickModel() {
  try {
    const selection = await promptForModel(() => discoverModels(settings), settings.model);
    if (selection) {
      settings.model = selection.model;
      saveSettings(settings);
      refreshProviderUi();
    }
  } catch (error) {
    alert(error.message);
  }
}

async function toggleRecording() {
  if (!recorder.recording) {
    try {
      await recorder.start();
      $('recordBtn').textContent = '⏹ Stop Recording';
      $('recordBtn').classList.replace('bg-brand-600', 'bg-rose-600');
      $('statusBar').textContent = 'Recording... click Stop when done.';
    } catch (error) {
      alert(`Microphone error: ${error.message}`);
    }
    return;
  }

  const blob = await recorder.stop();
  $('recordBtn').textContent = '🎤 Start Recording';
  $('recordBtn').classList.replace('bg-rose-600', 'bg-brand-600');
  $('statusBar').textContent = 'Transcribing...';
  await runTranscription(blob);
}

async function runTranscription(blob) {
  const started = performance.now();
  try {
    const wav = await blobToWav(blob);
    const text = await transcribeBlob(wav.blob, wav.extension, settings, $('timestampsToggle').checked);
    const seconds = ((performance.now() - started) / 1000).toFixed(1);
    $('outputText').value = text;
    $('statusBar').textContent = `Done in ${seconds}s · ${getProviderProfile(settings.provider).label}`;
    updateConnectionBadge(`${getProviderProfile(settings.provider).label} · ${resolveProviderConfig(settings).model}`, true);
  } catch (error) {
    $('statusBar').textContent = 'Transcription failed.';
    alert(error.message);
  }
}

function wireEvents() {
  $('settingsBtn').addEventListener('click', openSettings);
  $('closeSettingsBtn').addEventListener('click', closeSettings);
  $('pickModelBtn').addEventListener('click', pickModel);
  $('recordBtn').addEventListener('click', toggleRecording);

  $('copyBtn').addEventListener('click', () => {
    const text = $('outputText').value;
    if (!text) return;
    navigator.clipboard.writeText(text);
    $('statusBar').textContent = 'Transcript copied to clipboard.';
  });

  $('saveBtn').addEventListener('click', () => {
    const text = $('outputText').value;
    if (!text) return;
    const blob = new Blob([text], { type: 'text/plain' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `transcript-${Date.now()}.txt`;
    link.click();
  });

  $('fileInput').addEventListener('change', async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    $('statusBar').textContent = `Transcribing ${file.name}...`;
    await runTranscription(file);
    event.target.value = '';
  });

  $('providerSelect').addEventListener('change', (event) => {
    settings.provider = event.target.value;
    const profile = getProviderProfile(settings.provider);
    settings.baseUrl = profile.url || '';
    settings.model = profile.sttModel || '';
    saveSettings(settings);
    refreshProviderUi();
  });

  $('apiKeyInput').addEventListener('input', (event) => {
    settings.apiKey = event.target.value.trim();
    saveSettings(settings);
  });

  $('baseUrlInput').addEventListener('input', (event) => {
    settings.baseUrl = event.target.value.trim();
    saveSettings(settings);
  });

  $('testProviderBtn').addEventListener('click', async () => {
    $('testResult').textContent = 'Testing...';
    try {
      const models = await discoverModels(settings);
      $('testResult').textContent = `OK — ${models.length} model(s) available.`;
    } catch (error) {
      $('testResult').textContent = `Failed: ${error.message}`;
    }
  });
}

function populateProviderSelect() {
  $('providerSelect').replaceChildren(...PROVIDER_ORDER.map((id) => new Option(providerProfiles[id].label, id)));
}

populateProviderSelect();
wireEvents();
refreshProviderUi();
