/* Local GLB preview. No model bytes are sent to Qwen or an external service. */
const SmelterModels = (() => {
  let active = null;
  let library = null;
  let epoch = 0;
  function clear() {
    epoch++;
    if (!active) return;
    active.viewer.remove(); URL.revokeObjectURL(active.url);
    active.button.disabled = false; active.capture.disabled = true;
    active.spin.disabled = true; active.status.textContent = 'Preview released. Load again to inspect.';
    active = null;
  }
  function mount(asset, parent) {
    const card = document.createElement('section'); card.className = 'model-card';
    const title = document.createElement('h3'); title.textContent = asset.filename;
    const metadata = document.createElement('p');
    metadata.textContent = (asset.bytes / 1048576).toFixed(2) + ' MiB · ' + asset.meshes + ' meshes · ' + asset.materials + ' materials · ' + asset.images + ' embedded images';
    const evidence = document.createElement('details'); const summary = document.createElement('summary'); summary.textContent = 'Attachment metadata';
    const raw = document.createElement('pre'); raw.textContent = JSON.stringify(asset, null, 2); evidence.append(summary, raw);
    const status = document.createElement('p'); status.setAttribute('role', 'status'); status.textContent = 'Local browser preview · orbit and zoom · no AI inference';
    const stage = document.createElement('div'); stage.className = 'model-stage';
    const load = document.createElement('button'); load.textContent = 'Load 3D preview';
    const capture = document.createElement('button'); capture.textContent = 'Save PNG'; capture.disabled = true;
    const spin = document.createElement('button'); spin.textContent = 'Auto-rotate'; spin.disabled = true;
    const release = document.createElement('button'); release.textContent = 'Release preview'; release.onclick = clear;
    load.onclick = async () => {
      clear(); load.disabled = true; status.textContent = 'Loading local viewer…';
      const generation = epoch;
      let url = null;
      try {
        const result = await api('/api/models/status');
        if (result.status !== 'installed') throw Error(result.error + '. Install with: npm install --prefix .smelter/tooling/model-viewer --save-exact --ignore-scripts @google/model-viewer@4.1.0');
        if (!library) library = import('/assets/model-viewer.min.js').catch(error => { library = null; throw error; });
        await library;
        if (generation !== epoch) throw Error('Preview load superseded by navigation or another preview');
        const response = await fetch('/api/models/' + encodeURIComponent(asset.id), {headers: {'X-Smelter-Token': token || ''}});
        if (!response.ok) throw Error('Could not read the saved model attachment');
        url = URL.createObjectURL(await response.blob());
        if (generation !== epoch) throw Error('Preview load superseded by navigation or another preview');
        const viewer = document.createElement('model-viewer');
        viewer.setAttribute('camera-orbit', '45deg 65deg auto'); viewer.setAttribute('camera-controls', ''); viewer.setAttribute('touch-action', 'pan-y');
        viewer.setAttribute('shadow-intensity', '1'); viewer.setAttribute('exposure', '1');
        viewer.setAttribute('interaction-prompt', 'none'); viewer.setAttribute('alt', asset.filename + ' 3D preview');
        viewer.style.cssText = 'width:100%;height:420px;background:#26313e';
        viewer.addEventListener('load', () => { capture.disabled = spin.disabled = false; status.textContent = 'Ready · drag to orbit · scroll to zoom · PNG captures this view'; });
        viewer.addEventListener('error', () => { status.textContent = 'The browser could not render this model. Check WebGL support or model compatibility.'; capture.disabled = spin.disabled = true; load.disabled = false; });
        stage.replaceChildren(viewer); active = {viewer, url, button: load, capture, spin, status};
        spin.textContent = 'Auto-rotate'; viewer.src = url;
        spin.onclick = () => { viewer.autoRotate = !viewer.autoRotate; spin.textContent = viewer.autoRotate ? 'Pause rotation' : 'Auto-rotate'; };
        capture.onclick = async () => {
          capture.disabled = true;
          try {
            const blob = await viewer.toBlob({mimeType: 'image/png'});
            if (!blob) throw Error('No PNG was produced');
            const imageUrl = URL.createObjectURL(blob); const link = document.createElement('a');
            link.href = imageUrl; link.download = asset.filename.replace(/\.glb$/i, '') + '-preview.png'; link.click();
            setTimeout(() => URL.revokeObjectURL(imageUrl), 1000);
            status.textContent = 'PNG download requested. Original GLB unchanged.';
          } catch (error) { status.textContent = 'PNG capture failed: ' + error.message; }
          finally { capture.disabled = false; }
        };
      } catch (error) {
        if (url) URL.revokeObjectURL(url);
        load.disabled = false; status.textContent = error.message;
      }
    };
    card.append(title, metadata, stage, load, spin, capture, release, status, evidence); parent.append(card);
  }
  return {mount, clear};
})();
