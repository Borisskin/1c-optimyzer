import { Diagnostic, linter } from "@codemirror/lint";
import { EditorView } from "@codemirror/view";
import { backend } from "@/api/backend";

const DEBOUNCE_MS = 500;

let pending: number | undefined;

interface ValidationError {
  message: string;
  phase?: string;
  line?: number;
  column?: number;
}

interface ValidationResult {
  ok: boolean;
  errors?: ValidationError[];
}

async function validateQuery(view: EditorView): Promise<Diagnostic[]> {
  const code = view.state.doc.toString().trim();
  if (!code) return [];

  let result: ValidationResult;
  try {
    result = await backend.validateOqlQuery(code);
  } catch (e) {
    return [
      {
        from: 0,
        to: view.state.doc.length,
        severity: "warning",
        message: `Не удалось проверить запрос: ${String(e)}`,
      },
    ];
  }

  if (result.ok) return [];

  const diagnostics: Diagnostic[] = [];
  for (const err of result.errors ?? []) {
    let from = 0;
    let to = view.state.doc.length;
    if (err.line != null && err.column != null) {
      try {
        const lineInfo = view.state.doc.line(err.line);
        from = Math.max(0, lineInfo.from + (err.column - 1));
        to = Math.min(view.state.doc.length, from + 8);
      } catch {
        // фолбэк на весь документ
      }
    }
    diagnostics.push({
      from,
      to,
      severity: "error",
      message: err.message,
    });
  }
  return diagnostics;
}

export const oqlLinter = linter(
  (view) =>
    new Promise<Diagnostic[]>((resolve) => {
      if (pending !== undefined) window.clearTimeout(pending);
      pending = window.setTimeout(() => {
        pending = undefined;
        validateQuery(view).then(resolve);
      }, DEBOUNCE_MS);
    }),
);
