// Settings persistence in localStorage.

import { getProviderProfile } from './providers.js';

const STORAGE_KEY = 'wv1_settings';

export const defaultSettings = {
  provider: 'lemonade',
  apiKey: '',
  baseUrl: '',
  model: '',
  timestamps: false
};

export function loadSettings() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { ...defaultSettings };
    }
    const parsed = JSON.parse(raw);
    return { ...defaultSettings, ...parsed };
  } catch (_error) {
    return { ...defaultSettings };
  }
}

export function saveSettings(settings) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

// Resolve the effective base URL and model for a provider.
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
