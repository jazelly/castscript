import { AlertTriangle, Copy, FolderInput, Link2, Pause, Play, Plus, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { type Voice, api, enc } from '../api';
import { ImportDialog, VoiceDialog } from '../components/dialogs';
import { Badge, Button, Confirm, IconButton, PageHeader } from '../components/ui';
import { useI18n } from '../i18n';

export function Voices() {
  const { t } = useI18n();
  const [voices, setVoices] = useState<Voice[]>([]);
  const [dialog, setDialog] = useState<'upload' | 'import' | null>(null);
  const [deleting, setDeleting] = useState<Voice | null>(null);
  const [playing, setPlaying] = useState<string | null>(null);
  const audio = useRef<HTMLAudioElement | null>(null);

  const load = useCallback(() => void api<Voice[]>('/api/voices').then(setVoices), []);
  useEffect(load, [load]);
  useEffect(() => () => audio.current?.pause(), []);

  function toggle(v: Voice) {
    audio.current?.pause();
    if (playing === v.name) {
      setPlaying(null);
      return;
    }
    const a = new Audio(`/api/voices/${enc(v.name)}/audio`);
    a.onended = () => setPlaying(null);
    a.play();
    audio.current = a;
    setPlaying(v.name);
  }

  async function remove(v: Voice) {
    await api(`/api/voices/${enc(v.name)}`, 'DELETE');
    load();
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <PageHeader title={t('voices.title')} subtitle={t('voices.subtitle')}>
        <Button onClick={() => setDialog('import')}>
          <FolderInput size={15} />
          {t('scripts.import')}
        </Button>
        <Button variant="primary" onClick={() => setDialog('upload')}>
          <Plus size={15} />
          {t('voices.upload')}
        </Button>
      </PageHeader>
      <div className="grid min-h-0 flex-1 auto-rows-min grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-3 overflow-y-auto p-6">
        {voices.map((v) => (
          <article key={v.name} className="flex flex-col gap-2 rounded-lg border border-line bg-surface p-3 shadow-card">
            <div className="flex items-center gap-2">
              <IconButton
                label={playing === v.name ? t('voices.pause', { name: v.name }) : t('voices.play', { name: v.name })}
                onClick={() => toggle(v)}
                disabled={v.missing}
                className="bg-surface-2 text-fg"
              >
                {playing === v.name ? <Pause size={15} /> : <Play size={15} />}
              </IconButton>
              <span className="min-w-0 flex-1 truncate font-semibold">{v.name}</span>
              {v.linked && (
                <span title={t('common.linkedTo', { target: v.target ?? '' })}>
                  <Badge>
                    <Link2 size={11} />
                    {t('common.linked')}
                  </Badge>
                </span>
              )}
              {v.missing && (
                <span title={t('common.missingHint')}>
                  <Badge tone="warn">
                    <AlertTriangle size={11} />
                    {t('common.missing')}
                  </Badge>
                </span>
              )}
            </div>
            <p className="line-clamp-2 min-h-10 text-sm text-muted">{v.transcript}</p>
            <div className="flex justify-end gap-1">
              <IconButton
                label={t('voices.copy')}
                onClick={() =>
                  navigator.clipboard
                    .writeText(`@voice ${v.name.replace(/^\d+_/, '')} = ref: ../voices/${v.name}.wav`)
                    .then(() => toast.success(t('voices.copied')))
                }
              >
                <Copy size={14} />
              </IconButton>
              <IconButton label={t('common.delete')} onClick={() => setDeleting(v)}>
                <Trash2 size={14} />
              </IconButton>
            </div>
          </article>
        ))}
        {!voices.length && <p className="text-muted">{t('voices.empty')}</p>}
      </div>
      <VoiceDialog open={dialog === 'upload'} onOpenChange={(o) => setDialog(o ? 'upload' : null)} onDone={load} />
      <ImportDialog open={dialog === 'import'} onOpenChange={(o) => setDialog(o ? 'import' : null)} onDone={load} />
      <Confirm
        open={deleting !== null}
        onOpenChange={(o) => !o && setDeleting(null)}
        title={t('voices.deleteTitle', { name: deleting?.name ?? '' })}
        description={deleting?.linked ? t('scripts.deleteLink') : t('voices.deleteFile')}
        onConfirm={() => deleting && remove(deleting)}
      />
    </div>
  );
}
