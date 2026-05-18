// Общий fetch-hook для всех pre-built views.
// Возвращает {data, loading, error, refresh}; useEffect перезагружает при
// изменении archive_id или filters.

import { useCallback, useEffect, useRef, useState } from "react";
import type { ViewResult } from "@/api/backend";

export function useView(
  loader: () => Promise<ViewResult>,
  deps: ReadonlyArray<unknown>,
): {
  data: ViewResult | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
} {
  const [data, setData] = useState<ViewResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // bump увеличивается при ручном refresh — кладём в deps useEffect.
  const [bump, setBump] = useState(0);

  // Сохраняем последний loader в ref, чтобы deps useEffect не зависел от
  // identity-ссылки loader (caller передаёт new arrow function каждый render).
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    loaderRef
      .current()
      .then((r) => {
        if (cancelled) return;
        if (!r.ok) {
          setError(r.error ?? "Ошибка");
          setData(null);
        } else {
          setData(r);
        }
      })
      .catch((e) => {
        if (cancelled) return;
        setError(String(e));
        setData(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, bump]);

  const refresh = useCallback(() => setBump((b) => b + 1), []);
  return { data, loading, error, refresh };
}

/** Вспомогалка: построить map имени → индекса колонки. */
export function colIndex(columns: { name: string }[] | undefined): Record<string, number> {
  const out: Record<string, number> = {};
  if (!columns) return out;
  for (let i = 0; i < columns.length; i++) out[columns[i].name] = i;
  return out;
}
