/* Browser-only WebM export from public model-viewer camera/snapshot APIs. */
const SmelterTurntable = (() => {
  const mimeTypes = ['video/webm;codecs=vp8', 'video/webm;codecs=vp9', 'video/webm'];
  function supported() {
    return typeof MediaRecorder !== 'undefined' && typeof HTMLCanvasElement !== 'undefined' &&
      typeof HTMLCanvasElement.prototype.captureStream === 'function' &&
      mimeTypes.some(type => MediaRecorder.isTypeSupported(type));
  }
  function check(signal) {
    if (signal.aborted) throw new DOMException('Turntable export cancelled', 'AbortError');
    if (document.hidden) throw Error('Keep this browser tab visible during turntable export');
  }
  function rendered(signal) {
    return new Promise((resolve, reject) => {
      let timer;
      const clean = () => { clearTimeout(timer); signal.removeEventListener('abort', abort); document.removeEventListener('visibilitychange', visibility); };
      const fail = error => { clean(); reject(error); };
      const abort = () => fail(new DOMException('Turntable export cancelled', 'AbortError'));
      const visibility = () => { if (document.hidden) fail(Error('Keep this browser tab visible during turntable export')); };
      signal.addEventListener('abort', abort, {once: true});
      document.addEventListener('visibilitychange', visibility);
      timer = setTimeout(() => fail(Error('Browser rendering did not advance')), 5000);
      requestAnimationFrame(() => requestAnimationFrame(() => { clean(); resolve(); }));
    });
  }
  async function record(viewer, signal, progress) {
    if (!supported()) throw Error('This browser does not support WebM recording. PNG capture is still available.');
    check(signal);
    const original = {orbit: viewer.cameraOrbit, rotate: viewer.autoRotate, controls: viewer.cameraControls};
    const orbit = viewer.getCameraOrbit();
    original.orbit = orbit.theta + 'rad ' + orbit.phi + 'rad ' + orbit.radius + 'm';
    const canvas = document.createElement('canvas'); canvas.width = 960; canvas.height = 600;
    const context = canvas.getContext('2d');
    if (!context) throw Error('A 2D capture canvas is unavailable');
    const stream = canvas.captureStream(0);
    const track = stream.getVideoTracks()[0];
    if (!track || typeof track.requestFrame !== 'function') {
      stream.getTracks().forEach(x => x.stop());
      throw Error('Manual video frame capture is unavailable in this browser. Use PNG capture.');
    }
    const chunks = [];
    let recorder;
    try { recorder = new MediaRecorder(stream, {mimeType: mimeTypes.find(type => MediaRecorder.isTypeSupported(type)), videoBitsPerSecond: 2500000}); }
    catch (error) { stream.getTracks().forEach(x => x.stop()); throw error; }
    const finished = new Promise((resolve, reject) => {
      recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
      recorder.onerror = () => reject(Error('Browser video encoding failed'));
      recorder.onstop = () => resolve(new Blob(chunks, {type: recorder.mimeType}));
    });
    finished.catch(() => {});
    try {
      viewer.autoRotate = false; viewer.cameraControls = false;
      const frames = 72, fps = 12, snapshots = [];
      let snapshotBytes = 0;
      for (let frame = 0; frame < frames; frame++) {
        check(signal);
        viewer.cameraOrbit = (orbit.theta + 2 * Math.PI * frame / frames) + 'rad ' + orbit.phi + 'rad ' + orbit.radius + 'm';
        await viewer.updateComplete;
        viewer.jumpCameraToGoal();
        await viewer.updateComplete;
        await rendered(signal);
        check(signal);
        const snapshot = await viewer.toBlob({mimeType: 'image/png'});
        check(signal);
        snapshotBytes += snapshot.size;
        if (snapshotBytes > 128 * 1024 * 1024) throw Error('Turntable frame cache exceeded 128 MiB');
        snapshots.push(snapshot);
        progress(Math.round((frame + 1) / frames * 100), 'Rendering frames');
      }
      async function draw(snapshot) {
        check(signal);
        const image = await createImageBitmap(snapshot);
        try {
          context.fillStyle = '#26313e'; context.fillRect(0, 0, canvas.width, canvas.height);
          const scale = Math.min(canvas.width / image.width, canvas.height / image.height);
          const width = image.width * scale, height = image.height * scale;
          context.drawImage(image, (canvas.width - width) / 2, (canvas.height - height) / 2, width, height);
        } finally { image.close(); }
      }
      await draw(snapshots[0]);
      recorder.start();
      const start = performance.now();
      for (let frame = 0; frame < frames; frame++) {
        await draw(snapshots[frame]);
        snapshots[frame] = null;
        track.requestFrame();
        progress(Math.round((frame + 1) / frames * 100), 'Encoding video');
        const wait = (frame + 1) * 1000 / fps - (performance.now() - start);
        if (wait > 0) await new Promise(resolve => setTimeout(resolve, wait));
      }
      check(signal);
      // Leave the final requested frame time to reach the encoder.
      await new Promise(resolve => setTimeout(resolve, 100));
      recorder.stop();
      const blob = await finished;
      check(signal);
      if (!blob.size) throw Error('The browser produced an empty video');
      return blob;
    } finally {
      if (recorder.state !== 'inactive') recorder.stop();
      stream.getTracks().forEach(x => x.stop());
      if (viewer.isConnected) {
        viewer.cameraOrbit = original.orbit; viewer.autoRotate = original.rotate;
        viewer.cameraControls = original.controls; viewer.jumpCameraToGoal();
      }
    }
  }
  return {supported, record};
})();
