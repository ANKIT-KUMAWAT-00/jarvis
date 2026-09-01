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
