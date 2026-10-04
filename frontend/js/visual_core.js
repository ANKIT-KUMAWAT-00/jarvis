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

  animate() {
    this.time += 0.025;
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.width, this.height);

    const cx = this.width / 2;
    const cy = this.height / 2;
    const theme = this.getColorTheme();

    // 1. Central Ambient Glow
    const bgGrad = ctx.createRadialGradient(cx, cy, 5, cx, cy, 90);
    bgGrad.addColorStop(0, theme.glow);
    bgGrad.addColorStop(1, 'rgba(6, 9, 15, 0)');
    ctx.fillStyle = bgGrad;
    ctx.beginPath();
    ctx.arc(cx, cy, 90, 0, Math.PI * 2);
    ctx.fill();

    // 2. Orbital Rings
    const ringSpeed = (this.state === 'THINKING' || this.state === 'WORKING') ? 1.8 : 0.8;
    this.drawRing(cx, cy, 45, this.time * ringSpeed, theme.primary, 1.5, [6, 12]);
    this.drawRing(cx, cy, 65, -this.time * 0.7 * ringSpeed, theme.secondary, 1.2, [18, 8]);
    this.drawRing(cx, cy, 85, this.time * 0.5 * ringSpeed, theme.primary, 0.8, [3, 10]);

    // 3. Audio Waveform (for LISTENING mode)
    if (this.state === 'LISTENING') {
      ctx.beginPath();
      ctx.strokeStyle = theme.primary;
      ctx.lineWidth = 2;
      for (let x = -80; x <= 80; x += 4) {
        const dist = 1 - Math.abs(x) / 80;
        const wave = Math.sin(x * 0.15 + this.time * 6) * 16 * dist;
        const px = cx + x;
        const py = cy + wave;
        if (x === -80) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.stroke();
    }

    // 4. Central Reactor Core
    const corePulse = Math.sin(this.time * 3) * 2;
    ctx.beginPath();
    ctx.arc(cx, cy, 14 + corePulse, 0, Math.PI * 2);
    ctx.fillStyle = theme.primary;
    ctx.shadowColor = theme.primary;
    ctx.shadowBlur = 15;
    ctx.fill();
    ctx.shadowBlur = 0;

    // 5. Orbital Neural Nodes / Particles
    this.particles.forEach(p => {
      p.angle += p.speed * ringSpeed;
      const px = cx + Math.cos(p.angle) * p.radius;
      const py = cy + Math.sin(p.angle) * (p.radius * 0.75); // slight perspective

      ctx.beginPath();
      ctx.arc(px, py, p.size, 0, Math.PI * 2);
      ctx.fillStyle = theme.primary;
      ctx.globalAlpha = p.alpha;
      ctx.fill();
      ctx.globalAlpha = 1.0;
    });

    requestAnimationFrame(this.animate);
  }

  drawRing(cx, cy, radius, angleOffset, color, lineWidth, dashArray) {
    const ctx = this.ctx;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(angleOffset);
    ctx.beginPath();
    ctx.arc(0, 0, radius, 0, Math.PI * 2);
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;
    if (dashArray) ctx.setLineDash(dashArray);
    ctx.stroke();
    ctx.restore();
  }
}
