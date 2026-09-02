// Transcription backends: OpenAI-compatible (Lemonade, OpenRouter, OpenAI, LAN)
// and Gemini. No local whisper support in this build.

import { getTransport } from './providers.js';
import { resolveProviderConfig } from './settings.js';

function normalizeBaseUrl(baseUrl) {
  // Empty base = same-origin (hosted mode): the app and the /v1 proxy share
  // an origin, so relative URLs are used directly. The /v1 prefix is part of
  // the endpoint paths below.
  return String(baseUrl || '').replace(/\/$/, '');
}

// Build an endpoint URL. In hosted mode (empty base) endpoints are relative
// and already include /v1; otherwise base already ends with /v1.
function endpointUrl(config, path) {
  const base = normalizeBaseUrl(config.baseUrl);
  if (!base) {
    return `/v1${path}`;
  }
  return `${base}${path}`;
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

// Wrap fetch so DNS/connection failures say what actually happened instead
// of surfacing as misleading status codes.
async function fetchOrThrow(url, options, label) {
  try {
    return await fetch(url, options);
  } catch (error) {
    const reason = String(error?.message || error);
    if (/failed to fetch|name_not_resolved|networkerror/i.test(reason)) {
      throw new Error(`${label}: could not reach the server (DNS or connection failed). Check the Base URL and your internet connection.`);
    }
    throw error;
  }
}

async function transcribeWithOpenAiCompatible(config, blob, extension) {
  const endpoint = endpointUrl(config, '/audio/transcriptions');
  const formData = new FormData();
  const audioFile = new File([blob], `recording-${Date.now()}.${extension}`, { type: blob.type });
  const headers = {};

  formData.append('file', audioFile);
  formData.append('model', config.model);
  // NOTE: no response_format field — Lemonade's whisper endpoint 500s on it.
  // The working crawler (organize_es.py) sends only model + file.

  if (config.apiKey) {
    headers.Authorization = `Bearer ${config.apiKey}`;
  }

  const response = await fetchOrThrow(endpoint, { method: 'POST', headers, body: formData }, 'Speech request');
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
  const response = await fetchOrThrow(endpoint, {
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
    }, 'Gemini speech request');
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
    const response = await fetchOrThrow(endpoint, {}, 'Gemini model discovery');
    const json = await ensureJsonResponse(response, 'Gemini model discovery');
    return (json.models || [])
      .filter((model) => (model.supportedGenerationMethods || []).includes('generateContent'))
      .map((model) => ({ id: model.name.replace(/^models\//, ''), label: model.displayName || model.name }));
  }

  const endpoint = endpointUrl(config, '/models');
  const headers = {};
  if (config.apiKey) {
    headers.Authorization = `Bearer ${config.apiKey}`;
  }
  const response = await fetchOrThrow(endpoint, { headers }, 'Model discovery');
  const json = await ensureJsonResponse(response, 'Model discovery');
  return (json.data || [])
    .map((model) => ({ id: model.id, label: model.id }))
    .sort((a, b) => a.id.localeCompare(b.id));
}

export async function createChatCompletion(settings, model, prompt) {
  const config = resolveProviderConfig(settings);
  if (getTransport(config.provider) !== 'openai') {
    throw new Error('Voice Grading requires an OpenAI-compatible chat provider.');
  }
  if (!model.trim()) {
    throw new Error('Select a grading model first.');
  }

  const headers = { 'Content-Type': 'application/json' };
  if (config.apiKey) {
    headers.Authorization = `Bearer ${config.apiKey}`;
  }
  const response = await fetchOrThrow(endpointUrl(config, '/chat/completions'), {
    method: 'POST',
    headers,
    body: JSON.stringify({
      model,
      messages: [{ role: 'user', content: prompt }],
      temperature: 0.1,
      max_tokens: 1024,
      response_format: { type: 'json_object' }
    })
  }, 'Grade analysis');
  const json = await ensureJsonResponse(response, 'Grade analysis');
  const content = json.choices?.[0]?.message?.content;
  if (typeof content !== 'string' || !content.trim()) {
    throw new Error('The grading model returned no response.');
  }
  return content;
}
