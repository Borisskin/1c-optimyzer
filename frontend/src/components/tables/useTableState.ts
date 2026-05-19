/**
 * Hook для sortable + filterable табличных данных.
 *
 * Использование:
 *   const { rows, filter, setFilter, sortKey, sortDir, headerProps } =
 *     useTableState({ rows: data?.rows ?? [], columns: data?.columns ?? [] });
 *
 *   <TableFilter value={filter} onChange={setFilter} />
 *   <thead><tr>
 *     {columns.map(c => <th {...headerProps(c.name)}>{c.name}</th>)}
 *   </tr></thead>
 *   <tbody>{rows.map(...)}</tbody>
 *
 * Поведение:
 *   - Sort: 2-state toggle ASC ↔ DESC. Первый клик по колонке = ASC.
 *     Stable sort — для равных значений сохраняется исходный индекс.
 *   - Filter: substring case-insensitive по всем колонкам.
 *   - Ephemeral state — не persist между mount/unmount.
 */

import { useMemo, useState, useCallback } from "react";

export interface TableColumn {
  name: string;
  type?: string;
}

export type SortDir = "asc" | "desc";

export interface UseTableStateOptions {
  rows: unknown[][];
  columns: TableColumn[];
  /** Имя колонки для дефолтной сортировки (например, "duration_us"). Если не задано — порядок исходный. */
  defaultSortKey?: string;
  defaultSortDir?: SortDir;
}

export interface HeaderProps {
  onClick: () => void;
  className: string;
  "aria-sort": "ascending" | "descending" | "none";
  title: string;
  tabIndex: number;
  onKeyDown: (e: React.KeyboardEvent) => void;
  role: "button";
}

export interface UseTableStateResult {
  rows: unknown[][];
  filter: string;
  setFilter: (v: string) => void;
  sortKey: string | null;
  sortDir: SortDir;
  setSort: (key: string, dir?: SortDir) => void;
  headerProps: (columnName: string) => HeaderProps;
  /** Сравнение — сколько строк всего vs после фильтрации. Для UI типа "12 / 100". */
  totalRows: number;
  visibleRows: number;
}

export function useTableState({
  rows,
  columns,
  defaultSortKey,
  defaultSortDir = "desc",
}: UseTableStateOptions): UseTableStateResult {
  const [filter, setFilter] = useState("");
  const [sortKey, setSortKey] = useState<string | null>(defaultSortKey ?? null);
  const [sortDir, setSortDir] = useState<SortDir>(defaultSortDir);

  const colIndex = useMemo(() => {
    const m: Record<string, number> = {};
    columns.forEach((c, i) => (m[c.name] = i));
    return m;
  }, [columns]);

  // Фильтрация
  const filtered = useMemo(() => {
    if (!filter.trim()) return rows;
    const needle = filter.toLowerCase();
    return rows.filter((row) =>
      row.some((cell) => {
        if (cell == null) return false;
        return String(cell).toLowerCase().includes(needle);
      }),
    );
  }, [rows, filter]);

  // Сортировка (stable)
  const sorted = useMemo(() => {
    if (!sortKey || !(sortKey in colIndex)) return filtered;
    const idx = colIndex[sortKey];
    // map to indexed pairs для stable sort
    const indexed = filtered.map((row, i) => ({ row, i }));
    indexed.sort((a, b) => {
      const va = a.row[idx];
      const vb = b.row[idx];
      const cmp = compareValues(va, vb);
      if (cmp !== 0) return sortDir === "asc" ? cmp : -cmp;
      return a.i - b.i; // stable
    });
    return indexed.map((p) => p.row);
  }, [filtered, sortKey, sortDir, colIndex]);

  const setSort = useCallback((key: string, dir?: SortDir) => {
    setSortKey(key);
    if (dir) setSortDir(dir);
  }, []);

  const headerProps = useCallback(
    (columnName: string): HeaderProps => {
      const active = sortKey === columnName;
      const onClick = () => {
        if (active) {
          setSortDir((d) => (d === "asc" ? "desc" : "asc"));
        } else {
          setSortKey(columnName);
          setSortDir("asc");
        }
      };
      const ariaSort: HeaderProps["aria-sort"] = active
        ? sortDir === "asc"
          ? "ascending"
          : "descending"
        : "none";
      const className = active
        ? `th_sortable th_sortable_active th_sortable_${sortDir}`
        : "th_sortable";
      return {
        onClick,
        className,
        "aria-sort": ariaSort,
        title: active
          ? `Сортировка ${sortDir === "asc" ? "↑" : "↓"} — клик переключит направление`
          : "Клик — отсортировать по этой колонке",
        tabIndex: 0,
        role: "button",
        onKeyDown: (e: React.KeyboardEvent) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onClick();
          }
        },
      };
    },
    [sortKey, sortDir],
  );

  return {
    rows: sorted,
    filter,
    setFilter,
    sortKey,
    sortDir,
    setSort,
    headerProps,
    totalRows: rows.length,
    visibleRows: sorted.length,
  };
}

// ---------- helpers ----------

function compareValues(a: unknown, b: unknown): number {
  // null/undefined идут в конец (для DESC — в начало через знак)
  if (a == null && b == null) return 0;
  if (a == null) return 1;
  if (b == null) return -1;

  // числа
  if (typeof a === "number" && typeof b === "number") return a - b;

  // boolean
  if (typeof a === "boolean" && typeof b === "boolean") {
    return a === b ? 0 : a ? 1 : -1;
  }

  // строки — попробуем как числа (например "1234.56" из JSON), иначе lexicographic
  const sa = String(a);
  const sb = String(b);
  const na = Number(sa);
  const nb = Number(sb);
  if (!Number.isNaN(na) && !Number.isNaN(nb) && sa.trim() !== "" && sb.trim() !== "") {
    return na - nb;
  }
  // ts-like ISO timestamps — string compare работает корректно
  return sa.localeCompare(sb, "ru-RU");
}
