/* One owned GLB preview. Late callbacks cannot revive a released instance. */
const SmelterModels = (() => {
  let active = null, library = null, epoch = 0;
  function clear() {
    epoch++;
    const entry = active;
    active = null;
    if (!entry) return;
    entry.controller.abort();
    entry.recording?.abort();
    entry.dispose?.();
    entry.animations.disable();
    entry.viewer?.pause();
    entry.viewer?.remove();
    if (entry.url) URL.revokeObjectURL(entry.url);
    entry.button.disabled = false;
    entry.capture.disabled = entry.spin.disabled = entry.video.disabled = true;
    entry.cancel.hidden = true;
    entry.cancel.disabled = false;
    entry.status.textContent = 'Preview released. Load again to inspect.';
  }
  function mount(asset, parent) {
    const make = (tag, text) => { const node = document.createElement(tag); if (text) node.textContent = text; return node; };
    const card = make('section'); card.className = 'model-card';
    const title = make('h3', asset.filename);
    const metadata = make('p', (asset.bytes / 1048576).toFixed(2) + ' MiB · ' + asset.meshes + ' meshes · ' + asset.materials + ' materials · ' + asset.images + ' embedded images');
    const evidence = make('details'), summary = make('summary', 'Attachment metadata');
    evidence.append(summary, make('pre', JSON.stringify(asset, null, 2)));
    const status = make('p', 'Local browser preview · orbit and zoom · no AI inference'); status.setAttribute('role', 'status');
    const stage = make('div'); stage.className = 'model-stage';
    const animations = SmelterAnimations.mount(asset);
    const load = make('button', 'Load 3D preview'), capture = make('button', 'Save PNG');
    const spin = make('button', 'Auto-rotate'), video = make('button', 'Export turntable (WebM)');
    const cancel = make('button', 'Cancel export'), release = make('button', 'Release preview');
    capture.disabled = spin.disabled = video.disabled = true; cancel.hidden = true;
    const actions = make('div'); actions.className = 'model-actions'; actions.append(load, spin, capture, video, cancel, release);
    release.onclick = () => { if (active?.card === card) clear(); };
    load.onclick = async () => {
      clear();
      const entry = {card, button:load, capture, spin, video, cancel, status, animations, controller:new AbortController(), ready:false};
      active = entry;
      const generation = epoch;
      const owns = () => active === entry && generation === epoch && card.isConnected;
      load.disabled = true; status.textContent = 'Loading local viewer…';
      try {
        const result = await api('/api/models/status');
        if (!owns()) return;
        if (result.status !== 'installed') throw Error((result.error || 'Local viewer is missing') + '. Install with: npm install --prefix .smelter/tooling/model-viewer --save-exact --ignore-scripts @google/model-viewer@4.1.0');
        if (!library) library = import('/assets/model-viewer.min.js').catch(error => { library = null; throw error; });
        await library;
        if (!owns()) return;
        const response = await fetch('/api/models/' + encodeURIComponent(asset.id), {signal:entry.controller.signal, headers:{'X-Smelter-Token':SmelterAuth.token()}});
        if (!response.ok) throw Error('Could not read the saved model attachment');
        const blob = await response.blob();
        if (!owns()) return;
        const viewer = document.createElement('model-viewer');
        entry.viewer = viewer; entry.url = URL.createObjectURL(blob);
        viewer.setAttribute('camera-orbit', '45deg 65deg auto');
        viewer.setAttribute('camera-controls', ''); viewer.setAttribute('touch-action', 'pan-y');
        viewer.setAttribute('shadow-intensity', '1'); viewer.setAttribute('exposure', '1');
        viewer.setAttribute('interaction-prompt', 'none'); viewer.setAttribute('alt', asset.filename + ' 3D preview');
        const ready = () => {
          if (!owns() || entry.ready) return;
          entry.ready = true; animations.bind(viewer);
          capture.disabled = spin.disabled = false; video.disabled = !SmelterTurntable.supported();
          video.title = video.disabled ? 'WebM recording unavailable in this browser' : '72 frames · 960×600 · target six seconds; keep this tab visible';
          status.textContent = 'Ready · drag to orbit · scroll to zoom · PNG captures this view';
        };
        const failed = () => {
          if (!owns()) return;
          entry.ready = false; entry.recording?.abort(); animations.disable();
          status.textContent = 'The browser could not render this model. Check WebGL support or model compatibility.';
          capture.disabled = spin.disabled = video.disabled = true; load.disabled = false;
        };
        viewer.addEventListener('load', ready); viewer.addEventListener('error', failed);
        entry.dispose = () => { viewer.removeEventListener('load', ready); viewer.removeEventListener('error', failed); };
        stage.replaceChildren(viewer); spin.textContent = 'Auto-rotate'; viewer.src = entry.url;
        spin.onclick = () => { if (!owns() || !entry.ready || entry.recording) return; viewer.autoRotate = !viewer.autoRotate; spin.textContent = viewer.autoRotate ? 'Pause rotation' : 'Auto-rotate'; };
        video.onclick = async () => {
          if (!owns() || !entry.ready || entry.recording || entry.capturing) return;
          const recording = new AbortController(); entry.recording = recording;
          animations.setBusy(true); const wasPlaying = !viewer.paused; viewer.pause();
          video.disabled = capture.disabled = spin.disabled = true; cancel.hidden = false;
          cancel.onclick = () => { if (!owns()) return; recording.abort(); cancel.disabled = true; status.textContent = 'Cancelling video export…'; };
          try {
            const output = await SmelterTurntable.record(viewer, recording.signal, (percent, phase) => { if (owns()) status.textContent = phase + ': ' + percent + '% · keep this tab visible'; });
            if (!owns() || recording.signal.aborted || !entry.ready) return;
            download(output, asset.filename.replace(/\.glb$/i, '') + '-turntable.webm');
            status.textContent = 'Turntable WebM download requested. Viewing angle restored.';
          } catch (error) {
            if (owns()) status.textContent = error.name === 'AbortError' ? 'Turntable export cancelled; no video downloaded.' : 'Video export failed: ' + error.message;
          } finally {
            entry.recording = null;
            if (owns()) {
              cancel.hidden = true; cancel.disabled = false; animations.setBusy(false);
              if (entry.ready && wasPlaying) viewer.play();
              capture.disabled = spin.disabled = !entry.ready;
              video.disabled = !entry.ready || !SmelterTurntable.supported();
              spin.textContent = viewer.autoRotate ? 'Pause rotation' : 'Auto-rotate';
            }
          }
        };
        capture.onclick = async () => {
          if (!owns() || !entry.ready || entry.recording || entry.capturing) return;
          entry.capturing = true; capture.disabled = video.disabled = true;
          try {
            const output = await viewer.toBlob({mimeType:'image/png'});
            if (!owns() || !entry.ready) return;
            if (!output) throw Error('No PNG was produced');
            download(output, asset.filename.replace(/\.glb$/i, '') + '-preview.png');
            status.textContent = 'PNG download requested. Original GLB unchanged.';
          } catch (error) {
            if (owns()) status.textContent = 'PNG capture failed: ' + error.message;
          } finally {
            entry.capturing = false;
            if (owns()) { capture.disabled = !entry.ready; video.disabled = !entry.ready || !SmelterTurntable.supported(); }
          }
        };
      } catch (error) {
        if (!owns()) return;
        clear(); status.textContent = error.message;
      }
    };
    card.append(title, metadata, stage, actions, status, animations.element, evidence); parent.append(card);
  }
  function download(blob, filename) {
    const url = URL.createObjectURL(blob), link = document.createElement('a');
    link.href = url; link.download = filename; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return {mount, clear};
})();
