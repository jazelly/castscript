import {
  AlertTriangle,
  BookOpen,
  CircleCheck,
  CircleX,
  FileText,
  FolderInput,
  Link2,
  Mic,
  Play,
  Plus,
  Save,
  Search,
  Square,
  Trash2,
} from 'lucide-react';
import { DropdownMenu, Popover } from 'radix-ui';
import { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import {
  type Check,
  type Engine,
  LANGUAGES,
  type Render,
  type Script,
  type ScriptEntry,
  type Settings,
  type Voice,
  api,
  enc,
} from '../api';
import { Editor, type EditorHandle } from '../components/Editor';
import { ImportDialog, NewScriptDialog, StatusBadge, renderStats, timeAgo } from '../components/dialogs';
import { Badge, Button, Confirm, IconButton, Input, Select } from '../components/ui';
import { useI18n } from '../i18n';

type Props = {
  selected: string | null;
  onSelect: (name: string | null) => void;
  engines: Engine[];
  settings: Settings;
  onOpenSettings: () => void;
};

export function Studio({ selected, onSelect, engines, settings, onOpenSettings }: Props) {
  const { t } = useI18n();
  const [scripts, setScripts] = useState<ScriptEntry[]>([]);
  const [query, setQuery] = useState('');
  const [script, setScript] = useState<Script | null>(null);
  const [text, setText] = useState('');
  const [check, setCheck] = useState<Check | null>(null);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [dialog, setDialog] = useState<'new' | 'import' | null>(null);
  const [deleting, setDeleting] = useState<ScriptEntry | null>(null);
  const editor = useRef<EditorHandle>(null);
  const dirty = script !== null && text !== script.text;

  const loadList = useCallback(() => {
    api<ScriptEntry[]>('/api/scripts').then(setScripts);
    api<Voice[]>('/api/voices').then(setVoices);
  }, []);
  useEffect(loadList, [loadList]);

  useEffect(() => {
    if (!selected) {
      setScript(null);
      return;
    }
    api<Script>(`/api/scripts/${enc(selected)}`)
      .then((s) => {
        setScript(s);
        setText(s.text);
        setCheck(s.check);
      })
      .catch((err) => {
        toast.error((err as Error).message);
        onSelect(null);
      });
  }, [selected, onSelect]);

  const save = useCallback(async () => {
    if (!script) return null;
    const r = await api<{ check: Check }>(`/api/scripts/${enc(script.name)}`, 'PUT', { text });
    setScript({ ...script, text });
    setCheck(r.check);
    return r.check;
  }, [script, text]);

  async function select(name: string) {
    if (dirty) await save();
    onSelect(name);
  }

  async function remove(entry: ScriptEntry) {
    await api(`/api/scripts/${enc(entry.name)}`, 'DELETE');
    if (entry.name === selected) onSelect(null);
    loadList();
  }

  function insertVoice(v: Voice) {
    const path = script?.linked ? `${settings.workspace}/voices/${v.name}.wav` : `../voices/${v.name}.wav`;
    const speaker = v.name.replace(/^\d+_/, '');
    editor.current?.insertLine(`@voice ${speaker} = ref: ${path}`);
  }

  const shown = scripts.filter((s) => s.name.toLowerCase().includes(query.toLowerCase()));

  return (
    <div className="grid h-full min-h-0 grid-cols-[250px_1fr_340px] max-lg:grid-cols-[220px_1fr] max-md:grid-cols-1">
      <aside className="flex min-h-0 flex-col border-r border-line bg-surface max-md:max-h-64 max-md:border-r-0 max-md:border-b">
        <div className="flex items-center gap-1 px-3 pt-3 pb-2">
          <h2 className="flex-1 text-sm font-semibold tracking-wide text-muted uppercase">{t('scripts.title')}</h2>
          <IconButton label={t('scripts.import')} onClick={() => setDialog('import')}>
            <FolderInput size={16} />
          </IconButton>
          <IconButton label={t('scripts.new')} onClick={() => setDialog('new')}>
            <Plus size={16} />
          </IconButton>
        </div>
        <div className="relative px-3 pb-2">
          <Search size={14} className="pointer-events-none absolute top-2.5 left-5.5 text-muted" />
          <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t('common.search')} className="h-8 pl-7" />
        </div>
        <nav className="flex min-h-0 flex-1 flex-col gap-px overflow-y-auto px-2 pb-3">
          {shown.map((s) => (
            <div
              key={s.name}
              className={`group flex items-center gap-2 rounded-md pr-1 pl-2.5 ${s.name === selected ? 'bg-primary text-on-primary' : 'hover:bg-surface-2'}`}
            >
              <button onClick={() => select(s.name)} className="flex min-w-0 flex-1 items-center gap-2 py-1.5 text-left">
                <FileText size={14} className="shrink-0 opacity-60" />
                <span className="truncate">{s.name}</span>
                {s.linked && <Link2 size={13} aria-label={t('common.linked')} className="shrink-0 opacity-60" />}
                {s.missing && <AlertTriangle size={13} aria-label={t('common.missing')} className="shrink-0 text-warn" />}
              </button>
              <button
                aria-label={t('common.delete')}
                onClick={() => setDeleting(s)}
                className="invisible rounded-sm p-1 opacity-60 group-hover:visible hover:opacity-100"
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
          {!shown.length && <p className="px-2.5 py-2 text-sm text-muted">{scripts.length ? t('scripts.noMatch') : t('scripts.empty')}</p>}
        </nav>
      </aside>

      {script ? (
        <section className="flex min-h-0 min-w-0 flex-col max-md:min-h-96">
          <div className="flex flex-wrap items-center gap-2 border-b border-line bg-surface px-4 py-2">
            <h2 className="truncate text-lg font-semibold">{script.name}</h2>
            {script.linked && (
              <span title={t('common.linkedTo', { target: script.target ?? '' })}>
                <Badge>
                  <Link2 size={11} />
                  {t('common.linked')}
                </Badge>
              </span>
            )}
            {dirty && <Badge tone="accent">{t('editor.unsaved')}</Badge>}
            <CheckStatus check={check} />
            <div className="ml-auto flex items-center gap-1">
              <DropdownMenu.Root>
                <DropdownMenu.Trigger asChild>
                  <Button variant="ghost">
                    <Mic size={15} />
                    {t('editor.insertVoice')}
                  </Button>
                </DropdownMenu.Trigger>
                <DropdownMenu.Portal>
                  <DropdownMenu.Content
                    align="end"
                    sideOffset={4}
                    className="z-50 max-h-80 w-64 overflow-y-auto rounded-md border border-line bg-surface p-1 shadow-pop"
                  >
                    {voices.map((v) => (
                      <DropdownMenu.Item
                        key={v.name}
                        onSelect={() => insertVoice(v)}
                        className="flex cursor-default flex-col rounded-sm px-2 py-1.5 outline-none data-highlighted:bg-surface-2"
                      >
                        <span>{v.name}</span>
                        <span className="truncate text-sm text-muted">{v.transcript}</span>
                      </DropdownMenu.Item>
                    ))}
                    {!voices.length && <p className="px-2 py-1.5 text-sm text-muted">{t('editor.noVoices')}</p>}
                  </DropdownMenu.Content>
                </DropdownMenu.Portal>
              </DropdownMenu.Root>
              <Popover.Root>
                <Popover.Trigger asChild>
                  <Button variant="ghost">
                    <BookOpen size={15} />
                    {t('editor.syntax')}
                  </Button>
                </Popover.Trigger>
                <Popover.Portal>
                  <Popover.Content
                    align="end"
                    sideOffset={4}
                    className="z-50 rounded-md border border-line bg-surface p-3 shadow-pop"
                  >
                    <pre className="font-mono text-sm leading-relaxed whitespace-pre-wrap">{t('editor.syntaxBody')}</pre>
                  </Popover.Content>
                </Popover.Portal>
              </Popover.Root>
              <Button onClick={() => save().then(() => toast.success(t('common.saved')))} disabled={!dirty}>
                <Save size={15} />
                {t('common.save')}
              </Button>
            </div>
          </div>
          <div className="min-h-0 flex-1">
            <Editor
              ref={editor}
              value={text}
              onChange={setText}
              onSave={() => void save()}
              errorAt={check && !check.ok ? check.line : null}
            />
          </div>
        </section>
      ) : (
        <section className="grid place-items-center p-10 text-center text-muted">
          <div className="flex flex-col items-center gap-3">
            <FileText size={32} className="opacity-50" />
            <p>{scripts.length ? t('scripts.pick') : t('scripts.empty')}</p>
            <div className="flex gap-2">
              <Button onClick={() => setDialog('import')}>
                <FolderInput size={15} />
                {t('scripts.import')}
              </Button>
              <Button variant="primary" onClick={() => setDialog('new')}>
                <Plus size={15} />
                {t('scripts.new')}
              </Button>
            </div>
          </div>
        </section>
      )}

      {script && (
        <RenderPanel
          key={script.name}
          script={script.name}
          check={check}
          engines={engines}
          defaultLanguage={settings.language}
          save={save}
          onOpenSettings={onOpenSettings}
        />
      )}

      <NewScriptDialog open={dialog === 'new'} onOpenChange={(o) => setDialog(o ? 'new' : null)} onCreated={(n) => (loadList(), onSelect(n))} />
      <ImportDialog open={dialog === 'import'} onOpenChange={(o) => setDialog(o ? 'import' : null)} onDone={loadList} />
      <Confirm
        open={deleting !== null}
        onOpenChange={(o) => !o && setDeleting(null)}
        title={t('scripts.deleteTitle', { name: deleting?.name ?? '' })}
        description={deleting?.linked ? t('scripts.deleteLink') : t('scripts.deleteFile')}
        onConfirm={() => deleting && remove(deleting)}
      />
    </div>
  );
}

function CheckStatus({ check }: { check: Check | null }) {
  const { t } = useI18n();
  if (!check) return null;
  if (check.ok)
    return (
      <span className="inline-flex items-center gap-1 text-sm text-good">
        <CircleCheck size={14} />
        {t('editor.valid', { voices: check.voices, lines: check.lines })}
      </span>
    );
  return (
    <span className="inline-flex min-w-0 items-center gap-1 text-sm text-bad">
      <CircleX size={14} className="shrink-0" />
      <span className="truncate">{check.line ? t('editor.error', { line: check.line, error: check.error }) : check.error}</span>
    </span>
  );
}

function RenderPanel({
  script,
  check,
  engines,
  defaultLanguage,
  save,
  onOpenSettings,
}: {
  script: string;
  check: Check | null;
  engines: Engine[];
  defaultLanguage: string;
  save: () => Promise<Check | null>;
  onOpenSettings: () => void;
}) {
  const { t, locale } = useI18n();
  const [renders, setRenders] = useState<Render[]>([]);
  const [engine, setEngine] = useState(() => localStorage.getItem('castscript.engine') ?? '');
  const [language, setLanguage] = useState(defaultLanguage);
  const [deleting, setDeleting] = useState<Render | null>(null);
  const running = renders.find((r) => r.status === 'running');

  const load = useCallback(() => api<Render[]>(`/api/renders?script=${enc(script)}`).then(setRenders), [script]);
  useEffect(() => void load(), [load]);
  useEffect(() => {
    if (!running) return;
    const timer = setInterval(load, 1000);
    return () => clearInterval(timer);
  }, [running, load]);

  const kinds = check?.ok ? check.kinds : [];
  const options = engines.map((e) => {
    const missing = kinds.filter((k) => !e.kinds.includes(k));
    const note = !e.installed ? t('render.notInstalled') : missing.length ? t('render.needsKinds', { kinds: missing.join(', ') }) : e.kinds.join(' · ');
    return { value: e.name, label: e.name, note, disabled: !e.installed || missing.length > 0 };
  });
  const usable = options.filter((o) => !o.disabled).map((o) => o.value);
  const chosen = usable.includes(engine) ? engine : (usable[0] ?? '');

  async function start() {
    const c = await save();
    if (!c?.ok) {
      toast.error(t('render.fixScript'));
      return;
    }
    try {
      await api<Render>('/api/renders', 'POST', { script, engine: chosen, language });
      load();
    } catch (err) {
      toast.error((err as Error).message);
    }
  }

  async function remove(r: Render) {
    try {
      await api(`/api/renders/${r.id}`, 'DELETE');
      load();
    } catch (err) {
      toast.error((err as Error).message);
    }
  }

  return (
    <aside className="flex min-h-0 flex-col overflow-y-auto border-l border-line bg-surface max-lg:col-span-2 max-lg:border-t max-lg:border-l-0 max-md:col-span-1">
      <div className="flex flex-col gap-3 border-b border-line p-4">
        <h2 className="text-sm font-semibold tracking-wide text-muted uppercase">{t('render.title')}</h2>
        {engines.some((e) => e.installed) ? (
          <>
            <div className="grid grid-cols-[1fr_auto] gap-2">
              <Select
                label={t('render.engine')}
                value={chosen}
                options={options}
                onChange={(v) => (setEngine(v), localStorage.setItem('castscript.engine', v))}
              />
              <Select
                label={t('render.language')}
                value={language}
                options={LANGUAGES.map((l) => ({ value: l, label: t(`lang.${l}`) }))}
                onChange={setLanguage}
              />
            </div>
            {running ? (
              <Button onClick={() => api(`/api/renders/${running.id}/stop`, 'POST').then(load)}>
                <Square size={14} />
                {t('render.stop')}
              </Button>
            ) : (
              <Button variant="accent" onClick={start} disabled={!chosen} className="h-9">
                <Play size={15} />
                {t('render.start')}
              </Button>
            )}
          </>
        ) : (
          <div className="flex flex-col gap-2 rounded-md bg-surface-2 p-3 text-sm text-muted">
            <p>{t('render.noEngines')}</p>
            <Button onClick={onOpenSettings} className="self-start">
              {t('render.openSettings')}
            </Button>
          </div>
        )}
      </div>

      <div className="flex flex-col gap-3 p-4">
        <h3 className="text-sm font-semibold tracking-wide text-muted uppercase">{t('render.history')}</h3>
        {renders.map((r) => (
          <article key={r.id} className="flex flex-col gap-2 rounded-md border border-line p-3">
            <div className="flex items-center gap-2">
              <span className="font-semibold">{r.engine}</span>
              <StatusBadge status={r.status} />
              <span className="ml-auto text-sm text-muted">{timeAgo(r.created_at, locale)}</span>
              {r.status !== 'running' && (
                <IconButton label={t('common.delete')} onClick={() => setDeleting(r)} className="size-6">
                  <Trash2 size={13} />
                </IconButton>
              )}
            </div>
            {r.status === 'running' && <Progress render={r} />}
            {r.files.mp3 && <audio controls preload="none" src={r.files.mp3} className="h-8 w-full" />}
            <div className="flex items-center gap-3 text-sm text-muted">
              <span className="flex-1">{renderStats(r, t)}</span>
              {r.files.mp3 && (
                <a href={r.files.mp3} download className="text-primary hover:underline">
                  mp3
                </a>
              )}
              {r.files.srt && (
                <a href={r.files.srt} target="_blank" rel="noreferrer" className="text-primary hover:underline">
                  srt
                </a>
              )}
              <LogLink render={r} />
            </div>
          </article>
        ))}
        {!renders.length && <p className="text-sm text-muted">{t('render.none')}</p>}
      </div>
      <Confirm
        open={deleting !== null}
        onOpenChange={(o) => !o && setDeleting(null)}
        title={t('render.deleteTitle', { id: deleting?.id ?? '' })}
        description={t('render.deleteBody')}
        onConfirm={() => deleting && remove(deleting)}
      />
    </aside>
  );
}

function Progress({ render }: { render: Render }) {
  const { t } = useI18n();
  const p = render.progress;
  const pct = p?.total ? (p.done / p.total) * 100 : 0;
  return (
    <div className="flex items-center gap-2 text-sm text-muted">
      <div
        role="progressbar"
        aria-valuenow={Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-1.5 flex-1 overflow-hidden rounded-pill bg-surface-2"
      >
        <div className="h-full bg-accent transition-all" style={{ width: `${pct}%` }} />
      </div>
      <span>{p?.total ? t('render.lines', { done: p.done, total: p.total }) : t('render.loading')}</span>
    </div>
  );
}

export function LogLink({ render }: { render: Render }) {
  const { t } = useI18n();
  const [log, setLog] = useState('');
  return (
    <Popover.Root onOpenChange={(o) => o && api<Render>(`/api/renders/${render.id}`).then((r) => setLog(r.log ?? ''))}>
      <Popover.Trigger className="text-primary hover:underline">{t('render.log')}</Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="end"
          sideOffset={4}
          className="z-50 max-h-96 w-[min(90vw,640px)] overflow-auto rounded-md border border-line bg-surface p-3 shadow-pop"
        >
          <pre className="font-mono text-xs leading-relaxed break-all whitespace-pre-wrap">{log}</pre>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
