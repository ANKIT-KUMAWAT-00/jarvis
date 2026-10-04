/**
 * JARVIS Voice Engine
 * Handles Speech Recognition (with FINISH_MS=900 buffer & fast cancel bypass)
 * and Speech Synthesis (TTS with single-dispatch, mute, and interruption).
 */

class VoiceEngine {
  constructor(onTranscriptReady, onInterruption, onStateChange) {
    this.onTranscriptReady = onTranscriptReady;
    this.onInterruption = onInterruption;
    this.onStateChange = onStateChange;

    this.finishMs = 900;
    this.isListening = false;
    this.isSpeaking = false;
    this.isMuted = false;

    this.bufferText = '';
    this.finishTimer = null;

    this.recognition = null;
    this.synth = window.speechSynthesis || null;
    this.preferredVoice = null;

    this.initRecognition();
    this.initVoices();
  }

  initRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn('SpeechRecognition API not available in this browser.');
      return;
    }

    this.recognition = new SpeechRecognition();
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.lang = 'en-US';

    this.recognition.onstart = () => {
      this.isListening = true;
      if (this.onStateChange) this.onStateChange('LISTENING');
    };

    this.recognition.onresult = (event) => {
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          this.bufferText += ' ' + transcript;
        } else {
          interim += transcript;
        }
      }

      const activeText = (this.bufferText + ' ' + interim).trim().toLowerCase();

      // Fast Interruption Bypass: if user says "stop", "cancel", "wait", dispatch instantly
      if (['stop', 'wait', 'cancel', 'abort'].includes(activeText)) {
        if (this.finishTimer) clearTimeout(this.finishTimer);
        this.bufferText = '';
        this.stopSpeaking();
        if (this.onInterruption) this.onInterruption();
        return;
      }

      // Reset finish buffer window
      if (this.finishTimer) clearTimeout(this.finishTimer);
      this.finishTimer = setTimeout(() => {
        const finalText = (this.bufferText + ' ' + interim).trim();
        if (finalText.length > 0) {
          this.bufferText = '';
          this.onTranscriptReady(finalText);
        }
      }, this.finishMs);
    };

    this.recognition.onerror = (e) => {
      console.warn('SpeechRecognition error:', e.error);
      this.isListening = false;
      if (this.onStateChange) this.onStateChange('IDLE');
    };

    this.recognition.onend = () => {
      this.isListening = false;
      if (this.onStateChange) this.onStateChange('IDLE');
    };
  }

  initVoices() {
    if (!this.synth) return;
    const selectVoice = () => {
      const voices = this.synth.getVoices();
      // Prefer modern clear English voices (Daniel, Samantha, Google UK English Male, etc.)
      this.preferredVoice = voices.find(v => 
        (v.name.includes('Daniel') || v.name.includes('Google UK English Male') || v.name.includes('Oliver') || v.name.includes('Samantha')) && v.lang.startsWith('en')
      ) || voices.find(v => v.lang.startsWith('en')) || voices[0];
    };

    if (this.synth.onvoiceschanged !== undefined) {
      this.synth.onvoiceschanged = selectVoice;
    }
    selectVoice();
  }

  toggleListening() {
    if (!this.recognition) return false;
    if (this.isListening) {
      this.recognition.stop();
      this.isListening = false;
      return false;
    } else {
      this.stopSpeaking(); // Interrupt active speech when starting to listen
      this.bufferText = '';
      try {
        this.recognition.start();
        return true;
      } catch (e) {
        console.warn('Recognition start exception:', e);
        return false;
      }
    }
  }

  speak(text) {
    if (!this.synth || this.isMuted || !text) return;
    this.stopSpeaking();

    // Clean text of markdown formatting for speech
    const cleanText = text
      .replace(/```[\s\S]*?```/g, 'Code block omitted.')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/[#*_~\[\]]/g, '')
      .replace(/https?:\/\/\S+/g, 'link')
      .trim();

    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    if (this.preferredVoice) utterance.voice = this.preferredVoice;
    utterance.rate = 1.05;
    utterance.pitch = 0.95; // Slightly lower pitch for calm professional presence

    utterance.onstart = () => {
      this.isSpeaking = true;
      if (this.onStateChange) this.onStateChange('SPEAKING');
    };

    utterance.onend = () => {
      this.isSpeaking = false;
      if (this.onStateChange) this.onStateChange('IDLE');
    };

    utterance.onerror = () => {
      this.isSpeaking = false;
      if (this.onStateChange) this.onStateChange('IDLE');
    };

    this.synth.speak(utterance);
  }

  stopSpeaking() {
    if (this.synth && this.synth.speaking) {
      this.synth.cancel();
      this.isSpeaking = false;
    }
  }

  toggleMute() {
    this.isMuted = !this.isMuted;
    if (this.isMuted) this.stopSpeaking();
    return this.isMuted;
  }
}
