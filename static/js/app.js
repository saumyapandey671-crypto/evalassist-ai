/* ================================================================
   EvalAssist AI – app.js
   Handles: hamburger nav · scroll reveal · evaluate form ·
            result rendering · evidence accordion · review panel ·
            copy to clipboard · AI Engine demos
   ================================================================ */

'use strict';

// ── Utils ──────────────────────────────────────────────────────────
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];
const round2 = n => Math.round(n * 100) / 100;

function showToast(msg, type = 'info') {
  const t = document.createElement('div');
  t.className = 'toast toast-' + type;
  t.textContent = msg;
  Object.assign(t.style, {
    position: 'fixed', bottom: '24px', right: '24px', zIndex: 9999,
    background: type === 'success' ? '#1E7A4C' : type === 'error' ? '#A12C2F' : '#1F272B',
    color: '#fff', padding: '12px 20px', borderRadius: '10px',
    fontFamily: "'Poppins', sans-serif", fontSize: '13px', fontWeight: '600',
    boxShadow: '0 8px 24px rgba(0,0,0,0.25)',
    transition: 'opacity 0.3s', opacity: '0'
  });
  document.body.appendChild(t);
  requestAnimationFrame(() => { t.style.opacity = '1'; });
  setTimeout(() => {
    t.style.opacity = '0';
    setTimeout(() => t.remove(), 350);
  }, 2800);
}

// ── Hamburger menu ─────────────────────────────────────────────────
const hamburger = $('#hamburgerBtn');
const mobileNav = $('#mobileNav');
if (hamburger && mobileNav) {
  hamburger.addEventListener('click', () => {
    const open = hamburger.classList.toggle('open');
    mobileNav.classList.toggle('open', open);
    hamburger.setAttribute('aria-expanded', String(open));
  });
}

// ── Scroll-reveal ──────────────────────────────────────────────────
const revealEls = $$('.reveal');
if (revealEls.length) {
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); } });
  }, { threshold: 0.12 });
  revealEls.forEach(el => obs.observe(el));
}

