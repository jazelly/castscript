// Types and calls for the `castscript web` API (castscript/web.py).

export type Check =
  | { ok: true; voices: number; lines: number; kinds: string[] }
  | { ok: false; error: string; line: number | null };

export type ScriptEntry = { name: string; linked: boolean; target: string | null; missing: boolean };
export type Script = ScriptEntry & { text: string; check: Check };
export type Voice = ScriptEntry & { transcript: string };
export type Engine = { name: string; installed: boolean; kinds: string[] };
export type Settings = {
  envs: string;
  breeze_dir: string;
  breeze_checkpoint: string;
  language: string;
  locale: string;
  workspace: string;
};
export type RenderStatus = 'running' | 'done' | 'failed' | 'stopped' | 'interrupted';
export type Render = {
  id: number;
  script: string;
  engine: string;
  language: string;
  status: RenderStatus;
  created_at: number;
  finished_at: number | null;
  audio_seconds: number | null;
  files: { mp3?: string; srt?: string };
  progress: { done: number; total: number } | null;
  log?: string;
};
export type ImportResult = { scripts: string[]; voices: string[]; skipped: number };

export const LANGUAGES = ['zh', 'en', 'ja', 'ko', 'fr', 'de', 'es', 'it', 'pt', 'ru', 'nl'] as const;

export async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error ?? res.statusText);
  return data as T;
}

export const enc = encodeURIComponent;
