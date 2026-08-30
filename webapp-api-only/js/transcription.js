// Transcription backends: OpenAI-compatible (Lemonade, OpenRouter, OpenAI, LAN)
// and Gemini. No local whisper support in this build.

import { getTransport } from './providers.js';
import { resolveProviderConfig } from './settings.js';

function normalizeBaseUrl(baseUrl) {
  return String(baseUrl || '').replace(/\/$/, '');
}

async function ensureJsonResponse(response, label) {
  if (!response.ok) {
    let detail = '';
    try {
      const payload = await response.json();
      detail = payload?.error?.message || payload?.error || payload?.detail || '';
    } catch (_error) {
      detail = await response.text().catch(() => '');
    }
    throw new Error(`${label} failed (${response.status}): ${String(detail).slice(0, 300)}`);
  }
  return response.json();
}

async function transcribeWithOpenAiCompatible(config, blob, extension) {
  const endpoint = `${normalizeBaseUrl(config.baseUrl)}/audio/transcriptions`;
  const formData = new FormData();
  const audioFile = new File([blob], `recording-${Date.now()}.${extension}`, { type: blob.type });
  const headers = {};

  formData.append('file', audioFile);
  formData.append('model', config.model);
  formData.append('response_format', 'json');

  if (config.apiKey) {
    headers.Authorization = `Bearer ${config.apiKey}`;
  }

  const response = await fetch(endpoint, { method: 'POST', headers, body: formData });
  const json = await ensureJsonResponse(response, 'Speech request');
  const text = json.text || '';
  if (!text.trim()) {
    throw new Error('The speech provider returned an empty transcript.');
  }
  return text.trim();
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = reader.result;
      if (typeof result !== 'string') {
        reject(new Error('Could not encode audio input.'));
        return;
      }
      resolve(result.split(',')[1]);
    };
    reader.onerror = () => reject(new Error('Could not read audio input.'));
    reader.readAsDataURL(blob);
  });
}

async function transcribeWithGemini(config, blob) {
  const endpoint = `${normalizeBaseUrl(config.baseUrl)}/models/${config.model}:generateContent?key=${config.apiKey}`;
  const base64 = await blobToBase64(blob);
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents: [{
        parts: [
          { text: 'Transcribe this audio exactly as spoken. Return only the transcript text.' },
          { inline_data: { mime_type: blob.type || 'audio/wav', data: base64 } }
        ]
      }],
      generationConfig: { temperature: 0 }
    })
  });
  const json = await ensureJsonResponse(response, 'Gemini speech request');
  const text = json.candidates?.[0]?.content?.parts?.[0]?.text || '';
  if (!text.trim()) {
    throw new Error('The speech provider returned an empty transcript.');
  }
  return text.trim();
}

export async function transcribeBlob(blob, extension, settings) {
  const config = resolveProviderConfig(settings);
  const transport = getTransport(config.provider);

  if (transport === 'gemini') {
    return transcribeWithGemini(config, blob);
  }
  return transcribeWithOpenAiCompatible(config, blob, extension);
}

export async function discoverModels(settings) {
  const config = resolveProviderConfig(settings);
  const transport = getTransport(config.provider);

  if (transport === 'gemini') {
    const endpoint = `${normalizeBaseUrl(config.baseUrl)}/models?key=${config.apiKey}`;
    const response = await fetch(endpoint);
    const json = await ensureJsonResponse(response, 'Gemini model discovery');
    return (json.models || [])
      .filter((model) => (model.supportedGenerationMethods || []).includes('generateContent'))
      .map((model) => ({ id: model.name.replace(/^models\//, ''), label: model.displayName || model.name }));
  }

  const endpoint = `${normalizeBaseUrl(config.baseUrl)}/models`;
  const headers = {};
  if (config.apiKey) {
    headers.Authorization = `Bearer ${config.apiKey}`;
  }
  const response = await fetch(endpoint, { headers });
  const json = await ensureJsonResponse(response, 'Model discovery');
  return (json.data || [])
    .map((model) => ({ id: model.id, label: model.id }))
    .sort((a, b) => a.id.localeCompare(b.id));
}
