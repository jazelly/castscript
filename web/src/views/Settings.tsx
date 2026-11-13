import { CircleCheck, CircleMinus, FolderOpen } from 'lucide-react';
import { type FormEvent, useState } from 'react';
import { toast } from 'sonner';
import { type Engine, LANGUAGES, type Settings as SettingsData, api } from '../api';
import { Button, Field, Input, PageHeader, Select } from '../components/ui';
import { useI18n } from '../i18n';

export function Settings({
  settings,
  engines,
  onSaved,
}: {
  settings: SettingsData;
  engines: Engine[];
  onSaved: (s: SettingsData) => void;
}) {
  const { t } = useI18n();
  const [language, setLanguage] = useState(settings.language);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    try {
      const saved = await api<SettingsData>('/api/settings', 'PUT', {
        envs: String(f.get('envs')).trim(),
        breeze_dir: String(f.get('breeze_dir')).trim(),
        breeze_checkpoint: String(f.get('breeze_checkpoint')).trim(),
        language,
      });
      onSaved(saved);
      toast.success(t('common.saved'));
    } catch (err) {
      toast.error((err as Error).message);
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <PageHeader title={t('settings.title')} />
      <div className="min-h-0 flex-1 overflow-y-auto p-6">
        <div className="flex max-w-3xl flex-col gap-6">
          <section className="flex flex-col gap-2 rounded-lg border border-line bg-surface p-5 shadow-card">
            <h2 className="text-lg font-semibold">{t('settings.workspace')}</h2>
            <p className="flex items-center gap-2 font-mono text-base">
              <FolderOpen size={15} className="text-muted" />
              {settings.workspace}
            </p>
            <p className="text-sm text-muted">{t('settings.workspaceHint')}</p>
          </section>

          <form onSubmit={submit} className="flex flex-col gap-4 rounded-lg border border-line bg-surface p-5 shadow-card">
            <h2 className="text-lg font-semibold">{t('settings.engines')}</h2>
            <Field label={t('settings.envs')} hint={t('settings.envsHint')}>
              <Input name="envs" defaultValue={settings.envs} placeholder="~/castscript-envs" className="font-mono" />
            </Field>
            <div className="grid grid-cols-2 gap-4 max-md:grid-cols-1">
              <Field label={t('settings.breezeDir')}>
                <Input name="breeze_dir" defaultValue={settings.breeze_dir} placeholder="~/breeze-tts-mlx" className="font-mono" />
              </Field>
              <Field label={t('settings.breezeCheckpoint')}>
                <Input
                  name="breeze_checkpoint"
                  defaultValue={settings.breeze_checkpoint}
                  placeholder="~/breeze-tts-mlx/chkpt-mlx-int8"
                  className="font-mono"
                />
              </Field>
            </div>
            <Field label={t('settings.language')}>
              <Select
                label={t('settings.language')}
                value={language}
                onChange={setLanguage}
                options={LANGUAGES.map((l) => ({ value: l, label: t(`lang.${l}`) }))}
                className="w-48"
              />
            </Field>
            <Button variant="primary" className="self-start">
              {t('common.save')}
            </Button>
          </form>

          <section className="flex flex-col gap-3 rounded-lg border border-line bg-surface p-5 shadow-card">
            <h2 className="text-lg font-semibold">{t('settings.detected')}</h2>
            <ul className="grid grid-cols-2 gap-2 max-md:grid-cols-1">
              {engines.map((e) => (
                <li key={e.name} className="flex items-center gap-2 rounded-md bg-surface-2 px-3 py-2">
                  {e.installed ? <CircleCheck size={15} className="text-good" /> : <CircleMinus size={15} className="text-muted" />}
                  <span className="font-semibold">{e.name}</span>
                  <span className="text-sm text-muted">{e.installed ? t('settings.installed') : t('settings.notInstalled')}</span>
                  <span className="ml-auto text-sm text-muted">{t('settings.kinds', { kinds: e.kinds.join(', ') })}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      </div>
    </div>
  );
}
