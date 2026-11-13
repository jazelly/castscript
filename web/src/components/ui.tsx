// Shared UI pieces: Radix primitives styled with the design tokens in theme.css.
import { Check, ChevronDown, X } from 'lucide-react';
import { AlertDialog, Dialog, Select as RSelect, Tooltip } from 'radix-ui';
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from 'react';
import { useI18n } from '../i18n';

type Variant = 'primary' | 'accent' | 'outline' | 'ghost' | 'danger';
const variants: Record<Variant, string> = {
  primary: 'bg-primary text-on-primary hover:opacity-90',
  accent: 'bg-accent text-on-accent font-semibold hover:opacity-90',
  outline: 'border border-line bg-surface hover:bg-surface-2',
  ghost: 'hover:bg-surface-2',
  danger: 'bg-bad text-on-accent font-semibold hover:opacity-90',
};

export function Button({
  variant = 'outline',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      {...props}
      className={`inline-flex h-8 items-center justify-center gap-1.5 rounded-md px-3 text-base whitespace-nowrap transition disabled:opacity-50 ${variants[variant]} ${className}`}
    />
  );
}

/** Icon-only button: `label` is its accessible name and tooltip. */
export function IconButton({
  label,
  children,
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { label: string }) {
  return (
    <Tooltip.Root>
      <Tooltip.Trigger asChild>
        <button
          {...props}
          aria-label={label}
          className={`inline-flex size-8 shrink-0 items-center justify-center rounded-md text-muted transition hover:bg-surface-2 hover:text-fg disabled:opacity-50 ${className}`}
        >
          {children}
        </button>
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content
          sideOffset={4}
          className="z-50 rounded-sm bg-primary px-2 py-1 text-sm text-on-primary shadow-pop"
        >
          {label}
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}

const field = 'w-full rounded-md border border-line bg-surface px-2.5 text-base text-fg outline-primary placeholder:text-muted';

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`h-9 ${field} ${props.className ?? ''}`} />;
}

export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={`py-2 ${field} ${props.className ?? ''}`} />;
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-sm font-semibold text-muted">{label}</span>
      {children}
      {hint && <span className="text-sm text-muted">{hint}</span>}
    </label>
  );
}

export type Option = { value: string; label: string; note?: string; disabled?: boolean };

export function Select({
  value,
  onChange,
  options,
  label,
  className = '',
}: {
  value: string;
  onChange: (value: string) => void;
  options: Option[];
  label: string;
  className?: string;
}) {
  return (
    <RSelect.Root value={value || undefined} onValueChange={onChange}>
      <RSelect.Trigger
        aria-label={label}
        className={`inline-flex h-9 items-center justify-between gap-2 rounded-md border border-line bg-surface px-2.5 text-base outline-primary ${className}`}
      >
        <RSelect.Value placeholder="—" />
        <RSelect.Icon>
          <ChevronDown size={14} className="text-muted" />
        </RSelect.Icon>
      </RSelect.Trigger>
      <RSelect.Portal>
        <RSelect.Content
          position="popper"
          sideOffset={4}
          className="z-50 max-h-80 min-w-(--radix-select-trigger-width) overflow-hidden rounded-md border border-line bg-surface shadow-pop"
        >
          <RSelect.Viewport className="p-1">
            {options.map((o) => (
              <RSelect.Item
                key={o.value}
                value={o.value}
                disabled={o.disabled}
                className="flex cursor-default items-center gap-2 rounded-sm py-1.5 pr-2 pl-7 text-base outline-none select-none data-disabled:opacity-45 data-highlighted:bg-surface-2"
              >
                <RSelect.ItemIndicator className="absolute left-2.5">
                  <Check size={13} />
                </RSelect.ItemIndicator>
                <RSelect.ItemText>{o.label}</RSelect.ItemText>
                {o.note && <span className="ml-auto pl-3 text-sm text-muted">{o.note}</span>}
              </RSelect.Item>
            ))}
          </RSelect.Viewport>
        </RSelect.Content>
      </RSelect.Portal>
    </RSelect.Root>
  );
}

export function Modal({
  open,
  onOpenChange,
  title,
  description,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
}) {
  const { t } = useI18n();
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-scrim" />
        <Dialog.Content className="fixed top-1/2 left-1/2 z-50 flex w-[min(92vw,480px)] -translate-1/2 flex-col gap-4 rounded-lg border border-line bg-surface p-5 shadow-pop">
          <div className="flex items-start gap-3">
            <div className="flex flex-1 flex-col gap-1">
              <Dialog.Title className="text-lg font-semibold">{title}</Dialog.Title>
              {description ? (
                <Dialog.Description className="text-base text-muted">{description}</Dialog.Description>
              ) : (
                <Dialog.Description className="sr-only">{title}</Dialog.Description>
              )}
            </div>
            <Dialog.Close asChild>
              <IconButton label={t('common.cancel')}>
                <X size={16} />
              </IconButton>
            </Dialog.Close>
          </div>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function Confirm({
  open,
  onOpenChange,
  title,
  description,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  onConfirm: () => void;
}) {
  const { t } = useI18n();
  return (
    <AlertDialog.Root open={open} onOpenChange={onOpenChange}>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="fixed inset-0 z-40 bg-scrim" />
        <AlertDialog.Content className="fixed top-1/2 left-1/2 z-50 flex w-[min(92vw,420px)] -translate-1/2 flex-col gap-4 rounded-lg border border-line bg-surface p-5 shadow-pop">
          <AlertDialog.Title className="text-lg font-semibold">{title}</AlertDialog.Title>
          <AlertDialog.Description className="text-base text-muted">{description}</AlertDialog.Description>
          <div className="flex justify-end gap-2">
            <AlertDialog.Cancel asChild>
              <Button>{t('common.cancel')}</Button>
            </AlertDialog.Cancel>
            <AlertDialog.Action asChild>
              <Button variant="danger" onClick={onConfirm}>
                {t('common.delete')}
              </Button>
            </AlertDialog.Action>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}

/** Status is always shown with text, never colour alone. */
export function Badge({ tone = 'muted', children }: { tone?: 'muted' | 'good' | 'bad' | 'warn' | 'accent'; children: ReactNode }) {
  const tones = {
    muted: 'border-line text-muted',
    good: 'border-good text-good',
    bad: 'border-bad text-bad',
    warn: 'border-warn text-warn',
    accent: 'border-accent text-accent',
  };
  return (
    <span className={`inline-flex h-5 items-center gap-1 rounded-pill border px-2 text-xs font-semibold ${tones[tone]}`}>
      {children}
    </span>
  );
}

export function PageHeader({ title, subtitle, children }: { title: string; subtitle?: string; children?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end gap-3 border-b border-line px-6 py-5">
      <div className="flex flex-1 flex-col gap-1">
        <h1 className="text-2xl font-semibold">{title}</h1>
        {subtitle && <p className="text-base text-muted">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}
