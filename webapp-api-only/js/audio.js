// Microphone recording -> WAV blob (mirrors AuraEdit's audio-format.js).

let audioContext = null;

function getAudioContext() {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) {
    throw new Error('This browser cannot record audio.');
  }
  if (!audioContext || audioContext.state === 'closed') {
    audioContext = new AudioContextClass();
  }
  return audioContext;
}

function clampSample(sample) {
  return Math.max(-1, Math.min(1, sample));
}

export function encodeAudioBufferToWav(audioBuffer) {
  const channelCount = audioBuffer.numberOfChannels;
  const frameCount = audioBuffer.length;
  const bytesPerSample = 2;
  const blockAlign = channelCount * bytesPerSample;
  const byteRate = audioBuffer.sampleRate * blockAlign;
  const pcmDataLength = frameCount * blockAlign;
  const buffer = new ArrayBuffer(44 + pcmDataLength);
  const view = new DataView(buffer);

  const writeAscii = (offset, value) => {
    for (let index = 0; index < value.length; index += 1) {
      view.setUint8(offset + index, value.charCodeAt(index));
    }
  };

  writeAscii(0, 'RIFF');
  view.setUint32(4, 36 + pcmDataLength, true);
  writeAscii(8, 'WAVE');
  writeAscii(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM format code — required, or the WAV is invalid
  view.setUint16(22, channelCount, true);
  view.setUint32(24, audioBuffer.sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint32(32, blockAlign, true);
  view.setUint16(34, 16, true);
  writeAscii(36, 'data');
  view.setUint32(40, pcmDataLength, true);

  const channels = Array.from({ length: channelCount }, (_v, i) => audioBuffer.getChannelData(i));
  let offset = 44;
  for (let frameIndex = 0; frameIndex < frameCount; frameIndex += 1) {
    for (let channelIndex = 0; channelIndex < channelCount; channelIndex += 1) {
      const sample = clampSample(channels[channelIndex][frameIndex] ?? 0);
      const intSample = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
      view.setInt16(offset, intSample, true);
      offset += bytesPerSample;
    }
  }

  return buffer;
}

export async function blobToWav(audioBlob) {
  const mimeType = String(audioBlob?.type || '').trim().toLowerCase();
  if (mimeType === 'audio/wav' || mimeType === 'audio/wave' || mimeType === 'audio/x-wav') {
    return { blob: audioBlob, mimeType: 'audio/wav', extension: 'wav' };
  }

  const context = getAudioContext();
  try {
    const sourceBuffer = await audioBlob.arrayBuffer();
    const decoded = await context.decodeAudioData(sourceBuffer.slice(0));
    const wavBuffer = encodeAudioBufferToWav(decoded);
    return {
      blob: new Blob([wavBuffer], { type: 'audio/wav' }),
      mimeType: 'audio/wav',
      extension: 'wav'
    };
  } catch (_error) {
    throw new Error('Could not convert the recording into WAV for transcription.');
  }
}

export class MicRecorder {
  constructor() {
    this.stream = null;
    this.mediaRecorder = null;
    this.chunks = [];
    this.recording = false;
  }

  async start() {
    if (this.recording) return;
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.chunks = [];
    this.mediaRecorder = new MediaRecorder(this.stream);
    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        this.chunks.push(event.data);
      }
    };
    this.mediaRecorder.start();
    this.recording = true;
  }

  async stop() {
    if (!this.recording) return null;
    const stopped = new Promise((resolve) => {
      this.mediaRecorder.onstop = resolve;
    });
    this.mediaRecorder.stop();
    await stopped;
    this.stream.getTracks().forEach((track) => track.stop());
    this.recording = false;
    return new Blob(this.chunks, { type: this.mediaRecorder.mimeType || 'audio/webm' });
  }
}
