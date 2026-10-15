import { app } from 'electron';
import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process';
import { join } from 'node:path';
import { randomUUID } from 'node:crypto';

export class Transcriber {
  private child: ChildProcessWithoutNullStreams | null = null;
  private starting: Promise<void> | null = null;
  private idleTimer: NodeJS.Timeout | undefined;
  private pending = new Map<string, (text: string, error?: string) => void>();

  private start(): Promise<void> {
    if (this.starting) return this.starting;
    const exe = join(process.resourcesPath, 'resources', 'worker', 'MyAssistSpeech.exe');
    const model = app.isPackaged ? join(process.resourcesPath, 'resources', 'models', 'base') : join(app.getAppPath(), 'resources', 'models', 'base');
    this.child = app.isPackaged
      ? spawn(exe, [model], { stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true })
      : spawn(join(app.getAppPath(), 'worker', '.venv', 'Scripts', 'python.exe'), [join(app.getAppPath(), 'worker', 'speech.py'), model], { stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true });

    this.starting = new Promise((resolve, reject) => {
      let pending = '';
      let settled = false;
      const timer = setTimeout(() => { if (!settled) { settled = true; reject(new Error('Local speech engine took too long to start.')); } }, 60000);
      this.child!.stdout.setEncoding('utf8');
      this.child!.stdout.on('data', (chunk: string) => {
        pending += chunk;
        const lines = pending.split(/\r?\n/);
        pending = lines.pop() ?? '';
        for (const line of lines) {
          try {
            const message = JSON.parse(line);
            if (message.type === 'ready' && !settled) { settled = true; clearTimeout(timer); resolve(); }
            if (message.type === 'transcript' || message.type === 'error') {
              const done = this.pending.get(message.id);
              if (done) { this.pending.delete(message.id); done(message.text ?? '', message.type === 'error' ? message.message : undefined); }
            }
          } catch { /* Ignore malformed worker output; never log audio or transcript data. */ }
        }
      });
      this.child!.stderr.on('data', (chunk: Buffer) => { const message = chunk.toString().trim().slice(0, 240); if (message) process.stderr.write(`MyAssist speech worker: ${message}\n`); });
      this.child!.once('error', error => { if (!settled) { settled = true; clearTimeout(timer); reject(error); } });
      this.child!.once('exit', code => {
        this.child = null;
        if (!settled) { settled = true; clearTimeout(timer); reject(new Error(`Local speech engine stopped during startup (${code ?? 'unknown'}).`)); }
        for (const done of this.pending.values()) done('', 'Local speech engine stopped.');
        this.pending.clear();
        this.starting = null;
      });
    });
    return this.starting;
  }

  async transcribe(bytes: Uint8Array): Promise<string> {
    if (this.idleTimer) { clearTimeout(this.idleTimer); this.idleTimer = undefined; }
    await this.start();
    return new Promise((resolve, reject) => {
      if (!this.child) { reject(new Error('Local speech engine is unavailable.')); return; }
      const id = randomUUID();
      this.pending.set(id, (text, error) => {
        if (error) reject(new Error(error)); else resolve(text);
        this.scheduleStop();
      });
      const audio = Buffer.from(bytes).toString('base64');
      this.child.stdin.write(JSON.stringify({ kind: 'transcribe', id, audio }) + '\n', error => {
        if (error) { this.pending.delete(id); reject(error); this.scheduleStop(); }
      });
    });
  }

  private scheduleStop() {
    if (this.idleTimer) clearTimeout(this.idleTimer);
    this.idleTimer = setTimeout(() => this.stop(), 90000);
  }

  stop() {
    if (this.idleTimer) { clearTimeout(this.idleTimer); this.idleTimer = undefined; }
    if (this.child) { this.child.stdin.write('{"kind":"shutdown"}\n'); this.child.kill(); this.child = null; }
    this.starting = null;
  }
}
