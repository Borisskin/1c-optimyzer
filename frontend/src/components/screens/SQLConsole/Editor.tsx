import { useEffect, useRef } from "react";
import { EditorView, keymap } from "@codemirror/view";
import { EditorState, Prec } from "@codemirror/state";
import { basicSetup } from "codemirror";
import { makeSqlExtension, type SchemaShape } from "@/codemirror";

interface Props {
  value: string;
  onChange: (value: string) => void;
  onRun: () => void;
  schema: SchemaShape;
}

export function Editor({ value, onChange, onRun, schema }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const onChangeRef = useRef(onChange);
  const onRunRef = useRef(onRun);

  onChangeRef.current = onChange;
  onRunRef.current = onRun;

  // schema-key позволяет dispose-and-recreate EditorView при смене архива
  // (когда autocomplete должен показывать другой набор колонок).
  const schemaKey = Object.keys(schema)
    .map((t) => `${t}:${schema[t].length}`)
    .join("|");

  useEffect(() => {
    if (!containerRef.current) return;

    const state = EditorState.create({
      doc: value,
      extensions: [
        basicSetup,
        makeSqlExtension(schema),
        Prec.highest(
          keymap.of([
            {
              key: "Ctrl-Enter",
              mac: "Cmd-Enter",
              run: () => {
                onRunRef.current();
                return true;
              },
            },
          ]),
        ),
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            onChangeRef.current(update.state.doc.toString());
          }
        }),
      ],
    });

    const view = new EditorView({ state, parent: containerRef.current });
    viewRef.current = view;
    return () => {
      view.destroy();
      viewRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [schemaKey]);

  // Внешние изменения (templates load, saved queries) синхронизируем в editor.
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

  return (
    <div
      ref={containerRef}
      style={{ flex: "1 1 0", minHeight: 0, width: "100%", overflow: "auto" }}
    />
  );
}
