import { AudioLines, FileText, History as HistoryIcon, Languages, Settings as SettingsIcon } from 'lucide-react';
import { Tooltip } from 'radix-ui';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Toaster } from 'sonner';
import { type Engine, type Settings as SettingsData, api } from './api';
import { I18n, type Locale, defaultLocale, translator } from './i18n';
import { History } from './views/History';
import { Settings } from './views/Settings';
import { Studio } from './views/Studio';
import { Voices } from './views/Voices';

type Route = { view: 'studio' | 'voices' | 'history' | 'settings'; script: string | null };

function readRoute(): Route {
  const [view, ...rest] = decodeURIComponent(location.hash.replace(/^#\/?/, '')).split('/');
  if (view === 'voices' || view === 'history' || view === 'settings') return { view, script: null };
  return { view: 'studio', script: rest.join('/') || null };
}

function go(route: Route) {
  location.hash = route.view === 'studio' && route.script ? `/studio/${encodeURIComponent(route.script)}` : `/${route.view}`;
}

export default function App() {
  const [route, setRoute] = useState(readRoute);
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [engines, setEngines] = useState<Engine[]>([]);
  const locale: Locale = settings?.locale === 'zh' || settings?.locale === 'en' ? settings.locale : defaultLocale();
  const i18n = useMemo(() => ({ t: translator(locale), locale }), [locale]);
  const { t } = i18n;

  useEffect(() => {
    const onHash = () => setRoute(readRoute());
    addEventListener('hashchange', onHash);
    return () => removeEventListener('hashchange', onHash);
  }, []);
  useEffect(() => {
    api<SettingsData>('/api/settings').then(setSettings);
  }, []);
  useEffect(() => {
    api<Engine[]>('/api/engines').then(setEngines);
  }, [settings?.envs, settings?.breeze_dir, settings?.breeze_checkpoint]);
  useEffect(() => {
    document.documentElement.lang = locale === 'zh' ? 'zh-CN' : 'en';
  }, [locale]);

  const selectScript = useCallback((script: string | null) => go({ view: 'studio', script }), []);
  const toggleLocale = () =>
    api<SettingsData>('/api/settings', 'PUT', { locale: locale === 'zh' ? 'en' : 'zh' }).then(setSettings);

  if (!settings) return null;

  const nav = [
    { view: 'studio', icon: FileText, label: t('nav.studio') },
    { view: 'voices', icon: AudioLines, label: t('nav.voices') },
    { view: 'history', icon: HistoryIcon, label: t('nav.history') },
    { view: 'settings', icon: SettingsIcon, label: t('nav.settings') },
  ] as const;

  return (
    <I18n.Provider value={i18n}>
      <Tooltip.Provider delayDuration={300}>
        <div className="grid h-dvh grid-cols-[200px_1fr] max-md:grid-cols-1 max-md:grid-rows-[auto_1fr]">
          <header className="flex flex-col gap-1 border-r border-line bg-surface p-3 max-md:flex-row max-md:items-center max-md:border-r-0 max-md:border-b">
            <div className="flex items-center gap-2 px-2 pt-1 pb-4 max-md:p-0 max-md:pr-2">
              <img src="/favicon.svg" alt="" className="size-7" />
              <span className="text-lg font-semibold max-md:hidden">castscript</span>
            </div>
            <nav className="flex flex-col gap-1 max-md:flex-row">
              {nav.map(({ view, icon: Icon, label }) => (
                <button
                  key={view}
                  onClick={() => go({ view, script: view === 'studio' ? route.script : null })}
                  aria-current={route.view === view ? 'page' : undefined}
                  className={`flex items-center gap-2.5 rounded-md px-2.5 py-2 text-left ${route.view === view ? 'bg-primary text-on-primary' : 'text-fg hover:bg-surface-2'}`}
                >
                  <Icon size={16} />
                  <span className="max-md:sr-only">{label}</span>
                </button>
              ))}
            </nav>
            <button
              onClick={toggleLocale}
              aria-label={t('nav.language')}
              className="mt-auto flex items-center gap-2.5 rounded-md px-2.5 py-2 text-muted hover:bg-surface-2 hover:text-fg max-md:mt-0 max-md:ml-auto"
            >
              <Languages size={16} />
              <span>{locale === 'zh' ? '中文 / EN' : 'EN / 中文'}</span>
            </button>
          </header>
          <main className="min-h-0 min-w-0">
            {route.view === 'studio' && (
              <Studio
                selected={route.script}
                onSelect={selectScript}
                engines={engines}
                settings={settings}
                onOpenSettings={() => go({ view: 'settings', script: null })}
              />
            )}
            {route.view === 'voices' && <Voices />}
            {route.view === 'history' && <History onOpenScript={selectScript} />}
            {route.view === 'settings' && <Settings settings={settings} engines={engines} onSaved={setSettings} />}
          </main>
        </div>
        <Toaster
          position="bottom-right"
          toastOptions={{
            unstyled: true,
            classNames: {
              toast: 'flex w-80 items-center gap-2 rounded-md border border-line bg-surface p-3 text-base text-fg shadow-pop',
              success: '[&_[data-icon]]:text-good',
              error: '[&_[data-icon]]:text-bad',
            },
          }}
        />
      </Tooltip.Provider>
    </I18n.Provider>
  );
}