// ── Copy to clipboard helper ───────────────────────────────────────
function copyCode(btn) {
  const block = btn.closest('.code-block');
  const pre = block.querySelector('pre') || block;
  const text = pre.textContent || pre.innerText;
  navigator.clipboard.writeText(text.trim()).then(() => {
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(() => { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 2000);
  });
}
$$('.copy-btn').forEach(btn => {
  if (!btn.dataset.bound) {
    btn.dataset.bound = '1';
    btn.addEventListener('click', () => copyCode(btn));
  }
});

// ========= EVALUATE PAGE ==========================================

const evaluateForm = $('#evaluateForm');
if (evaluateForm) {

  // ── State ────────────────────────────────────────────────────
  let currentMode = 'passage';
  let lastResult  = null;

  // ── Mode toggle ──────────────────────────────────────────────
  $$('.mode-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      $$('.mode-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentMode = btn.dataset.mode;
    });
  });

  // ── Sample answers ───────────────────────────────────────────
  const SAMPLES = {
    strong: `Breadth-First Search (BFS) is a graph traversal algorithm that explores all nodes at the current depth level before moving to the next level. It systematically visits every reachable node from the starting node.

BFS uses a queue data structure (FIFO – First In, First Out) to keep track of nodes to be visited. When a node is dequeued, all its unvisited neighbours are enqueued. This FIFO property ensures that nodes are visited in the order they were discovered, which directly implements the level-by-level exploration.

The time complexity of BFS is O(V + E), where V is the number of vertices and E is the number of edges. Every vertex is enqueued and dequeued exactly once, and every edge is examined at most twice (once from each endpoint in undirected graphs). The space complexity is also O(V), because in the worst case the queue holds all vertices at the widest level of the graph.

BFS guarantees the shortest path in unweighted graphs because it explores nodes level by level; the first time it reaches the destination is via the shortest route. In contrast, Depth-First Search (DFS) uses a stack and dives deep before backtracking, so it is better suited for tasks like topological sorting or cycle detection. BFS is preferred when the solution is near the root or when we need the shortest path, while DFS uses less memory on sparse graphs.`,

    partial: `BFS stands for Breadth-First Search. It starts from a source node and visits all neighbours before going deeper. A queue is used to store nodes that need to be explored next.

The time complexity is O(V + E) where V is vertices and E is edges. BFS explores nodes level by level, making it useful for finding the shortest path in graphs without weights.

Unlike DFS which uses a stack, BFS uses a queue. BFS is better when you want the shortest path.`,

    weak: `BFS is a searching technique. It looks at nodes one by one. It uses some kind of data structure to remember which nodes to visit. The time taken depends on the graph size. DFS is another method that works differently.`
  };

  $$('.btn-sample').forEach(btn => {
    btn.addEventListener('click', () => {
      const key = btn.dataset.sample;
      if (SAMPLES[key]) {
        $('#answerText').value = SAMPLES[key];
        $('#answerText').dispatchEvent(new Event('input'));
      }
    });
  });

  // ── Drag-and-drop upload ─────────────────────────────────────
  const dropZone = $('#dropZone');
  const fileInput = $('#fileInput');
  if (dropZone && fileInput) {
    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
    dropZone.addEventListener('drop', e => {
      e.preventDefault(); dropZone.classList.remove('drag-over');
      const file = e.dataTransfer.files[0];
      if (file) handleFileUpload(file);
    });
    fileInput.addEventListener('change', () => {
      if (fileInput.files[0]) handleFileUpload(fileInput.files[0]);
    });
  }

  async function handleFileUpload(file) {
    const MAX = 8 * 1024 * 1024;
    if (file.size > MAX) { showToast('File exceeds 8 MB limit.', 'error'); return; }
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['txt','pdf','docx'].includes(ext)) {
      showToast(`Unsupported type .${ext}. Use .txt, .pdf, or .docx.`, 'error'); return;
    }
    dropZone.querySelector('p').textContent = `Uploading ${file.name}…`;
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await fetch('/api/evaluate/upload', { method: 'POST', body: fd });
      const json = await res.json();
      if (json.error) { showToast(json.error, 'error'); return; }
      $('#answerText').value = json.text;
      dropZone.querySelector('p').innerHTML = `<strong>${file.name}</strong> loaded ✓`;
    } catch (err) {
      showToast('Upload failed. Please try again.', 'error');
      dropZone.querySelector('p').textContent = 'Drag & drop or click to select';
    }
  }

  // ── Form submit ──────────────────────────────────────────────
  evaluateForm.addEventListener('submit', async e => {
    e.preventDefault();
    const submitBtn = $('#submitBtn');
    const spinner   = submitBtn.querySelector('.spinner');
    const btnText   = submitBtn.querySelector('.btn-text');

    submitBtn.disabled = true;
    if (spinner) spinner.style.display = 'inline-block';
    if (btnText) btnText.textContent = 'Evaluating…';

    const rubricRaw = $('#rubricText').value.trim();
    const payload = {
      label:     $('#labelInput').value.trim(),
      question:  $('#questionInput').value.trim(),
      answer:    $('#answerText').value.trim(),
      max_marks: parseFloat($('#maxMarks').value) || 10,
      rubric:    rubricRaw,
      mode:      currentMode,
    };

    try {
      const res  = await fetch('/api/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.error) {
        showError(data.error);
      } else {
        lastResult = data;
        renderResults(data, payload);
      }
    } catch (err) {
      showError('Could not reach the server. Please check the app is running.');
    } finally {
      submitBtn.disabled = false;
      if (spinner) spinner.style.display = 'none';
      if (btnText) btnText.textContent = 'Evaluate';
    }
  });

  function showError(msg) {
    const panel = $('#resultsPanel');
    panel.classList.add('show');
    panel.innerHTML = `
      <div class="notice notice-err" role="alert">
        <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <span>${escHtml(msg)}</span>
      </div>`;
  }

  // ── Render results ───────────────────────────────────────────
  function renderResults(data, payload) {
    const panel = $('#resultsPanel');
    panel.classList.add('show');

    const pct = Math.round(data.overall_R * 100);
    const circumference = 251.2;
    const offset = circumference - (pct / 100) * circumference;

    let html = `
      <!-- Score ring -->
      <div class="score-ring-wrap reveal visible">
        <svg class="score-ring-svg" width="90" height="90" viewBox="0 0 90 90" aria-label="Score ${pct}%" role="img">
          <circle class="score-ring-circle" cx="45" cy="45" r="40"/>
          <circle class="score-ring-arc" id="scoreArc" cx="45" cy="45" r="40"
            style="stroke-dashoffset:${offset}"/>
          <text class="score-ring-text" x="45" y="50" text-anchor="middle">${pct}%</text>
        </svg>
        <div class="score-info">
          <h3>Provisional Score</h3>
          <div class="big-score mono">${data.total_marks_suggested} / ${data.total_marks_available}</div>
          <div class="score-label">Across ${data.criteria.length} criteria</div>
        </div>
      </div>

      <!-- Notice -->
      <div class="notice" role="note" style="margin-bottom:20px">
        <svg viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        <span><strong>Provisional only.</strong> A teacher must review and approve these marks before they are used.</span>
      </div>

      <!-- Criterion table -->
      <div class="card" style="margin-bottom:20px;padding:0;overflow:hidden;">
        <div class="criterion-table-wrap">
          <table class="criterion-table" aria-label="Criterion scores">
            <thead>
              <tr>
                <th>Criterion</th>
                <th title="TF-IDF cosine similarity">S</th>
                <th title="Keyword coverage">K</th>
                <th title="Combined ratio: 0.65·S + 0.35·K">R</th>
                <th>Band</th>
                <th>Suggested</th>
                <th>Final Mark</th>
                <th>Evidence</th>
              </tr>
            </thead>
            <tbody id="criterionTbody">
    `;

    data.criteria.forEach((cr, idx) => {
      const bandClass = cr.band.includes('Strong') ? 'band-strong'
                      : cr.band.includes('Partial') ? 'band-partial' : 'band-limited';
      html += `
        <tr>
          <td>${escHtml(cr.criterion)}</td>
          <td class="val-s">${cr.S.toFixed(3)}</td>
          <td class="val-k">${cr.K.toFixed(3)}</td>
          <td class="val-r">${cr.R.toFixed(3)}</td>
          <td><span class="band-chip ${bandClass}">${escHtml(cr.band)}</span></td>
          <td class="mono">${cr.marks_suggested}</td>
          <td>
            <input type="number" class="final-mark-input" id="finalMark${idx}"
              value="${cr.marks_suggested}" min="0" max="${cr.marks_available}"
              step="0.5" aria-label="Final mark for criterion ${idx+1}">
          </td>
          <td>
            <button class="expand-btn" data-idx="${idx}" aria-expanded="false"
              aria-controls="evidence${idx}">
              View
              <svg viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"/></svg>
            </button>
          </td>
        </tr>
        <tr class="evidence-row">
          <td colspan="8">
            <div class="evidence-inner" id="evidence${idx}">
              ${renderEvidence(cr)}
            </div>
          </td>
        </tr>
      `;
    });

    html += `
            </tbody>
          </table>
        </div>
      </div>

      <!-- Review panel -->
      <div class="review-panel">
        <h3>Teacher Review</h3>
        <textarea class="review-textarea" id="teacherComment" rows="3"
          placeholder="Add a comment for the student…" aria-label="Teacher comment"></textarea>
        <div class="review-actions">
          <button class="btn-approve" id="btnApprove" type="button">✓ Approve marks</button>
          <button class="btn-return" id="btnReturn" type="button">↩ Return for re-marking</button>
          <button class="btn-copy" id="btnCopy" type="button">⎘ Copy feedback</button>
        </div>
      </div>
    `;

    panel.innerHTML = html;

    // Evidence accordion
    $$('.expand-btn', panel).forEach(btn => {
      btn.addEventListener('click', () => {
        const idx  = btn.dataset.idx;
        const box  = $(`#evidence${idx}`, panel);
        const open = box.classList.toggle('show');
        btn.classList.toggle('open', open);
        btn.setAttribute('aria-expanded', String(open));
        btn.querySelector('.btn-text') && (btn.querySelector('.btn-text').textContent = open ? 'Hide' : 'View');
      });
    });

    // Approve
    $('#btnApprove', panel).addEventListener('click', () => {
      const totFinal = data.criteria.reduce((s, _, i) => {
        const v = parseFloat($(`#finalMark${i}`, panel)?.value || 0);
        return s + (isNaN(v) ? 0 : v);
      }, 0);
      showToast(`Marks approved: ${round2(totFinal)} / ${data.total_marks_available}`, 'success');
    });

    // Return
    $('#btnReturn', panel).addEventListener('click', () => {
      showToast('Submission flagged for re-marking.', 'info');
    });

    // Copy feedback
    $('#btnCopy', panel).addEventListener('click', () => {
      const comment = $('#teacherComment', panel).value.trim();
      const lines = data.criteria.map((cr, i) => {
        const fm = parseFloat($(`#finalMark${i}`, panel)?.value || cr.marks_suggested);
        return `• ${cr.criterion}\n  Score: ${fm} / ${cr.marks_available}  |  ${cr.band}\n  ${cr.feedback}`;
      });
      const text = [
        `EvalAssist AI – Provisional Feedback`,
        `Total: ${round2(data.total_marks_suggested)} / ${data.total_marks_available}`,
        '',
        ...lines,
        comment ? `\nTeacher comment: ${comment}` : '',
        '\n[Provisional only – approved by teacher]'
      ].join('\n');
      navigator.clipboard.writeText(text).then(() => showToast('Feedback copied!', 'success'));
    });

    // Update history table
    renderHistory();

    // Animate ring
    setTimeout(() => {
      const arc = document.getElementById('scoreArc');
      if (arc) arc.style.strokeDashoffset = offset;
    }, 100);

    panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function renderEvidence(cr) {
    const matched = cr.matched_words.map(w =>
      `<span class="chip chip-match">${escHtml(w)}</span>`).join('');
    const missing = cr.missing_words.map(w =>
      `<span class="chip chip-miss">${escHtml(w)}</span>`).join('');

    const sentHtml = cr.matched_sentence
      ? `<div class="evidence-sentence">"${escHtml(cr.matched_sentence)}"</div>`
      : '';

    const formulaHtml = `
      <div class="formula-box">
        R = min(1, 0.65 × ${cr.S.toFixed(3)} + 0.35 × ${cr.K.toFixed(3)}) = ${cr.R.toFixed(3)}<br>
        marks = (${cr.marks_available} / n) × ${cr.R.toFixed(3)} = <strong>${cr.marks_suggested}</strong>
      </div>`;

    return `
      <p style="font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#6b7280;margin-bottom:8px;">Matched words</p>
      <div class="chip-group">${matched || '<span style="font-size:12px;color:#9ca3af">None matched</span>'}</div>
      <p style="font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#6b7280;margin:10px 0 8px;">Missing concepts</p>
      <div class="chip-group">${missing || '<span style="font-size:12px;color:#9ca3af">None missing</span>'}</div>
      ${sentHtml}
      <p style="font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#6b7280;margin:10px 0 8px;">Formula (with real values)</p>
      ${formulaHtml}
      <p style="font-size:12px;color:#6b7280;margin-top:8px;">${escHtml(cr.feedback)}</p>
    `;
  }

  function renderHistory() {
    fetch('/api/evaluate', { method: 'OPTIONS' }).catch(() => {});
    // Re-fetch via GET is not supported; history is already in template on page load.
    // After an evaluation, we rely on the server-side rendered table being updated on
    // next page load. A lightweight approach: just reload the history section via the
    // existing data passed from server context on page load (updated in memory).
  }

} // end evaluate page

