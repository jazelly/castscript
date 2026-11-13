import { type FormEvent, useState } from 'react';
import { toast } from 'sonner';
import { type ImportResult, type RenderStatus, type Voice, api } from '../api';
import { type T, useI18n } from '../i18n';
import { Badge, Button, Field, Input, Modal, Textarea } from './ui';

export function ImportDialog({ open, onOpenChange, onDone }: { open: boolean; onOpenChange: (o: boolean) => void; onDone: () => void }) {
  const { t } = useI18n();
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await api<ImportResult>('/api/import', 'POST', { path: new FormData(e.currentTarget).get('path') });
      toast.success(t('import.done', { scripts: r.scripts.length, voices: r.voices.length, skipped: r.skipped }));
      onOpenChange(false);
      onDone();
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open={open} onOpenChange={onOpenChange} title={t('import.title')} description={t('import.body')}>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <Field label={t('import.path')}>
          <Input name="path" required autoFocus placeholder={t('import.placeholder')} />
        </Field>
        <div className="flex justify-end gap-2">
          <Button type="button" onClick={() => onOpenChange(false)}>
            {t('common.cancel')}
          </Button>
          <Button variant="primary" disabled={busy}>
            {t('common.import')}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export function NewScriptDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onCreated: (name: string) => void;
}) {
  const { t } = useI18n();

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const name = String(new FormData(e.currentTarget).get('name')).trim().replace(/\.cast\.txt$/, '');
    try {
      await api('/api/scripts', 'POST', { name, text: t('scripts.template') });
      toast.success(t('scripts.created', { name }));
      onOpenChange(false);
      onCreated(name);
    } catch (err) {
      toast.error((err as Error).message);
    }
  }

  return (
    <Modal open={open} onOpenChange={onOpenChange} title={t('scripts.new')}>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <Field label={t('common.name')}>
          <Input name="name" required autoFocus placeholder={t('scripts.namePlaceholder')} />
        </Field>
        <div className="flex justify-end gap-2">
          <Button type="button" onClick={() => onOpenChange(false)}>
            {t('common.cancel')}
          </Button>
          <Button variant="primary">{t('common.create')}</Button>
        </div>
      </form>
    </Modal>
  );
}

export function VoiceDialog({ open, onOpenChange, onDone }: { open: boolean; onOpenChange: (o: boolean) => void; onDone: () => void }) {
  const { t } = useI18n();
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const file = f.get('audio') as File;
    setBusy(true);
    try {
      const audio = await new Promise<string>((resolve) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result).split(',')[1]);
        reader.readAsDataURL(file);
      });
      const name = String(f.get('name')).trim();
      await api<Voice[]>('/api/voices', 'POST', { name, transcript: f.get('transcript'), audio });
      toast.success(t('voices.added', { name }));
      onOpenChange(false);
      onDone();
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open={open} onOpenChange={onOpenChange} title={t('voices.upload')} description={t('voices.subtitle')}>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <Field label={t('common.name')}>
          <Input name="name" required autoFocus placeholder="narrator" />
        </Field>
        <Field label={t('voices.file')}>
          <Input name="audio" type="file" accept=".wav,audio/wav" required className="pt-1.5" />
        </Field>
        <Field label={t('voices.transcript')}>
          <Textarea name="transcript" rows={3} required placeholder={t('voices.transcriptPlaceholder')} />
        </Field>
        <div className="flex justify-end gap-2">
          <Button type="button" onClick={() => onOpenChange(false)}>
            {t('common.cancel')}
          </Button>
          <Button variant="primary" disabled={busy}>
            {t('voices.upload')}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export function StatusBadge({ status }: { status: RenderStatus }) {
  const { t } = useI18n();
  const tone = { running: 'accent', done: 'good', failed: 'bad', stopped: 'warn', interrupted: 'warn' } as const;
  return <Badge tone={tone[status]}>{t(`status.${status}`)}</Badge>;
}

export function timeAgo(seconds: number, locale: string): string {
  const diff = (seconds * 1000 - Date.now()) / 1000;
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });
  for (const [unit, size] of [['day', 86400], ['hour', 3600], ['minute', 60]] as const) {
    if (Math.abs(diff) >= size) return rtf.format(Math.round(diff / size), unit);
  }
  return rtf.format(Math.round(diff), 'second');
}

export function renderStats(r: { audio_seconds: number | null; created_at: number; finished_at: number | null }, t: T): string {
  const parts = [];
  if (r.audio_seconds) parts.push(t('render.audio', { seconds: r.audio_seconds.toFixed(1) }));
  if (r.finished_at) parts.push(t('render.took', { seconds: Math.round(r.finished_at - r.created_at) }));
  return parts.join(' · ');
}
