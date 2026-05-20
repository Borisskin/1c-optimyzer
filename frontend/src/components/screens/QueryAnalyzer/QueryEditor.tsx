import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import { EditorState, StateEffect, StateField, RangeSetBuilder } from "@codemirror/state";
import { EditorView, Decoration, type DecorationSet, keymap, lineNumbers, drawSelection } from "@codemirror/view";
import { defaultKeymap, history, historyKeymap } from "@codemirror/commands";
import { sql } from "@codemirror/lang-sql";
import type { QAFinding } from "@/api/backend";
import styles from "./QueryEditor.module.css";

/** Imperative handle — даёт родителю возможность скроллить и подсвечивать диапазон. */
export interface QueryEditorHandle {
  scrollToRange: (lineStart: number, colStart: number, lineEnd: number, colEnd: number) => void;
}

/** Подсветка ranges из findings — через DecorationSet + StateField. */
const setFindingsEffect = StateEffect.define<QAFinding[]>();

/** Временная "flash" подсветка для клика по карточке finding. null → снять. */
const setFlashEffect = StateEffect.define<{ from: number; to: number } | null>();

function severityClass(sev: QAFinding["severity"]): string {
  switch (sev) {
    case "critical":
      return styles.markCritical;
    case "warning":
      return styles.markWarning;
    case "info":
      return styles.markInfo;
  }
}

const findingsField = StateField.define<DecorationSet>({
  create: () => Decoration.none,
  update(deco, tr) {
    deco = deco.map(tr.changes);
    for (const eff of tr.effects) {
      if (eff.is(setFindingsEffect)) {
        const findings = eff.value;
        const builder = new RangeSetBuilder<Decoration>();
        const doc = tr.state.doc;
        // Преобразуем findings в позиции в документе (1-based → 0-based offset)
        const sorted = [...findings].sort((a, b) => {
          if (a.line_start !== b.line_start) return a.line_start - b.line_start;
          return a.col_start - b.col_start;
        });
        for (const f of sorted) {
          if (f.line_start < 1 || f.line_start > doc.lines) continue;
          const lineStart = doc.line(f.line_start);
          const startOffset = Math.min(lineStart.from + f.col_start - 1, lineStart.to);
          const lineEnd = doc.line(Math.min(f.line_end, doc.lines));
          const endOffset = Math.min(lineEnd.from + f.col_end - 1, lineEnd.to);
          if (endOffset > startOffset) {
            builder.add(
              startOffset,
              endOffset,
              Decoration.mark({
                class: severityClass(f.severity),
                attributes: { title: f.message },
              }),
            );
          }
        }
        deco = builder.finish();
      }
    }
    return deco;
  },
  provide: (field) => EditorView.decorations.from(field),
});

/** Flash-подсветка одного диапазона; снимается через setTimeout в QueryEditor. */
const flashField = StateField.define<DecorationSet>({
  create: () => Decoration.none,
  update(deco, tr) {
    deco = deco.map(tr.changes);
    for (const eff of tr.effects) {
      if (eff.is(setFlashEffect)) {
        if (eff.value === null) {
          deco = Decoration.none;
        } else {
          const builder = new RangeSetBuilder<Decoration>();
          builder.add(
            eff.value.from,
            eff.value.to,
            Decoration.mark({ class: styles.markFlash }),
          );
          deco = builder.finish();
        }
      }
    }
    return deco;
  },
  provide: (field) => EditorView.decorations.from(field),
});


interface QueryEditorProps {
  value: string;
  onChange: (v: string) => void;
  findings: QAFinding[];
  placeholder?: string;
  readOnly?: boolean;
}

export const QueryEditor = forwardRef<QueryEditorHandle, QueryEditorProps>(function QueryEditor(
  { value, onChange, findings, placeholder, readOnly },
  ref,
) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const viewRef = useRef<EditorView | null>(null);
  const flashTimerRef = useRef<number | null>(null);

  // Сборка editor один раз
  useEffect(() => {
    if (!hostRef.current) return;
    const updateListener = EditorView.updateListener.of((u) => {
      if (u.docChanged) {
        const text = u.state.doc.toString();
        onChange(text);
      }
    });
    const state = EditorState.create({
      doc: value,
      extensions: [
        lineNumbers(),
        history(),
        drawSelection(),
        keymap.of([...defaultKeymap, ...historyKeymap]),
        sql(),
        findingsField,
        flashField,
        EditorView.editable.of(!readOnly),
        EditorView.lineWrapping,
        updateListener,
      ],
    });
    const view = new EditorView({ state, parent: hostRef.current });
    viewRef.current = view;
    return () => {
      if (flashTimerRef.current !== null) {
        window.clearTimeout(flashTimerRef.current);
        flashTimerRef.current = null;
      }
      view.destroy();
      viewRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync value when controlled prop changes externally (e.g. after analyze/rewrite paste)
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const current = view.state.doc.toString();
    if (current !== value) {
      view.dispatch({
        changes: { from: 0, to: current.length, insert: value },
      });
    }
  }, [value]);

  // Push findings into the StateField when they change
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    view.dispatch({ effects: setFindingsEffect.of(findings) });
  }, [findings]);

  useImperativeHandle(
    ref,
    () => ({
      scrollToRange(lineStart, colStart, lineEnd, colEnd) {
        const view = viewRef.current;
        if (!view) return;
        const doc = view.state.doc;
        if (lineStart < 1 || lineStart > doc.lines) return;
        const ls = doc.line(lineStart);
        const le = doc.line(Math.min(Math.max(lineEnd, lineStart), doc.lines));
        const fromRaw = Math.min(ls.from + Math.max(colStart - 1, 0), ls.to);
        const toRaw = Math.min(le.from + Math.max(colEnd - 1, 0), le.to);
        const from = Math.min(fromRaw, toRaw);
        const to = Math.max(fromRaw, toRaw);
        view.dispatch({
          effects: [
            EditorView.scrollIntoView(from, { y: "center" }),
            setFlashEffect.of({ from, to: to > from ? to : from + 1 }),
          ],
        });
        if (flashTimerRef.current !== null) {
          window.clearTimeout(flashTimerRef.current);
        }
        flashTimerRef.current = window.setTimeout(() => {
          flashTimerRef.current = null;
          const v = viewRef.current;
          if (!v) return;
          v.dispatch({ effects: setFlashEffect.of(null) });
        }, 1000);
      },
    }),
    [],
  );

  return (
    <div className={styles.wrap}>
      <div ref={hostRef} className={styles.editor} />
      {!value && placeholder && <div className={styles.placeholder}>{placeholder}</div>}
    </div>
  );
});