// ── FAQ accordion ──────────────────────────────────────────────────
$$('.faq-question').forEach(btn => {
  btn.addEventListener('click', () => {
    const answer  = btn.nextElementSibling;
    const isOpen  = answer.classList.contains('show');
    // Close all
    $$('.faq-answer.show').forEach(a => a.classList.remove('show'));
    $$('.faq-question.open').forEach(b => b.classList.remove('open'));
    if (!isOpen) {
      answer.classList.add('show');
      btn.classList.add('open');
    }
  });
});

// ── "See how it works" smooth scroll ───────────────────────────────
const seeHow = $('#seeHowBtn');
if (seeHow) {
  seeHow.addEventListener('click', e => {
    e.preventDefault();
    const target = $('#howItWorksSection');
    if (target) target.scrollIntoView({ behavior: 'smooth' });
  });
}

// ── HTML escape ────────────────────────────────────────────────────
function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

// =====================================================================
// AI ENGINE page
// =====================================================================

// ── Rule engine sliders ────────────────────────────────────────────
const completenessSlider = $('#completenessSlider');
const correctnessSlider  = $('#correctnessSlider');
if (completenessSlider && correctnessSlider) {

  async function runRules() {
    const c = parseFloat(completenessSlider.value);
    const k = parseFloat(correctnessSlider.value);
    $('#completenessVal').textContent = c.toFixed(2);
    $('#correctnessVal').textContent  = k.toFixed(2);

    const res  = await fetch('/api/rules', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ completeness: c, correctness: k })
    });
    const data = await res.json();

    const box = $('#ruleTrace');
    box.innerHTML = data.trace.map(line => {
      const cls = line.includes('FIRED') ? 'trace-fired'
                : line.includes('Conclusion') ? 'trace-conclusion' : '';
      return `<span class="trace-line ${cls}">${escHtml(line)}</span>`;
    }).join('\n');

    $('#ruleFired').textContent = data.fired_rule;
    $('#ruleConclusion').textContent = data.conclusion;
  }

  completenessSlider.addEventListener('input', runRules);
  correctnessSlider.addEventListener('input', runRules);
  runRules();
}

