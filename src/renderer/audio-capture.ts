let stream: MediaStream | null = null;
let recorder: MediaRecorder | null = null;
let chunks: Blob[] = [];
let timer: number | undefined;
let desired = false;
let ending: Promise<void> | null = null;

function stopTracks() {
  if (timer) window.clearTimeout(timer);
  timer = undefined;
  stream?.getTracks().forEach(track => track.stop());
  stream = null;
}

export async function beginRecording(onLimit: () => void) {
  if (ending || desired || recorder) return;
  desired = true;
  chunks = [];
  try {
    const selected = localStorage.getItem('myassist-mic') ?? '';
    stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        ...(selected ? { deviceId: { exact: selected } } : {}),
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    if (!desired) { stopTracks(); return; }
    recorder = new MediaRecorder(stream);
    recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
    recorder.start(500);
    timer = window.setTimeout(() => { onLimit(); void endRecording(true); }, 90000);
  } catch (error) {
    stopTracks();
    desired = false;
    throw error;
  }
}

export function endRecording(cancelled = false): Promise<void> {
  if (ending) return ending;
  desired = false;
  const active = recorder;
  recorder = null;
  if (!active) { stopTracks(); chunks = []; return Promise.resolve(); }

  ending = (async () => {
    if (active.state !== 'inactive') {
      const stopped = new Promise<void>(resolve => active.addEventListener('stop', () => resolve(), { once: true }));
      active.stop();
      await stopped;
    }
    stopTracks();
    if (cancelled) { chunks = []; return; }
    const blob = new Blob(chunks, { type: active.mimeType || 'audio/webm' });
    chunks = [];
    if (!blob.size) return;
    const buffer = await blob.arrayBuffer();
    const result = await window.myAssist.sendRecording(new Uint8Array(buffer));
    if (!result?.ok) void window.myAssist.showError(result?.error ?? 'Transcription did not complete.');
  })().finally(() => { ending = null; });
  return ending;
}
