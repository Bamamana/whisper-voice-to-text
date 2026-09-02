// Settings persistence in localStorage (API-only build).

import { getProviderProfile } from './providers.js';

const STORAGE_KEY = 'wv1api_settings';

export const defaultSettings = {
  provider: 'hosted',
  apiKey: '',
  baseUrl: '',
  model: '',
  liveModel: ''
};

export function loadSettings() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { ...defaultSettings };
    }
    return { ...defaultSettings, ...JSON.parse(raw) };
  } catch (_error) {
    return { ...defaultSettings };
  }
}

export function saveSettings(settings) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

export function resolveProviderConfig(settings) {
  const profile = getProviderProfile(settings.provider);
  // When the app is served from the hosted server (same origin as the /v1
  // proxy), "hosted" mode uses relative paths — no CORS, Access cookie applies.
  const hosted = settings.provider === 'hosted';
  return {
    provider: settings.provider,
    transport: profile.transport,
    baseUrl: hosted ? '' : (settings.baseUrl || profile.url || '').replace(/\/$/, ''),
    apiKey: settings.apiKey || '',
    model: settings.model || profile.sttModel
  };
}