// ── Search demo ────────────────────────────────────────────────────
let searchSteps = [];
let searchStepIdx = 0;
let searchResult = null;

const searchAlgoSelect = $('#searchAlgoSelect');
if (searchAlgoSelect) {

  async function runSearch() {
    const algo = searchAlgoSelect.value;
    const res = await fetch('/api/search', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ algorithm: algo })
    });
    searchResult = await res.json();
    searchSteps = searchResult.steps || [];
    searchStepIdx = 0;
    renderSearchStep(-1); // reset
    $('#searchLog').textContent = `Algorithm: ${searchResult.algorithm}. Press Step or Run.`;
  }

  function renderSearchStep(upToIdx) {
    const nodes = ['S0','S1','S2','S3','S4','S5','S6'];
    const path  = searchResult?.path || [];
    const visited = upToIdx < 0 ? [] : (searchSteps[upToIdx]?.visited || []);

    const viz = $('#searchViz');
    viz.innerHTML = nodes.map(n => {
      let cls = '';
      if (n === 'S0') cls = 'start';
      else if (n === 'S6') cls = path.includes(n) && upToIdx >= searchSteps.length - 1 ? 'path goal' : 'goal';
      if (path.includes(n) && upToIdx >= searchSteps.length - 1 && n !== 'S0') cls = 'path';
      if (visited.includes(n) && !cls.includes('path')) cls = 'visited';
      if (upToIdx >= 0 && searchSteps[upToIdx]?.expand === n) cls = 'current';

      return `<div class="search-node ${cls}" title="${n}">${n}</div>`;
    }).join('');
  }

  $('#btnSearchStep').addEventListener('click', () => {
    if (!searchResult) { runSearch(); return; }
    if (searchStepIdx < searchSteps.length) {
      renderSearchStep(searchStepIdx);
      const s = searchSteps[searchStepIdx];
      $('#searchLog').textContent += `\nStep ${searchStepIdx + 1}: expand ${s.expand}`;
      searchStepIdx++;
    } else {
      const found = searchResult.found;
      $('#searchLog').textContent += found
        ? `\n✓ Goal found. Path: ${searchResult.path.join(' → ')}`
        : '\n✗ Goal not found.';
    }
  });

  $('#btnSearchRun').addEventListener('click', async () => {
    await runSearch();
    for (let i = 0; i < searchSteps.length; i++) {
      renderSearchStep(i);
      await sleep(300);
    }
    renderSearchStep(searchSteps.length - 1);
    const log = $('#searchLog');
    log.textContent = searchResult.found
      ? `${searchResult.algorithm}: Found. Path: ${searchResult.path.join(' → ')}. Nodes expanded: ${searchResult.visited.length}.`
      : `${searchResult.algorithm}: Goal not found. Nodes expanded: ${searchResult.visited.length}.`;
  });

  $('#btnSearchReset').addEventListener('click', () => {
    searchResult = null; searchStepIdx = 0;
    renderSearchStep(-1);
    $('#searchLog').textContent = 'Select an algorithm and press Step or Run.';
  });

  searchAlgoSelect.addEventListener('change', runSearch);
  runSearch();
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

