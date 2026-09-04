/**
 * JARVIS Voice Engine
 * Handles Speech Recognition (with 1800ms natural speech pause detection,
 * wake-word extension, anti-echo mic muting, and instant interruption)
 * and Speech Synthesis (TTS with single-dispatch, mute, and echo suppression).
 */

class VoiceEngine {
  constructor(onTranscriptReady, onInterruption, onStateChange, onInterim) {
    this.onTranscriptReady = onTranscriptReady;
    this.onInterruption = onInterruption;
    this.onStateChange = onStateChange;
    this.onInterim = onInterim;

    this.finishMs = 1800; // 1.8s silence window to hear complete sentences
    this.isListening = false;
    this.isSpeaking = false;
    this.isMuted = false;
    this.isPausedForSpeech = false;

    this.bufferText = '';
    this.currentInterim = '';
    this.finishTimer = null;
    this.lastDispatched = '';
    this.lastDispatchedTime = 0;

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
      if (this.onStateChange && !this.isSpeaking) this.onStateChange('LISTENING');
    };

    this.recognition.onresult = (event) => {
      // Ignore microphone input while JARVIS is speaking or processing (anti-echo)
      if (this.isSpeaking || this.isPausedForSpeech) {
        return;
      }

      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          this.bufferText += ' ' + transcript;
        } else {
          interim += transcript;
        }
      }

      this.currentInterim = interim;
      const combined = (this.bufferText + ' ' + interim).trim();
      if (!combined) return;

      const lowerText = combined.toLowerCase();

      // Fast Interruption Bypass: if user says "stop", "cancel", "wait", "ruko"
      if (['stop', 'wait', 'cancel', 'abort', 'ruko', 'chup'].includes(lowerText)) {
        this.clearBuffer();
        this.stopSpeaking();
        if (this.onInterruption) this.onInterruption();
        return;
      }

      // Live caption / interim visual feedback
      if (this.onInterim) {
        this.onInterim(combined);
      }

      // If user only spoke a wake-word ("jarvis", "hey jarvis", "jarvis hindi"),
      // give an extended 2800ms silence window to let them complete their command
      const isWakeOnly = /^(hey\s+)?jarvis(\s+(hindi|bhai|ji))?$/i.test(lowerText);
      const waitDelay = isWakeOnly ? 2800 : this.finishMs;

      if (this.finishTimer) clearTimeout(this.finishTimer);
      this.finishTimer = setTimeout(() => {
        this.finalizeAndDispatch();
      }, waitDelay);
    };

    this.recognition.onerror = (e) => {
      if (e.error !== 'no-speech') {
        console.warn('SpeechRecognition error:', e.error);
      }
    };

    this.recognition.onend = () => {
      // Auto-restart recognition if continuous mode is still desired and not paused
      if (this.isListening && !this.isPausedForSpeech) {
        try {
          this.recognition.start();
        } catch (e) {}
      } else {
        this.isListening = false;
        if (this.onStateChange && !this.isSpeaking) this.onStateChange('IDLE');
      }
    };
  }

  finalizeAndDispatch() {
    if (this.isSpeaking || this.isPausedForSpeech) return;

    const finalText = (this.bufferText + ' ' + this.currentInterim).trim();
    this.clearBuffer();

    if (!finalText) return;

    // Suppress rapid duplicate dispatches
    const now = Date.now();
    if (finalText.toLowerCase() === this.lastDispatched.toLowerCase() && (now - this.lastDispatchedTime < 2500)) {
      console.log('VoiceEngine: Suppressed duplicate speech dispatch:', finalText);
      return;
    }

    this.lastDispatched = finalText;
    this.lastDispatchedTime = now;

    // Mute mic before sending so JARVIS never listens to his own echo
    this.pauseListening();

    if (this.onTranscriptReady) {
      this.onTranscriptReady(finalText);
    }
  }

  clearBuffer() {
    this.bufferText = '';
    this.currentInterim = '';
    if (this.finishTimer) {
      clearTimeout(this.finishTimer);
      this.finishTimer = null;
    }
  }

  pauseListening() {
    this.isPausedForSpeech = true;
    this.clearBuffer();
  }

  resumeListening() {
    this.isPausedForSpeech = false;
    this.clearBuffer();
    if (this.isListening && this.recognition) {
      try {
        this.recognition.start();
      } catch (e) {}
    }
  }

  initVoices() {
    if (!this.synth) return;
    const selectVoice = () => {
      const voices = this.synth.getVoices();
      this.preferredVoice = voices.find(v => 
        (v.name.includes('Daniel') || v.name.includes('Google UK English Male') || v.name.includes('Oliver') || v.name.includes('Samantha') || v.name.includes('Rishi')) && v.lang.startsWith('en')
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
      this.isListening = false;
      this.pauseListening();
      try {
        this.recognition.stop();
      } catch (e) {}
      if (this.onStateChange) this.onStateChange('IDLE');
      return false;
    } else {
      this.stopSpeaking();
      this.resumeListening();
      this.isListening = true;
      try {
        this.recognition.start();
        if (this.onStateChange) this.onStateChange('LISTENING');
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

    // Immediately pause recognition while speaking to prevent mic from hearing speakers
    this.pauseListening();

    const utterance = new SpeechSynthesisUtterance(cleanText);
    if (this.preferredVoice) utterance.voice = this.preferredVoice;
    utterance.rate = 1.05;
    utterance.pitch = 0.95;

    utterance.onstart = () => {
      this.isSpeaking = true;
      if (this.onStateChange) this.onStateChange('SPEAKING');
    };

    const finishSpeech = () => {
      this.isSpeaking = false;
      if (this.onStateChange) this.onStateChange('IDLE');
      // Buffer of 400ms after speech ends to prevent speaker reverberation
      setTimeout(() => {
        if (!this.isSpeaking) {
          this.resumeListening();
        }
      }, 400);
    };

    utterance.onend = finishSpeech;
    utterance.onerror = finishSpeech;

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
