/**
 * JARVIS AI Visual Core Renderer
 * Real-time dynamic canvas rendering of neural nodes, orbital rings, and stateful energy pulses.
 */

class VisualCore {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.state = 'IDLE'; // IDLE, LISTENING, THINKING, WORKING, SUCCESS, ERROR
    this.time = 0;
    this.particles = [];
    this.audioAmplitude = 0; // For speech waveform responsiveness

    this.initCanvas();
    this.initParticles();
    this.animate = this.animate.bind(this);
    requestAnimationFrame(this.animate);

    window.addEventListener('resize', () => this.initCanvas());
  }

  initCanvas() {
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width = (rect.width || 460) * dpr;
    this.canvas.height = (rect.height || 240) * dpr;
    this.ctx.scale(dpr, dpr);
    this.width = rect.width || 460;
    this.height = rect.height || 240;
  }

  initParticles() {
    this.particles = [];
    for (let i = 0; i < 40; i++) {
      this.particles.push({
        angle: Math.random() * Math.PI * 2,
        radius: 35 + Math.random() * 60,
        speed: (Math.random() - 0.5) * 0.02,
        size: 1.5 + Math.random() * 2,
        alpha: 0.3 + Math.random() * 0.6
      });
    }
  }

  setState(newState) {
    this.state = newState.toUpperCase();
    const stateLabel = document.getElementById('core-state-text');
    const subLabel = document.getElementById('core-substate-text');
    
    const descriptions = {
      IDLE: { title: 'SYSTEM STANDBY', sub: 'Listening & Reasoning Layers Active' },
      LISTENING: { title: 'VOICE CAPTURE ACTIVE', sub: 'Streaming Speech Ingestion Window' },
      THINKING: { title: 'NEURAL REASONING', sub: 'Evaluating Intent, Context & Plan' },
      WORKING: { title: 'TOOL DISPATCH ACTIVE', sub: 'Subprocess Execution & Verification' },
      SUCCESS: { title: 'OPERATION VERIFIED', sub: 'Receipt Proofs Validated' },
      ERROR: { title: 'TELEMETRY EXCEPTION', sub: 'Failure Identified & Inspected' }
    };

    if (descriptions[this.state]) {
      if (stateLabel) stateLabel.textContent = descriptions[this.state].title;
      if (subLabel) subLabel.textContent = descriptions[this.state].sub;
    }
  }

  getColorTheme() {
    switch (this.state) {
      case 'LISTENING':
        return { primary: '#00f0ff', secondary: '#0070f3', glow: 'rgba(0, 240, 255, 0.4)' };
      case 'THINKING':
        return { primary: '#7928ca', secondary: '#d946ef', glow: 'rgba(121, 40, 202, 0.5)' };
      case 'WORKING':
        return { primary: '#00df8f', secondary: '#00f0ff', glow: 'rgba(0, 223, 143, 0.5)' };
      case 'SUCCESS':
        return { primary: '#00df8f', secondary: '#58a6ff', glow: 'rgba(0, 223, 143, 0.6)' };
      case 'ERROR':
        return { primary: '#ff0055', secondary: '#f5a623', glow: 'rgba(255, 0, 85, 0.6)' };
      case 'IDLE':
      default:
        return { primary: '#00f0ff', secondary: '#0070f3', glow: 'rgba(0, 240, 255, 0.25)' };
    }
  }
