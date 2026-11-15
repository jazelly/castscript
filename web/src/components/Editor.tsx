// Script editor: CodeMirror with castscript highlighting and the parse-error line marked.
import { StreamLanguage, syntaxHighlighting } from '@codemirror/language';
import { RangeSetBuilder, StateEffect, StateField } from '@codemirror/state';
import { Decoration, type DecorationSet, EditorView, keymap } from '@codemirror/view';
import { Tag, tagHighlighter } from '@lezer/highlight';
import CodeMirror, { type ReactCodeMirrorRef } from '@uiw/react-codemirror';
import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef } from 'react';

// Tokens map to .tok-* classes in theme.css.
const tokens = { voice: Tag.define(), speaker: Tag.define(), emotion: Tag.define(), event: Tag.define(), comment: Tag.define() };
const highlight = syntaxHighlighting(
  tagHighlighter(Object.entries(tokens).map(([name, tag]) => ({ tag, class: `tok-${name}` }))),
);

const castscript = StreamLanguage.define<{ lineStart: boolean; speakerDone: boolean }>({
  startState: () => ({ lineStart: true, speakerDone: false }),
  token(stream, state) {
    if (stream.sol()) {
      state.lineStart = true;
      state.speakerDone = false;
    }
    if (state.lineStart) {
      state.lineStart = false;
      if (stream.match(/^\s*#.*/)) return 'comment';
      if (stream.match(/^@voice\b/)) return 'voice';
      if (stream.match(/^\s*(---|<(pause|停顿|at|时间)[^>]*>)\s*$/)) return 'event';
      if (stream.match(/^[^：:（()）@#\s][^：:（()）]*?(?=\s*[（(：:])/)) {
        state.speakerDone = true;
        return 'speaker';
      }
    }
    if (state.speakerDone && stream.match(/^[（(][^）)]*[）)]/)) return 'emotion';
    if (stream.match(/^(\[(笑|叹气|咳嗽|清嗓子)\]|<(pause|停顿)[^>]*>)/)) return 'event';
    if (stream.match(/^[：:]/)) {
      state.speakerDone = false;
      return null;
    }
    stream.next();
    return null;
  },
  tokenTable: tokens,
});

const setErrorLine = StateEffect.define<number | null>();
const errorLine = StateField.define<DecorationSet>({
  create: () => Decoration.none,
  update(deco, tr) {
    for (const e of tr.effects) {
      if (e.is(setErrorLine)) {
        const builder = new RangeSetBuilder<Decoration>();
        if (e.value && e.value <= tr.state.doc.lines) {
          const line = tr.state.doc.line(e.value);
          builder.add(line.from, line.from, Decoration.line({ class: 'cm-error-line' }));
        }
        return builder.finish();
      }
    }
    return deco.map(tr.changes);
  },
  provide: (f) => EditorView.decorations.from(f),
});

export type EditorHandle = { insertLine: (text: string) => void };

type Props = { value: string; onChange: (value: string) => void; onSave: () => void; errorAt: number | null };

export const Editor = forwardRef<EditorHandle, Props>(function Editor({ value, onChange, onSave, errorAt }, ref) {
  const cm = useRef<ReactCodeMirrorRef>(null);
  const save = useRef(onSave);
  save.current = onSave;

  useImperativeHandle(ref, () => ({
    insertLine(text) {
      const view = cm.current?.view;
      if (!view) return;
      const line = view.state.doc.lineAt(view.state.selection.main.head);
      view.dispatch({ changes: { from: line.from, insert: `${text}\n` }, selection: { anchor: line.from + text.length + 1 } });
      view.focus();
    },
  }));

  useEffect(() => {
    cm.current?.view?.dispatch({ effects: setErrorLine.of(errorAt) });
  }, [errorAt, value]);

  const extensions = useMemo(
    () => [
      castscript,
      highlight,
      errorLine,
      EditorView.lineWrapping,
      keymap.of([{ key: 'Mod-s', preventDefault: true, run: () => (save.current(), true) }]),
    ],
    [],
  );

  return (
    <CodeMirror
      ref={cm}
      value={value}
      onChange={onChange}
      extensions={extensions}
      theme="none"
      height="100%"
      className="h-full min-h-0"
      basicSetup={{ foldGutter: false, highlightActiveLine: true, autocompletion: false, searchKeymap: true }}
    />
  );
});
