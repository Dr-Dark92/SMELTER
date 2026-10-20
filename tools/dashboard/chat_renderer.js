/* Small text-only Markdown renderer. Never interprets raw HTML or URLs. */
const SmelterChat = (() => {
  function parseBlocks(text) {
    const lines = String(text).replace(/\r\n/g, '\n').split('\n');
    const blocks = [];
    for (let i = 0; i < lines.length;) {
      const line = lines[i];
      const fence = line.match(/^ {0,3}(`{3,}|~{3,})(.*)$/);
      if (fence) {
        const marker = fence[1];
        const code = [];
        i++;
        while (i < lines.length && !new RegExp('^ {0,3}' + marker[0] + '{' + marker.length + ',}\\s*$').test(lines[i])) {
          code.push(lines[i++]);
        }
        if (i < lines.length) i++;
        blocks.push({type: 'code', language: fence[2].trim().split(/\s+/)[0].slice(0, 40), text: code.join('\n')});
        continue;
      }
      if (!line.trim()) { i++; continue; }
      const heading = line.match(/^(#{1,6})\s+(.+)$/);
      if (heading) { blocks.push({type: 'heading', level: Math.min(6, heading[1].length + 2), text: heading[2]}); i++; continue; }
      const item = line.match(/^\s*(?:([-+*])|\d+[.)])\s+(.+)$/);
      if (item) {
        const ordered = !item[1];
        let list = blocks[blocks.length - 1];
        if (!list || list.type !== 'list' || list.ordered !== ordered) {
          list = {type: 'list', ordered, items: []}; blocks.push(list);
        }
        list.items.push(item[2]); i++; continue;
      }
      if (/^>\s?/.test(line)) { blocks.push({type: 'quote', text: line.replace(/^>\s?/, '')}); i++; continue; }
      let paragraph = blocks[blocks.length - 1];
      if (!paragraph || paragraph.type !== 'paragraph' || i === 0 || !lines[i - 1].trim()) {
        paragraph = {type: 'paragraph', text: line}; blocks.push(paragraph);
      } else paragraph.text += '\n' + line;
      i++;
    }
    return blocks;
  }

  function inline(parent, text, doc) {
    const pattern = /(`[^`\n]+`|\*\*[^*\n]+\*\*)/g;
    let offset = 0;
    for (const match of text.matchAll(pattern)) {
      parent.append(doc.createTextNode(text.slice(offset, match.index)));
      const code = match[0][0] === '`';
      const span = doc.createElement(code ? 'code' : 'strong');
      span.textContent = match[0].slice(code ? 1 : 2, code ? -1 : -2);
      parent.append(span); offset = match.index + match[0].length;
    }
    parent.append(doc.createTextNode(text.slice(offset)));
  }

  function copyButton(text, label = 'Copy', doc = document) {
    const button = doc.createElement('button');
    button.type = 'button'; button.className = 'copy-button'; button.textContent = label;
    button.setAttribute('aria-label', label);
    button.onclick = async () => {
      try {
        await navigator.clipboard.writeText(text);
        button.textContent = 'Copied';
      } catch {
        button.textContent = 'Select text to copy';
        button.title = 'Clipboard access unavailable. Select the text and copy manually.';
      }
      setTimeout(() => { button.textContent = label; }, 2500);
    };
    return button;
  }

  function render(text, container, doc = document) {
    container.replaceChildren();
    container.classList.add('formatted-message');
    for (const block of parseBlocks(text)) {
      if (block.type === 'code') {
        const section = doc.createElement('section'); section.className = 'code-block';
        const bar = doc.createElement('div'); bar.className = 'code-toolbar';
        const language = doc.createElement('span'); language.textContent = block.language || 'Code';
        bar.append(language, copyButton(block.text, 'Copy code', doc));
        const pre = doc.createElement('pre'); const code = doc.createElement('code');
        code.textContent = block.text; pre.append(code); section.append(bar, pre); container.append(section);
      } else if (block.type === 'list') {
        const list = doc.createElement(block.ordered ? 'ol' : 'ul');
        for (const item of block.items) { const li = doc.createElement('li'); inline(li, item, doc); list.append(li); }
        container.append(list);
      } else {
        const tag = block.type === 'heading' ? 'h' + block.level : block.type === 'quote' ? 'blockquote' : 'p';
        const node = doc.createElement(tag); inline(node, block.text, doc); container.append(node);
      }
    }
  }
  return {parseBlocks, render, copyButton};
})();
if (typeof module !== 'undefined') module.exports = SmelterChat;