// ── Minimax ────────────────────────────────────────────────────────
const minimaxForm = $('#minimaxForm');
if (minimaxForm) {

  async function runMinimax() {
    const leavesRaw = $('#minimaxLeaves').value.trim();
    const ab        = $('#minimaxAB').checked;
    let leaves;
    try {
      leaves = leavesRaw.split(/[\s,]+/).map(Number);
      if (leaves.some(isNaN)) throw new Error();
    } catch {
      showToast('Enter 2, 4, or 8 comma-separated numbers.', 'error'); return;
    }
    const res = await fetch('/api/minimax', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ leaves, alpha_beta: ab })
    });
    const data = await res.json();
    if (data.error) { showToast(data.error, 'error'); return; }
    renderMinimax(data);
  }

  function renderMinimax(data) {
    const n = data.leaves.length; // 4 leaves → depth 2
    const depth = Math.log2(n);
    const pruned = new Set(data.pruned);
    const trace  = data.trace;

    // Build a simple visual representation
    const container = $('#minimaxViz');
    container.innerHTML = '';

    // Root row
    const rootVal = data.root_value;
    container.innerHTML = `
      <div class="minimax-row">
        <div class="minimax-node max-node" title="MAX root">
          ${rootVal}
        </div>
      </div>
      <div style="font-size:11px;color:#9ca3af;text-align:center;margin:-10px 0 4px">MAX</div>
    `;

    if (depth >= 2) {
      // Internal nodes (MIN)
      const minRow = document.createElement('div');
      minRow.className = 'minimax-row';
      const nInternal = n / 2;
      for (let i = 0; i < nInternal; i++) {
        const t = trace.find(x => x.node === `root${i === 0 ? 'L' : 'R'}` && x.type === 'min');
        const val = t ? t.value : '?';
        const d   = document.createElement('div');
        d.className = `minimax-node min-node${pruned.has(`root${i===0?'L':'R'}`) ? ' pruned' : ''}`;
        d.title = `MIN node (${i===0?'L':'R'})`;
        d.textContent = val;
        minRow.appendChild(d);
      }
      container.appendChild(minRow);
      const minLabel = document.createElement('div');
      minLabel.style.cssText = 'font-size:11px;color:#9ca3af;text-align:center;margin:-10px 0 4px';
      minLabel.textContent = 'MIN';
      container.appendChild(minLabel);

      // Leaf row
      const leafRow = document.createElement('div');
      leafRow.className = 'minimax-row';
      data.leaves.forEach((v, i) => {
        const lkeys = ['rootLL','rootLR','rootRL','rootRR'];
        const d = document.createElement('div');
        d.className = `minimax-node leaf${pruned.has(lkeys[i]) ? ' pruned' : ''}`;
        d.title = `Leaf ${v}${pruned.has(lkeys[i]) ? ' (pruned)' : ''}`;
        d.textContent = pruned.has(lkeys[i]) ? '✗' : v;
        leafRow.appendChild(d);
      });
      container.appendChild(leafRow);
      const leafLabel = document.createElement('div');
      leafLabel.style.cssText = 'font-size:11px;color:#9ca3af;text-align:center;margin:-10px 0 4px';
      leafLabel.textContent = 'Leaves';
      container.appendChild(leafLabel);
    }

    $('#minimaxResult').textContent = `Root value = ${data.root_value}${data.alpha_beta ? ' (with α-β pruning)' : ''}. Pruned: ${data.pruned.length} nodes.`;
  }

  minimaxForm.addEventListener('submit', e => { e.preventDefault(); runMinimax(); });
  runMinimax();
}

