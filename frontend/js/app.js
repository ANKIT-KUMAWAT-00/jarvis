/**
 * JARVIS Main Frontend Controller
 * Connects WebSockets, manages state transitions, updates HUDs, and handles user interactions.
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Initialize Visual Core
  const visualCore = new VisualCore('core-canvas');

  // 2. Initialize Knowledge Graph
  const knowledgeGraph = new KnowledgeGraphView('graph-canvas');

  // 3. Audio Chime Generator using Web Audio API (Zero external assets needed!)
  const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  function playChime(type) {
    if (audioCtx.state === 'suspended') audioCtx.resume();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);

    const now = audioCtx.currentTime;
    if (type === 'activate') {
      osc.frequency.setValueAtTime(440, now);
      osc.frequency.exponentialRampToValueAtTime(880, now + 0.15);
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.2);
      osc.start(now);
      osc.stop(now + 0.2);
    } else if (type === 'success') {
      osc.frequency.setValueAtTime(587.33, now);
      osc.frequency.exponentialRampToValueAtTime(880, now + 0.25);
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
      osc.start(now);
      osc.stop(now + 0.3);
    } else if (type === 'alert') {
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(220, now);
      osc.frequency.setValueAtTime(180, now + 0.1);
      gain.gain.setValueAtTime(0.06, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
      osc.start(now);
      osc.stop(now + 0.25);
    }
  }

  // 4. Voice Engine
  const voice = new VoiceEngine(
    // onTranscriptReady
    (transcript) => {
      dispatchCommand(transcript);
    },
    // onInterruption
    () => {
      interruptExecution();
    },
    // onStateChange
    (state) => {
      const btnMic = document.getElementById('btn-mic');
      if (btnMic) {
        if (state === 'LISTENING') btnMic.classList.add('listening');
        else btnMic.classList.remove('listening');
      }
      visualCore.setState(state);
    }
  );

  // 5. DOM References
  const cmdForm = document.getElementById('command-form');
  const cmdInput = document.getElementById('cmd-input');
  const dialogueContainer = document.getElementById('dialogue-container');
  const btnMic = document.getElementById('btn-mic');
  const btnStop = document.getElementById('btn-stop');
  const btnVoiceToggle = document.getElementById('btn-voice-toggle');
  const btnScreenCapture = document.getElementById('btn-screen-capture');
  const btnGraphToggle = document.getElementById('btn-graph-toggle');
  const btnGraphClose = document.getElementById('btn-graph-close');
  const graphModal = document.getElementById('graph-modal');
  const confirmModal = document.getElementById('confirm-modal');
  const btnAddMemory = document.getElementById('btn-add-memory');

  // Key Modal DOM
  const keyModal = document.getElementById('key-modal');
  const metricModel = document.getElementById('metric-model');
  const btnKeyCancel = document.getElementById('btn-key-cancel');
  const btnKeySave = document.getElementById('btn-key-save');
  const inputGeminiKey = document.getElementById('input-gemini-key');
  const keyStatusMsg = document.getElementById('key-status-msg');

  if (metricModel) {
    metricModel.addEventListener('click', () => {
      if (keyModal) {
        keyModal.classList.remove('hidden');
        if (inputGeminiKey) inputGeminiKey.focus();
      }
    });
  }

  if (btnKeyCancel) {
    btnKeyCancel.addEventListener('click', () => {
      if (keyModal) keyModal.classList.add('hidden');
      if (keyStatusMsg) keyStatusMsg.style.display = 'none';
    });
  }

  if (btnKeySave) {
    btnKeySave.addEventListener('click', async () => {
      const apiKey = (inputGeminiKey ? inputGeminiKey.value : '').trim();
      if (!apiKey) {
        if (keyStatusMsg) {
          keyStatusMsg.style.display = 'block';
          keyStatusMsg.style.color = '#ff4757';
          keyStatusMsg.textContent = 'Please enter a valid Gemini API key.';
        }
        return;
      }
      btnKeySave.disabled = true;
      btnKeySave.textContent = 'Verifying...';
      if (keyStatusMsg) {
        keyStatusMsg.style.display = 'block';
        keyStatusMsg.style.color = 'var(--accent-cyan)';
        keyStatusMsg.textContent = 'Testing connection to Google Gemini API...';
      }

      try {
        const resp = await fetch('/api/config/key', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ api_key: apiKey })
        });
        const data = await resp.json();
        if (!resp.ok) {
          throw new Error(data.detail || 'Failed to verify API key');
        }
        playChime('success');
        if (keyStatusMsg) {
          keyStatusMsg.style.color = 'var(--accent-green)';
          keyStatusMsg.textContent = 'Gemini connected successfully! Brain activated.';
        }
        setTimeout(() => {
          if (keyModal) keyModal.classList.add('hidden');
          btnKeySave.disabled = false;
          btnKeySave.textContent = 'Connect Gemini Brain';
          if (keyStatusMsg) keyStatusMsg.style.display = 'none';
          if (inputGeminiKey) inputGeminiKey.value = '';
        }, 1200);
      } catch (err) {
        playChime('alert');
        btnKeySave.disabled = false;
        btnKeySave.textContent = 'Connect Gemini Brain';
        if (keyStatusMsg) {
          keyStatusMsg.style.color = '#ff4757';
          keyStatusMsg.textContent = err.message;
        }
      }
    });
  }

  // Task Telemetry DOM
  const taskStateBadge = document.getElementById('task-state-badge');
  const goalText = document.getElementById('goal-text');
  const taskStepsList = document.getElementById('task-steps-list');
  const activityStream = document.getElementById('activity-stream');

  // Memory DOM
  const memoryListContainer = document.getElementById('memory-list-container');
  const memorySearchInput = document.getElementById('memory-search-input');

  let currentConfirmationToken = null;

  // 6. Connect WebSocket
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;
  let socket = null;

  function connectWebSocket() {
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      const pulse = document.getElementById('status-pulse');
      if (pulse) pulse.className = 'pulse-indicator online';
      console.log('JARVIS Telemetry Stream Connected.');
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleServerEvent(data);
      } catch (e) {
        console.warn('WS parse error', e);
      }
    };

    socket.onclose = () => {
      const pulse = document.getElementById('status-pulse');
      if (pulse) pulse.className = 'pulse-indicator offline';
      setTimeout(connectWebSocket, 3000);
    };
  }
  connectWebSocket();

  // 7. Handle Server Telemetry Events
  function handleServerEvent(event) {
    const type = event.type;

    if (type === 'SYSTEM_READY') {
      const modelVal = document.getElementById('val-model');
      if (modelVal) {
        modelVal.textContent = event.model || 'ONLINE';
        if (event.model && (event.model.includes('mock') || event.model.includes('Offline'))) {
          modelVal.className = 'metric-val amber';
          modelVal.title = 'Offline Mock Mode. Click to configure Gemini API Key.';
        } else {
          modelVal.className = 'metric-val green';
          modelVal.title = 'Gemini Brain Active';
        }
      }
      document.getElementById('val-workspace').textContent = event.workspace || '~';
    }


    else if (type === 'THINKING') {
      visualCore.setState('THINKING');
      if (taskStateBadge) {
        taskStateBadge.textContent = 'THINKING';
        taskStateBadge.className = 'badge';
      }
    }

    else if (type === 'PLAN_FORMULATED') {
      visualCore.setState('WORKING');
      if (taskStateBadge) taskStateBadge.textContent = 'EXECUTING';
      if (goalText) goalText.textContent = event.goal;
      
      // Render step checklist
      if (taskStepsList) {
        taskStepsList.innerHTML = '';
        (event.steps || []).forEach(s => {
          const li = document.createElement('li');
          li.className = 'task-step-item';
          li.id = `step-node-${s.step_id}`;
          li.innerHTML = `
            <span class="step-icon">○</span>
            <span class="step-title">${s.title}</span>
          `;
          taskStepsList.appendChild(li);
        });
      }
    }

    else if (type === 'STEP_START') {
      const node = document.getElementById(`step-node-${event.step_id}`);
      if (node) {
        node.className = 'task-step-item running';
        node.querySelector('.step-icon').textContent = '●';
      }
    }

    else if (type === 'TOOL_ACTIVITY') {
      logActivityStream(event.tool, event.action, event.params);
    }

    else if (type === 'WAITING_FOR_PERMISSION') {
      playChime('alert');
      visualCore.setState('ERROR');
      if (taskStateBadge) {
        taskStateBadge.textContent = 'PERMISSION REQUIRED';
        taskStateBadge.className = 'badge';
      }
      showConfirmationModal(event.token, event.prompt);
    }

    else if (type === 'STEP_VERIFIED') {
      const node = document.getElementById(`step-node-${event.step_id}`);
      if (node) {
        node.className = 'task-step-item verified';
        node.querySelector('.step-icon').textContent = '✓';
      }
      logActivityVerified(event.receipt);
    }

    else if (type === 'SPEAKING') {
      visualCore.setState('SUCCESS');
      playChime('success');
      if (taskStateBadge) {
        taskStateBadge.textContent = 'COMPLETED';
        taskStateBadge.className = 'badge';
      }
      appendDialogueMessage('jarvis', event.response);
      voice.speak(event.response);
    }

    else if (type === 'MEMORY_UPDATED') {
      refreshMemories();
    }

    else if (type === 'IDLE') {
      visualCore.setState('IDLE');
      if (taskStateBadge) taskStateBadge.textContent = 'IDLE';
    }

    else if (type === 'ERROR') {
      visualCore.setState('ERROR');
      playChime('alert');
      if (taskStateBadge) taskStateBadge.textContent = 'FAILED';
      appendDialogueMessage('jarvis', event.message);
    }
  }

  // 8. Command Dispatcher
  let lastDispatchedPrompt = '';

  async function dispatchCommand(promptText) {
    if (!promptText.trim()) return;
    lastDispatchedPrompt = promptText.trim();

    appendDialogueMessage('user', promptText);
    playChime('activate');
    visualCore.setState('THINKING');

    if (cmdInput) cmdInput.value = '';

    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: promptText })
      });
      const data = await resp.json();

      if (data.state === 'WAITING_FOR_PERMISSION') {
        showConfirmationModal(data.token, data.response);
      } else if (data.response && !voice.isSpeaking) {
        // Handled via WebSocket broadcast, but fallback display if WS missed
        if (!dialogueContainer.lastElementChild?.textContent.includes(data.response.slice(0, 30))) {
          appendDialogueMessage('jarvis', data.response);
          voice.speak(data.response);
        }
      }
    } catch (e) {
      appendDialogueMessage('jarvis', `Connection error: ${e.message}`);
      visualCore.setState('ERROR');
    }
  }

  // 9. Stop / Interruption
  async function interruptExecution() {
    voice.stopSpeaking();
    visualCore.setState('IDLE');
    try {
      await fetch('/api/interrupt', { method: 'POST' });
    } catch (e) {}
  }

  // 10. Confirmation Modal Handler
  function showConfirmationModal(token, promptText) {
    currentConfirmationToken = token;
    const modal = document.getElementById('confirm-modal');
    document.getElementById('modal-token-id').textContent = `TOKEN: ${token.token_id.slice(0, 8)}...`;
    document.getElementById('modal-risk-badge').textContent = `LEVEL ${token.risk_level} CONFIRMATION`;
    document.getElementById('modal-explanation').textContent = token.explanation || promptText;
    document.getElementById('modal-target-val').textContent = `${token.tool_name} -> ${token.target}`;
    modal.classList.remove('hidden');
  }

  document.getElementById('btn-modal-confirm').addEventListener('click', async () => {
    if (!currentConfirmationToken) return;
    confirmModal.classList.add('hidden');
    try {
      await fetch('/api/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token_id: currentConfirmationToken.token_id, confirmed: true })
      });
      // Resume action with verified token and original prompt
      appendDialogueMessage('user', `[Authorized Action: ${currentConfirmationToken.action_name}]`);
      const replayPrompt = lastDispatchedPrompt || `Resume authorized action for ${currentConfirmationToken.target}`;
      await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: replayPrompt,
          token_id: currentConfirmationToken.token_id
        })
      });
    } catch (e) {
      console.warn('Confirm exception', e);
    }
  });

  document.getElementById('btn-modal-deny').addEventListener('click', async () => {
    if (!currentConfirmationToken) return;
    confirmModal.classList.add('hidden');
    try {
      await fetch('/api/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token_id: currentConfirmationToken.token_id, confirmed: false })
      });
      appendDialogueMessage('jarvis', 'Action was rejected by user. Operations safely halted.');
      visualCore.setState('IDLE');
    } catch (e) {}
  });

  // 11. Activity Logging
  function logActivityStream(tool, action, params) {
    if (!activityStream) return;
    const div = document.createElement('div');
    div.className = 'activity-log-line tool';
    const paramStr = JSON.stringify(params || {}).slice(0, 60);
    div.textContent = `[${tool.toUpperCase()}] ${action} (${paramStr})`;
    activityStream.appendChild(div);
    activityStream.scrollTop = activityStream.scrollHeight;
  }

  function logActivityVerified(receipt) {
    if (!activityStream) return;
    const div = document.createElement('div');
    div.className = 'activity-log-line verified';
    div.textContent = `[VERIFIED] ${receipt}`;
    activityStream.appendChild(div);
    activityStream.scrollTop = activityStream.scrollHeight;
  }

  // 12. Dialogue Message Appender
  function appendDialogueMessage(sender, text) {
    const article = document.createElement('article');
    article.className = `msg msg-${sender}`;
    const avatarLetter = sender === 'jarvis' ? 'J' : 'U';
    const meta = sender === 'jarvis' ? 'JARVIS Core' : 'User';
    
    article.innerHTML = `
      <div class="msg-avatar">${avatarLetter}</div>
      <div class="msg-body">
        <div class="msg-meta">${meta}</div>
        <div class="msg-content">${escapeHtml(text)}</div>
      </div>
    `;
    dialogueContainer.appendChild(article);
    dialogueContainer.scrollTop = dialogueContainer.scrollHeight;
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // 13. Memory Panel Data Management
  async function refreshMemories() {
    try {
      const resp = await fetch('/api/memory?limit=30');
      if (!resp.ok) return;
      const memories = await resp.json();
      
      document.getElementById('val-memories').textContent = memories.length;

      if (!memoryListContainer) return;
      memoryListContainer.innerHTML = '';
      if (memories.length === 0) {
        memoryListContainer.innerHTML = '<div class="memory-empty">No memories saved yet. Try saying: "JARVIS, remember that..."</div>';
        return;
      }

      memories.forEach(m => {
        const card = document.createElement('div');
        card.className = 'memory-card';
        card.innerHTML = `
          <div class="mem-tag">${m.category}</div>
          <div class="mem-body">${escapeHtml(m.content)}</div>
        `;
        memoryListContainer.appendChild(card);
      });
    } catch (e) {
      console.warn('Memory load failed', e);
    }
  }

  // Search filter
  if (memorySearchInput) {
    memorySearchInput.addEventListener('input', (e) => {
      const filter = e.target.value.toLowerCase();
      const cards = memoryListContainer.querySelectorAll('.memory-card');
      cards.forEach(c => {
        const text = c.textContent.toLowerCase();
        c.style.display = text.includes(filter) ? 'block' : 'none';
      });
    });
  }

  // Add explicit memory prompt
  if (btnAddMemory) {
    btnAddMemory.addEventListener('click', async () => {
      const fact = prompt('Enter a fact, project detail, or preference to commit to memory:');
      if (fact && fact.trim()) {
        await fetch('/api/remember', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ fact: fact.trim() })
        });
        refreshMemories();
      }
    });
  }

  // 14. Event Listeners for Toolbar Controls
  if (cmdForm) {
    cmdForm.addEventListener('submit', (e) => {
      e.preventDefault();
      dispatchCommand(cmdInput.value);
    });
  }

  if (btnMic) {
    btnMic.addEventListener('click', () => {
      voice.toggleListening();
    });
  }

  if (btnStop) {
    btnStop.addEventListener('click', () => {
      interruptExecution();
    });
  }

  if (btnVoiceToggle) {
    btnVoiceToggle.addEventListener('click', () => {
      const muted = voice.toggleMute();
      document.getElementById('label-speaker').textContent = muted ? 'Voice: OFF' : 'Voice: ON';
      btnVoiceToggle.style.opacity = muted ? '0.6' : '1.0';
    });
  }

  if (btnScreenCapture) {
    btnScreenCapture.addEventListener('click', async () => {
      dispatchCommand('What am I looking at on my screen?');
    });
  }

  if (btnGraphToggle) {
    btnGraphToggle.addEventListener('click', () => {
      graphModal.classList.remove('hidden');
      knowledgeGraph.loadData();
    });
  }

  if (btnGraphClose) {
    btnGraphClose.addEventListener('click', () => {
      graphModal.classList.add('hidden');
    });
  }

  // 15. Initial Load Health Check
  async function initHealth() {
    try {
      const resp = await fetch('/api/health');
      if (!resp.ok) return;
      const data = await resp.json();
      
      document.getElementById('val-model').textContent = data.active_model;
      if (data.system_info && data.system_info.architecture) {
        document.getElementById('val-arch').textContent = `macOS ${data.system_info.architecture}`;
      }
      refreshMemories();
    } catch (e) {
      console.warn('Health check exception', e);
    }
  }
  initHealth();
});
