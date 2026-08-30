// Live transcription over Lemonade's OpenAI Realtime WebSocket API.
// Protocol (from lemonade-sdk docs/api/openai.md `WS /realtime`):
//   - Connect: ws://host:port/v1/realtime?model=<name>
//   - Send: session.update, then input_audio_buffer.append (base64 PCM16 mono 16kHz)
//   - Recv: conversation.item.input_audio_transcription.delta (interim)
//           conversation.item.input_audio_transcription.completed (final)
//   - Stop: input_audio_buffer.commit, wait for final, close.

const CHUNK_MS = 100;
const SAMPLE_RATE = 16000;

export class LiveTranscriber {
  constructor({ onInterim, onFinal, onStatus, onError } = {}) {
    this.onInterim = onInterim || (() => {});
    this.onFinal = onFinal || (() => {});
    this.onStatus = onStatus || (() => {});
    this.onError = onError || (() => {});
    this.ws = null;
    this.audioContext = null;
    this.stream = null;
    this.processor = null;
    this.active = false;
    this.finalText = '';
  }

  // baseUrl like http://localhost:13305/v1 -> ws://host/v1/realtime
  // Empty baseUrl = hosted mode: same-origin, use the current host.
  static wsUrlFromBaseUrl(baseUrl, model) {
    let host;
    if (!baseUrl) {
      host = window.location.host;
      const scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${scheme}//${host}/v1/realtime?model=${encodeURIComponent(model)}`;
    }
    const url = new URL(baseUrl);
    const scheme = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${scheme}//${url.host}/v1/realtime?model=${encodeURIComponent(model)}`;
  }

  async start(baseUrl, model) {
    const wsUrl = LiveTranscriber.wsUrlFromBaseUrl(baseUrl, model);
    this.onStatus('Connecting to live stream...');

    this.ws = new WebSocket(wsUrl);
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('WebSocket connect timeout')), 5000);
      this.ws.onopen = () => { clearTimeout(timer); resolve(); };
      this.ws.onerror = () => { clearTimeout(timer); reject(new Error('WebSocket connect failed — is the model a streaming (realtime) model?')); };
    });

    this.ws.onmessage = (event) => this._handleMessage(event);
    this.ws.onclose = () => { if (this.active) this.onStatus('Live stream disconnected.'); };
    this.ws.onerror = () => { if (this.active) this.onError('WebSocket error'); };

    this.ws.send(JSON.stringify({ type: 'session.update', session: { model } }));
    this.active = true;
    this.finalText = '';

    await this._startMic();
    this.onStatus('Live — speak now, words appear as you talk.');
  }

  _handleMessage(event) {
    let msg;
    try { msg = JSON.parse(event.data); } catch (_e) { return; }
    switch (msg.type) {
      case 'conversation.item.input_audio_transcription.delta':
        if (typeof msg.delta === 'string' && msg.delta.trim()) {
          this.onInterim(msg.delta.trim());
        }
        break;
      case 'conversation.item.input_audio_transcription.completed':
        if (typeof msg.transcript === 'string' && msg.transcript.trim()) {
          this.finalText = `${this.finalText} ${msg.transcript.trim()}`.trim();
          this.onFinal(msg.transcript.trim(), this.finalText);
        }
        break;
      case 'input_audio_buffer.speech_started':
        this.onStatus('Listening...');
        break;
      case 'error':
        this.onError(msg.error?.message || 'Server error');
        break;
    }
  }

  async _startMic() {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: SAMPLE_RATE });

    // Resample to 16kHz mono PCM16 and stream base64 chunks.
    // ScriptProcessor buffer must be a power of two (256–16384); 4096 @16kHz = 256ms.
    const source = this.audioContext.createMediaStreamSource(this.stream);
    this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);

    this.processor.onaudioprocess = (e) => {
      if (!this.active || !this.ws || this.ws.readyState !== WebSocket.OPEN) return;
      const samples = e.inputBuffer.getChannelData(0);

      const pcm = new Int16Array(samples.length);
      for (let i = 0; i < samples.length; i += 1) {
        const s = Math.max(-1, Math.min(1, samples[i]));
        pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }
      const b64 = this._bytesToBase64(new Uint8Array(pcm.buffer));
      this.ws.send(JSON.stringify({ type: 'input_audio_buffer.append', audio: b64 }));
    };

    source.connect(this.processor);
    this.processor.connect(this.audioContext.destination); // ScriptProcessor needs a destination
  }

  _bytesToBase64(bytes) {
    let binary = '';
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
    }
    return btoa(binary);
  }

  // Stop mic, commit remaining audio, wait briefly for the final transcript.
  async stop() {
    this.active = false;
    if (this.processor) { this.processor.disconnect(); this.processor = null; }
    if (this.stream) { this.stream.getTracks().forEach((t) => t.stop()); this.stream = null; }
    if (this.audioContext) { await this.audioContext.close().catch(() => {}); this.audioContext = null; }

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'input_audio_buffer.commit' }));
      // Give the server a moment to deliver the final transcript.
      await new Promise((r) => setTimeout(r, 1500));
      this.ws.close(1000, 'OK');
    }
    this.ws = null;
    this.onStatus('Live session ended.');
    return this.finalText;
  }
}