// ── Bayesian updater ───────────────────────────────────────────────
const bayesForm = $('#bayesForm');
if (bayesForm) {
  bayesForm.addEventListener('input', async () => {
    const prior = parseFloat($('#bayesPrior').value);
    const like  = parseFloat($('#bayesLike').value);
    const fp    = parseFloat($('#bayesFP').value);
    const res   = await fetch('/api/bayes', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ prior, likelihood: like, false_positive: fp })
    });
    const data = await res.json();
    $('#bayesResult').textContent = `Posterior P(H|E) = ${data.posterior}`;
    $('#bayesFormula').textContent = data.formula;
  });
}

// ── Fuzzy chart ────────────────────────────────────────────────────
const fuzzySlider = $('#fuzzySlider');
if (fuzzySlider) {
  fuzzySlider.addEventListener('input', async () => {
    const score = parseFloat(fuzzySlider.value);
    $('#fuzzyVal').textContent = score.toFixed(2);
    const res  = await fetch('/api/fuzzy', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ score })
    });
    const data = await res.json();
    $('#fuzzyLow').textContent    = data.low.toFixed(3);
    $('#fuzzyMedium').textContent = data.medium.toFixed(3);
    $('#fuzzyHigh').textContent   = data.high.toFixed(3);
    drawFuzzyChart(score, data);
  });
  fuzzySlider.dispatchEvent(new Event('input'));
}

