/**
 * JARVIS Interactive Knowledge Graph Visualizer
 * Physics-based 2D Canvas force-directed graph connecting notes, projects, and memories.
 */

class KnowledgeGraphView {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.nodes = [];
    this.links = [];
    this.selectedNode = null;
    this.hoveredNode = null;
    this.time = 0;
    this.isRunning = false;

    this.initCanvas();
    this.setupEvents();
    this.animate = this.animate.bind(this);
  }

  initCanvas() {
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = 800 * dpr;
    this.canvas.height = 480 * dpr;
    this.ctx.scale(dpr, dpr);
    this.width = 800;
    this.height = 480;
  }

  setupEvents() {
    this.canvas.addEventListener('mousemove', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const mx = (e.clientX - rect.left) * (this.width / rect.width);
      const my = (e.clientY - rect.top) * (this.height / rect.height);
      
      this.hoveredNode = this.nodes.find(n => {
        const dx = n.x - mx;
        const dy = n.y - my;
        return Math.sqrt(dx * dx + dy * dy) < (n.size + 4);
      });

      this.canvas.style.cursor = this.hoveredNode ? 'pointer' : 'default';
    });

    this.canvas.addEventListener('click', () => {
      if (this.hoveredNode) {
        this.selectedNode = this.hoveredNode;
        const infoBanner = document.getElementById('graph-node-info');
        if (infoBanner) {
          infoBanner.textContent = `[${this.selectedNode.type.toUpperCase()}] ${this.selectedNode.info}`;
        }
      }
    });
  }

  async loadData() {
    try {
      const resp = await fetch('/api/knowledge-graph');
      if (!resp.ok) return;
      const data = await resp.json();
      
      const cx = this.width / 2;
      const cy = this.height / 2;

      // Position nodes in radial spread
      this.nodes = (data.nodes || []).map((n, i) => {
        const angle = (i / Math.max(1, data.nodes.length)) * Math.PI * 2;
        const dist = n.type === 'core' ? 0 : 90 + (i % 3) * 55;
        return {
          ...n,
          x: cx + Math.cos(angle) * dist,
          y: cy + Math.sin(angle) * dist,
          vx: 0,
          vy: 0
        };
      });

      this.links = data.links || [];
      if (!this.isRunning) {
        this.isRunning = true;
        requestAnimationFrame(this.animate);
      }
    } catch (e) {
      console.warn('Failed to load knowledge graph', e);
    }
  }

  animate() {
    if (!this.isRunning) return;
    this.time += 0.02;
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.width, this.height);

    const cx = this.width / 2;
    const cy = this.height / 2;

    // Gentle spring relaxation
    for (let i = 0; i < this.nodes.length; i++) {
      const n1 = this.nodes[i];
      // Slight pull to center
      if (n1.type !== 'core') {
        n1.vx += (cx - n1.x) * 0.0005;
        n1.vy += (cy - n1.y) * 0.0005;
      }

      // Repulsion between nodes
      for (let j = i + 1; j < this.nodes.length; j++) {
        const n2 = this.nodes[j];
        const dx = n2.x - n1.x;
        const dy = n2.y - n1.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        if (dist < 120) {
          const force = (120 - dist) * 0.002;
          n1.vx -= (dx / dist) * force;
          n1.vy -= (dy / dist) * force;
          n2.vx += (dx / dist) * force;
          n2.vy += (dy / dist) * force;
        }
      }

      n1.x += n1.vx;
      n1.y += n1.vy;
      n1.vx *= 0.88; // Damping
      n1.vy *= 0.88;
    }

    // 1. Draw Links
    const nodeMap = new Map(this.nodes.map(n => [n.id, n]));
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.2)';
    ctx.lineWidth = 1;
    this.links.forEach(l => {
      const src = nodeMap.get(l.source);
      const tgt = nodeMap.get(l.target);
      if (src && tgt) {
        ctx.beginPath();
        ctx.moveTo(src.x, src.y);
        ctx.lineTo(tgt.x, tgt.y);
        ctx.stroke();
      }
    });

    // 2. Draw Nodes
    this.nodes.forEach(n => {
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.size, 0, Math.PI * 2);
      ctx.fillStyle = n.color || '#00f0ff';
      ctx.fill();

      if (n === this.selectedNode || n === this.hoveredNode) {
        ctx.lineWidth = 2.5;
        ctx.strokeStyle = '#fff';
        ctx.stroke();
      }

      // Node Label
      ctx.fillStyle = '#f0f6fc';
      ctx.font = '10px Outfit, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(n.label, n.x, n.y + n.size + 12);
    });

    requestAnimationFrame(this.animate);
  }
}
