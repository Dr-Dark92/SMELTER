/* Clip playback uses source names; friendly labels belong to SMELTER metadata. */
const SmelterAnimations = (() => {
  function mount(asset) {
    const element = document.createElement('section'); element.className = 'animation-panel';
    const heading = document.createElement('h4'); heading.textContent = 'Character animations';
    const notice = document.createElement('p'); notice.setAttribute('role', 'status'); notice.textContent = 'Load the 3D preview to inspect embedded animation clips.';
    const select = document.createElement('select'); select.setAttribute('aria-label', 'Animation clip');
    const original = document.createElement('p');
    const play = document.createElement('button'); play.textContent = 'Play animation';
    const restart = document.createElement('button'); restart.textContent = 'Restart animation';
    const seek = document.createElement('input'); seek.type = 'range'; seek.min = '0'; seek.max = '1'; seek.step = '0.001'; seek.value = '0'; seek.setAttribute('aria-label', 'Animation position');
    const time = document.createElement('span');
    const label = document.createElement('input'); label.maxLength = 120; label.placeholder = 'For example: Walk forward'; label.setAttribute('aria-label', 'Animation label');
    const save = document.createElement('button'); save.textContent = 'Save animation name';
    const note = document.createElement('p'); note.textContent = 'Names are saved in SMELTER. The original GLB and embedded clip names remain unchanged.';
    element.append(heading, notice, select, original, play, restart, seek, time, label, save, note);
    // Task artifacts are previewed in place; their clip labels are not stored as chat attachment metadata.
    if (asset.labels_read_only) { label.hidden = save.hidden = true; note.textContent = 'Clip names shown as embedded in the GLB. Labels do not prove clip semantics.'; }
    let viewer = null, timer = null, names = [], busy = false, saving = false, generation = 0;
    const controls = [select, play, restart, seek, label, save];
    function usable() { return viewer && names.length && names.filter(n => n === names[select.selectedIndex]).length === 1; }
    function refresh() {
      controls.forEach(c => { c.disabled = busy || !viewer || !names.length; });
      play.disabled = restart.disabled = seek.disabled = busy || !usable();
      save.disabled = save.disabled || saving;
      if (!viewer || !names.length) return;
      play.textContent = viewer.paused ? 'Play animation' : 'Pause animation';
      const duration = Number.isFinite(viewer.duration) ? viewer.duration : 0;
      seek.max = String(duration || 1); seek.value = String(viewer.currentTime || 0);
      time.textContent = (viewer.currentTime || 0).toFixed(2) + ' / ' + duration.toFixed(2) + ' s';
    }
    function choose() {
      if (!viewer || !names.length) return;
      const index = select.selectedIndex;
      viewer.pause(); viewer.animationCrossfadeDuration = 0; viewer.animationName = names[index]; viewer.currentTime = 0;
      const source = asset.animation_clips?.[index]?.source_name;
      original.textContent = 'Clip ' + (index + 1) + ' of ' + names.length + ' · original name: ' + (source || names[index]);
      label.value = asset.animation_labels?.[String(index)] || '';
      notice.textContent = usable() ? 'Choose a clip, then play or scrub to identify it.' : 'Duplicate source names: separate playback is unavailable for this clip in the viewer.';
      refresh();
    }
    select.onchange = choose;
    play.onclick = () => { if (viewer.paused) viewer.play(); else viewer.pause(); refresh(); };
    restart.onclick = () => { viewer.currentTime = 0; viewer.play(); refresh(); };
    seek.oninput = () => { viewer.pause(); viewer.currentTime = Number(seek.value); refresh(); };
    save.onclick = async () => {
      if (!viewer || busy || saving || !names.length) return;
      const binding = generation;
      const index = select.selectedIndex, value = label.value.trim();
      if (!value) { notice.textContent = 'Enter an animation name first.'; return; }
      saving = true; refresh();
      try {
        const updated = await api('/api/models', 'POST', {action: 'rename_animation', id: asset.id, index, label: value});
        Object.assign(asset, updated);
        if (binding !== generation) return;
        select.options[index].textContent = (index + 1) + '. ' + updated.animation_labels[String(index)] + ' [' + names[index] + ']';
        notice.textContent = 'Animation name saved.';
      } catch (error) { if (binding === generation) notice.textContent = error.message; }
      finally { saving = false; refresh(); }
    };
    function disable() {
      generation++; clearInterval(timer); timer = null; viewer = null; names = []; busy = false; refresh();
    }
    function bind(target) {
      disable(); viewer = target; names = [...target.availableAnimations]; select.replaceChildren();
      names.forEach((name, i) => {
        const option = document.createElement('option'); option.value = String(i);
        const alias = asset.animation_labels?.[String(i)]; option.textContent = (i + 1) + '. ' + (alias ? alias + ' [' + name + ']' : name); select.append(option);
      });
      if (names.length) { select.selectedIndex = 0; choose(); timer = setInterval(refresh, 150); }
      else { original.textContent = ''; notice.textContent = 'This GLB contains no animation clips.'; refresh(); }
    }
    disable();
    return {element, bind, disable, setBusy(value) { busy = value; refresh(); }};
  }
  return {mount};
})();