function drawFuzzyChart(score, data) {
  const canvas = $('#fuzzyCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.offsetWidth || 300;
  const H = canvas.offsetHeight || 120;
  canvas.width = W; canvas.height = H;
  ctx.clearRect(0, 0, W, H);

  function tri(x, a, b, c) {
    if (x <= a || x >= c) return 0;
    if (x <= b) return (x - a) / (b - a);
    return (c - x) / (c - b);
  }

  const colors = ['#3b82f6','#f59e0b','#10b981'];
  const tris   = [[-0.1, 0, 0.5], [0.2, 0.5, 0.8], [0.5, 1, 1.1]];
  const labels = ['Low','Medium','High'];

  tris.forEach(([a, b, c], i) => {
    ctx.beginPath();
    ctx.moveTo(0, H);
    for (let px = 0; px <= W; px++) {
      const x = px / W;
      const y = tri(x, a, b, c);
      ctx.lineTo(px, H - y * (H - 8));
    }
    ctx.strokeStyle = colors[i];
    ctx.lineWidth = 2;
    ctx.stroke();
  });

  // Score line
  ctx.beginPath();
  ctx.moveTo(score * W, 0);
  ctx.lineTo(score * W, H);
  ctx.strokeStyle = '#A12C2F';
  ctx.lineWidth = 2;
  ctx.setLineDash([4, 3]);
  ctx.stroke();
  ctx.setLineDash([]);
}

// ── Dempster-Shafer ────────────────────────────────────────────────
const dempsterForm = $('#dempsterForm');
if (dempsterForm) {
  dempsterForm.addEventListener('input', async () => {
    const m1 = parseFloat($('#dsM1').value);
    const m2 = parseFloat($('#dsM2').value);
    const res = await fetch('/api/dempster', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ m1, m2 })
    });
    const data = await res.json();
    $('#dsResult').textContent = `Combined m(A) = ${data.combined_A}  |  Belief = ${data.belief}  |  Plausibility = ${data.plausibility}`;
  });
}

// ── Status page ────────────────────────────────────────────────────
const runTestsBtn = $('#runTestsBtn');
if (runTestsBtn) {
  runTestsBtn.addEventListener('click', async () => {
    runTestsBtn.disabled = true;
    runTestsBtn.textContent = 'Running…';
    const container = $('#testResults');
    container.innerHTML = '<p style="color:#6b7280;font-size:13px;">Running self-check…</p>';

    try {
      const res  = await fetch('/api/selftest');
      const data = await res.json();

      let html = '';
      data.checks.forEach(c => {
        const cls = c.status === 'pass' ? 'pass' : 'fail';
        html += `
          <div class="status-check-row">
            <div class="status-dot ${cls}"></div>
            <div class="status-check-name">${escHtml(c.name)}</div>
            <div class="status-check-ms mono">${c.ms}ms</div>
            <span class="status-check-badge ${cls}">${c.status.toUpperCase()}</span>
            ${c.error ? `<span style="font-size:12px;color:#dc2626;margin-left:8px">${escHtml(c.error)}</span>` : ''}
          </div>`;
      });

      const allPass = data.all_pass;
      container.innerHTML = `
        <div class="notice ${allPass ? '' : 'notice-err'}" style="margin-bottom:16px">
          <svg viewBox="0 0 24 24">
            ${allPass
              ? '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>'
              : '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>'}
          </svg>
          <strong>${allPass ? 'All checks passed.' : 'Some checks failed – see details below.'}</strong>
        </div>
        ${html}`;
    } catch (err) {
      container.innerHTML = `<div class="notice notice-err"><span>Could not reach the server.</span></div>`;
    } finally {
      runTestsBtn.disabled = false;
      runTestsBtn.textContent = 'Run self-check';
    }
  });
}
