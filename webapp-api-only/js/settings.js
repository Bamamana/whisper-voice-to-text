// Settings persistence in localStorage (API-only build).

import { getProviderProfile } from './providers.js';

const STORAGE_KEY = 'wv1api_settings';

export const defaultSettings = {
  provider: 'lemonade',
  apiKey: '',
  baseUrl: '',
  model: ''
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
  return {
    provider: settings.provider,
    transport: profile.transport,
    baseUrl: (settings.baseUrl || profile.url || '').replace(/\/$/, ''),
    apiKey: settings.apiKey || '',
    model: settings.model || profile.sttModel
  };
}
