import { useEffect, useState } from 'react';
import { type Render, api } from '../api';
import { StatusBadge, renderStats, timeAgo } from '../components/dialogs';
import { PageHeader } from '../components/ui';
import { useI18n } from '../i18n';
import { LogLink } from './Studio';

export function History({ onOpenScript }: { onOpenScript: (name: string) => void }) {
  const { t, locale } = useI18n();
  const [renders, setRenders] = useState<Render[]>([]);
  const running = renders.some((r) => r.status === 'running');

  useEffect(() => {
    const load = () => api<Render[]>('/api/renders').then(setRenders);
    load();
    if (!running) return;
    const timer = setInterval(load, 2000);
    return () => clearInterval(timer);
  }, [running]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <PageHeader title={t('history.title')} subtitle={t('history.subtitle')} />
      <div className="min-h-0 flex-1 overflow-auto p-6">
        {renders.length ? (
          <table className="w-full border-separate border-spacing-0 overflow-hidden rounded-lg border border-line bg-surface text-left">
            <thead className="text-sm text-muted">
              <tr>
                {['#', t('history.script'), t('history.engine'), t('history.status'), t('history.when'), t('history.length'), t('history.output')].map(
                  (h) => (
                    <th key={h} className="border-b border-line px-3 py-2 font-semibold">
                      {h}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {renders.map((r) => (
                <tr key={r.id} className="align-middle hover:bg-surface-2">
                  <td className="border-b border-line px-3 py-2 text-muted">{r.id}</td>
                  <td className="border-b border-line px-3 py-2">
                    <button onClick={() => onOpenScript(r.script)} className="text-primary hover:underline">
                      {r.script}
                    </button>
                  </td>
                  <td className="border-b border-line px-3 py-2">
                    {r.engine} <span className="text-sm text-muted">· {t(`lang.${r.language}` as 'lang.zh')}</span>
                  </td>
                  <td className="border-b border-line px-3 py-2">
                    <StatusBadge status={r.status} />
                  </td>
                  <td className="border-b border-line px-3 py-2 text-sm text-muted">{timeAgo(r.created_at, locale)}</td>
                  <td className="border-b border-line px-3 py-2 text-sm text-muted">{renderStats(r, t)}</td>
                  <td className="border-b border-line px-3 py-2">
                    <div className="flex items-center gap-3 text-sm">
                      {r.files.mp3 && <audio controls preload="none" src={r.files.mp3} className="h-8 w-56" />}
                      <LogLink render={r} />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-muted">{t('history.empty')}</p>
        )}
      </div>
    </div>
  );
}
