/* File code is text only. No HTML interpretation or synthetic typing. */
const SmelterFiles = (() => {
  const labels = {reading:'Reading', read:'Read only', proposed:'Proposed · not saved',
    writing:'Writing · awaiting result', saved:'Saved', error:'Failed · latest proposal not saved',
    stopped:'Stopped · latest proposal unconfirmed', unconfirmed:'Unconfirmed'};
  function mount(container, doc = document) {
    const heading = doc.createElement('h3'); heading.textContent = 'File activity';
    const note = doc.createElement('p'); note.className = 'file-activity-note';
    note.textContent = 'Original snapshots and tool-reported edits. Proposed code is not saved until the tool confirms it.';
    const grid = doc.createElement('div'); grid.className = 'file-activity-grid';
    container.className = 'file-activity'; container.setAttribute('aria-label', 'Files in this request');
    container.append(heading, note, grid);
    const cards = new Map();
    function make(file) {
      const card = doc.createElement('article'); card.className = 'file-work-card';
      const title = doc.createElement('h4');
      const badge = doc.createElement('span'); badge.className = 'file-work-status'; badge.setAttribute('role','status');
      const original = doc.createElement('details');
      const summary = doc.createElement('summary');
      const before = doc.createElement('pre'); before.className = 'file-original-code'; before.tabIndex = 0;
      original.append(summary, before);
      const label = doc.createElement('label'); label.className = 'file-code-label';
      const caption = doc.createElement('span');
      const code = doc.createElement('textarea'); code.readOnly = true; code.spellcheck = false; code.rows = 9;
      code.className = 'file-updated-code'; code.wrap = 'off'; label.append(caption, code);
      const error = doc.createElement('p'); error.className = 'file-work-error';
      const previous = doc.createElement('details');
      const previousLabel = doc.createElement('summary'); previousLabel.textContent = 'Last confirmed saved version';
      const previousCode = doc.createElement('pre'); previous.append(previousLabel, previousCode);
      card.append(title, badge, original, label, error, previous); grid.append(card);
      return {card,title,badge,summary,before,caption,code,error,previous,previousCode};
    }
    function update(files) {
      for (const file of Array.isArray(files) ? files.slice(0,12) : []) {
        if (!file || typeof file.id !== 'string') continue;
        if (!cards.has(file.id)) cards.set(file.id, make(file));
        const ui = cards.get(file.id);
        ui.title.textContent = (file.area === 'source' ? 'Source · ' : 'Workspace · ') + file.path;
        ui.badge.textContent = labels[file.status] || 'Unconfirmed';
        ui.card.dataset.state = file.status;
        ui.summary.textContent = 'Original file · click to expand' + (file.before_truncated ? ' · preview truncated' : '');
        ui.before.textContent = file.before == null ? 'Original content not available yet.' : file.before;
        const saved = file.status === 'saved';
        const value = saved ? file.after : file.draft;
        ui.caption.textContent = saved ? 'Updated file · saved' + (file.after_truncated ? ' · preview truncated' : '') :
          file.draft ? (file.kind==='code'?'Proposed code · not confirmed saved':'Proposed CSS replacement · not confirmed saved') : 'Updated code · waiting for an edit';
        const text = value == null ? '' : String(value);
        if (ui.code.value !== text) {
          const atEnd = ui.code.scrollHeight - ui.code.scrollTop - ui.code.clientHeight < 40;
          const top = ui.code.scrollTop;
          ui.code.value = text;
          ui.code.scrollTop = atEnd ? ui.code.scrollHeight : top;
        }
        ui.code.setAttribute('aria-label', ui.caption.textContent + ': ' + file.path);
        ui.code.placeholder = file.status === 'read' ? 'Read only; no edit proposed.' : 'Waiting for code from the model…';
        ui.error.textContent = file.error || ''; ui.error.hidden = !file.error;
        ui.previous.hidden = saved || file.after == null;
        ui.previousCode.textContent = file.after || '';
      }
      heading.textContent = 'File activity · ' + cards.size + (cards.size === 1 ? ' file' : ' files');
      container.hidden = cards.size === 0;
    }
    update([]);
    return {update};
  }
  return {mount};
})();
if (typeof module !== 'undefined') module.exports = SmelterFiles;
