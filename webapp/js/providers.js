// Provider profiles shared by all transcription backends.
// Mirrors AuraEdit's server/provider-defaults.js.

export const providerProfiles = {
  local: {
    label: 'Local Whisper (Python bridge)',
    transport: 'local',
    url: 'http://127.0.0.1:8177',
    apiKeyRequired: false,
    sttModel: 'auto'
  },
  lemonade: {
    label: 'AMD Lemonade',
    transport: 'openai',
    url: 'http://localhost:13305/v1',
    apiKeyRequired: false,
    sttModel: 'Whisper-Large-v3-Turbo'
  },
  openrouter: {
    label: 'OpenRouter',
    transport: 'openai',
    url: 'https://openrouter.ai/api/v1',
    apiKeyRequired: true,
    sttModel: 'openai/whisper-1'
  },
  openai: {
    label: 'OpenAI',
    transport: 'openai',
    url: 'https://api.openai.com/v1',
    apiKeyRequired: true,
    sttModel: 'whisper-1'
  },
  gemini: {
    label: 'Gemini',
    transport: 'gemini',
    url: 'https://generativelanguage.googleapis.com/v1beta',
    apiKeyRequired: true,
    sttModel: 'gemini-2.5-flash'
  },
  compatible: {
    label: 'OpenAI-Compatible',
    transport: 'openai',
    url: '',
    apiKeyRequired: false,
    sttModel: 'whisper-1'
  }
};

export const PROVIDER_ORDER = ['lemonade', 'openrouter', 'openai', 'gemini', 'local', 'compatible'];

export function getProviderProfile(provider) {
  return providerProfiles[provider] || providerProfiles.compatible;
}

export function getTransport(provider) {
  return getProviderProfile(provider).transport;
}
