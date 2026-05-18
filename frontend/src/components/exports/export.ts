// CSV / JSON / TSV экспорт результатов view (Sprint 2 Phase H).
// XLSX отложен — добавится через openpyxl-аналог в JS отдельным треком,
// если повсеместный CSV / TSV не покрывает запрос пользователей.

import { save } from "@tauri-apps/plugin-dialog";
import { writeTextFile } from "@tauri-apps/plugin-fs";

export interface ExportColumn {
  name: string;
}

export type ExportFormat = "csv" | "tsv" | "json";

export async function exportRows(
  defaultName: string,
  format: ExportFormat,
  columns: ExportColumn[],
  rows: unknown[][],
): Promise<{ saved: boolean; path?: string }> {
  const ext = format;
  const path = await save({
    filters: [{ name: format.toUpperCase(), extensions: [ext] }],
    defaultPath: `${defaultName}.${ext}`,
  });
  if (!path) return { saved: false };

  let content: string;
  if (format === "json") {
    content = JSON.stringify(
      {
        columns: columns.map((c) => c.name),
        rows,
        exported_at: new Date().toISOString(),
      },
      null,
      2,
    );
  } else {
    const sep = format === "tsv" ? "\t" : ",";
    const header = columns.map((c) => csvCell(c.name, sep)).join(sep);
    const body = rows.map((row) => row.map((v) => csvCell(v, sep)).join(sep)).join("\n");
    content = `${header}\n${body}`;
  }
  await writeTextFile(path, content);
  return { saved: true, path };
}

function csvCell(v: unknown, sep: string): string {
  if (v == null) return "";
  let s: string;
  if (typeof v === "string") s = v;
  else if (typeof v === "number" || typeof v === "boolean") s = String(v);
  else s = JSON.stringify(v);
  if (s.includes(sep) || s.includes('"') || s.includes("\n") || s.includes("\r")) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}
