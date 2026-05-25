/**
 * Sprint 7 Phase D — импорт плана запроса из загруженного архива ТЖ.
 *
 * Flow:
 *   1. Mount → backend.planAnalyzerListTjPlans(archive_id) → list событий
 *   2. Юзер кликает строку → backend.planAnalyzerGetTjPlan(archive_id, event_id)
 *      → передаём sql_text + plan_text родителю через onPick
 *   3. Родитель показывает PlanTextView (D.6) + AI explanation
 *
 * Edge cases:
 *   - Нет архива в appStore → empty state «Загрузите архив ТЖ через TopBar»
 *   - Архив есть, но has_planSQLText=false → banner с инструкцией по <plan/>
 *   - Архив есть, has_planSQLText=true, items пустой (фильтр? offset?) → empty hint
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { backend, type PlanAnalyzerTjItem, type PlanEngine } from "@/api/backend";
import { useAppStore } from "@/store/appStore";
import { Icon } from "@/components/icons/Icon";
import styles from "./PlanTjImport.module.css";

interface Props {
  /** Колбек когда юзер выбрал план — родитель сам делает analyze + render. */
  onPick: (payload: {
    event_id: number;
    sql_text: string;
    plan_text: string;
    ts: string | null;
    duration_us: number | null;
    context: string | null;
    engine?: PlanEngine | null;
  }) => void;
  busy: boolean;
}

// Sprint 8 Phase B — filter toggle для смешанных архивов MSSQL+PG.
type EngineFilter = "all" | "mssql" | "postgres";

export function PlanTjImport({ onPick, busy }: Props) {
  const archive = useAppStore((s) => s.archive);
  const [items, setItems] = useState<PlanAnalyzerTjItem[] | null>(null);
  const [total, setTotal] = useState(0);
  const [countsByEngine, setCountsByEngine] = useState<Partial<Record<string, number>>>({});
  const [hasPlans, setHasPlans] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pickingId, setPickingId] = useState<number | null>(null);
  // Sprint 8 Phase B — фильтр по engine для mixed архивов.
  const [engineFilter, setEngineFilter] = useState<EngineFilter>("all");
  // Auto-collapse: после выбора плана список сворачивается в bar, оставляя
  // место для plan view внизу. Юзер кликает «Сменить» → bar исчезает,
  // полный список возвращается. Без этого список 200 строк занимал
  // полэкрана и сам план почти не было видно.
  const [selectedItem, setSelectedItem] = useState<PlanAnalyzerTjItem | null>(null);

  const archiveId = archive?.archive_id ?? null;

  // Re-load list когда меняется активный архив или engine filter.
  useEffect(() => {
    if (!archiveId) {
      setItems(null);
      setHasPlans(null);
      setError(null);
      setSelectedItem(null);  // archive switched → сбрасываем selection
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    const engine = engineFilter === "all" ? undefined : engineFilter;
    backend
      .planAnalyzerListTjPlans(archiveId, 200, 0, engine)
      .then((resp) => {
        if (cancelled) return;
        if (!resp.ok) {
          setError(resp.details ?? resp.error ?? "Ошибка загрузки планов");
          setItems(null);
          setHasPlans(null);
          return;
        }
        setItems(resp.items ?? []);
        setTotal(resp.total ?? 0);
        setHasPlans(resp.has_planSQLText ?? false);
        setCountsByEngine(resp.counts_by_engine ?? {});
      })
      .catch((e) => {
        if (cancelled) return;
        setError(String(e));
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [archiveId, engineFilter]);

  const onClickRow = useCallback(
    async (item: PlanAnalyzerTjItem) => {
      if (!archiveId || busy || pickingId !== null) return;
      setPickingId(item.event_id);
      setError(null);
      try {
        const resp = await backend.planAnalyzerGetTjPlan(archiveId, item.event_id);
        if (!resp.ok) {
          setError(resp.details ?? resp.error ?? "Ошибка получения плана");
          return;
        }
        onPick({
          event_id: resp.event_id ?? item.event_id,
          sql_text: resp.sql_text ?? "",
          plan_text: resp.plan_text ?? "",
          ts: resp.ts ?? null,
          duration_us: resp.duration_us ?? null,
          context: resp.context ?? null,
          engine: resp.engine ?? item.engine ?? null,
        });
        // Auto-collapse — после успешного импорта сворачиваем список в bar
        setSelectedItem(item);
      } catch (e) {
        setError(String(e));
      } finally {
        setPickingId(null);
      }
    },
    [archiveId, busy, pickingId, onPick],
  );

  // Sprint 8 Phase B — показываем filter toggle только если есть оба engine
  // в архиве. Если только один — toggle бесполезен.
  const hasBothEngines = useMemo(() => {
    const m = countsByEngine.mssql ?? 0;
    const p = countsByEngine.postgres ?? 0;
    return m > 0 && p > 0;
  }, [countsByEngine]);

  // Сортировка по длительности — самые медленные первыми.
  // duration_us = null ставим в конец.
  const sortedItems = useMemo(() => {
    if (!items) return items;
    return [...items].sort(
      (a, b) => (b.duration_us ?? -1) - (a.duration_us ?? -1),
    );
  }, [items]);

  // === Render: нет архива ===
  if (!archiveId) {
    return (
      <div className={styles.empty}>
        <Icon name="Inbox" size={28} color="var(--o-text-mute)" />
        <div className={styles.emptyTitle}>Архив ТЖ не загружен</div>
        <div className={styles.emptyHint}>
          Загрузите архив через TopBar (кнопка слева вверху), затем вернитесь сюда —
          планы запросов из DBMSSQL событий появятся автоматически.
        </div>
      </div>
    );
  }

  // === Render: ошибка ===
  if (error) {
    return (
      <div className={styles.errorBox}>
        <div className={styles.errorTitle}>Не удалось загрузить планы</div>
        <div className={styles.errorDetail}>{error}</div>
      </div>
    );
  }

  // === Render: loading ===
  if (loading || items === null) {
    return <div className={styles.loading}>Загружаю список планов…</div>;
  }

  // === Render: архив есть, но <plan/> не настроен ===
  if (hasPlans === false) {
    return (
      <div className={styles.noPlansBanner}>
        <div className={styles.noPlansTitle}>В архиве нет планов запросов</div>
        <div className={styles.noPlansHint}>
          DBMSSQL события в этом архиве не содержат поле{" "}
          <code className={styles.code}>planSQLText</code>. Чтобы планы появлялись,
          добавьте элемент <code className={styles.code}>&lt;plan/&gt;</code> в{" "}
          <code className={styles.code}>logcfg.xml</code> и перезапустите 1C Server
          Agent — подробности в файле{" "}
          <code className={styles.code}>docs/onboarding/enable-plansqltext.md</code>{" "}
          (или просто запустите скрипт{" "}
          <code className={styles.code}>scripts/patch-logcfg-for-plans.ps1</code>).
        </div>
        <div className={styles.noPlansHintSecondary}>
          После правки соберите новый архив ТЖ — старые архивы перепарсивать
          не нужно (там физически нет planSQLText в исходниках).
        </div>
      </div>
    );
  }

  // === Render: items пустые ===
  if (items.length === 0) {
    return (
      <div className={styles.empty}>
        <div className={styles.emptyTitle}>Нет DBMSSQL событий с планом</div>
        <div className={styles.emptyHint}>
          В архиве должны быть события — попробуйте перезагрузить или собрать
          архив за период когда были долгие SQL-запросы.
        </div>
      </div>
    );
  }

  // === Render: collapsed bar когда план уже выбран ===
  // Список 200 строк занимает полэкрана, не оставляя места для самого
  // плана внизу. После выбора показываем 1-строчный bar с info + кнопкой
  // «Сменить» которая возвращает полный список.
  if (selectedItem) {
    return (
      <div className={styles.collapsedBar}>
        <div className={styles.collapsedInfo}>
          <span className={styles.collapsedLabel}>Выбран:</span>
          <span className={styles.collapsedTs}>{formatTs(selectedItem.ts)}</span>
          <span className={styles.collapsedDuration}>
            {formatDuration(selectedItem.duration_us)}
          </span>
          <span className={styles.collapsedSql} title={selectedItem.sql_preview}>
            {selectedItem.sql_preview}
          </span>
        </div>
        <button
          type="button"
          className={styles.collapsedButton}
          onClick={() => setSelectedItem(null)}
        >
          Сменить план ({total})
        </button>
      </div>
    );
  }

  // === Render: список планов ===
  return (
    <div className={styles.listContainer}>
      <div className={styles.listHeader}>
        <span>
          Найдено планов: <strong>{total}</strong>
          {total > items.length && ` (показано ${items.length})`}
        </span>
        {/* Sprint 8 Phase B — engine filter toggle для mixed архивов. */}
        {hasBothEngines && (
          <div className={styles.engineFilter} role="group" aria-label="Фильтр по движку">
            <button
              type="button"
              className={`${styles.engineFilterBtn} ${engineFilter === "all" ? styles.engineFilterBtnActive : ""}`}
              onClick={() => setEngineFilter("all")}
            >
              Все ({(countsByEngine.mssql ?? 0) + (countsByEngine.postgres ?? 0)})
            </button>
            <button
              type="button"
              className={`${styles.engineFilterBtn} ${engineFilter === "mssql" ? styles.engineFilterBtnActive : ""}`}
              onClick={() => setEngineFilter("mssql")}
            >
              MSSQL ({countsByEngine.mssql ?? 0})
            </button>
            <button
              type="button"
              className={`${styles.engineFilterBtn} ${engineFilter === "postgres" ? styles.engineFilterBtnActive : ""}`}
              onClick={() => setEngineFilter("postgres")}
            >
              PostgreSQL ({countsByEngine.postgres ?? 0})
            </button>
          </div>
        )}
      </div>
      <div className={styles.list}>
        {(sortedItems ?? items).map((it) => (
          <button
            key={it.event_id}
            type="button"
            className={`${styles.row} ${pickingId === it.event_id ? styles.rowLoading : ""}`}
            onClick={() => onClickRow(it)}
            disabled={busy || pickingId !== null}
          >
            <div className={styles.rowMeta}>
              {/* Sprint 8 Phase B — engine badge (MSSQL / PG / неизв.). */}
              {it.engine && (
                <span
                  className={
                    it.engine === "postgres"
                      ? `${styles.engineBadge} ${styles.engineBadgePg}`
                      : `${styles.engineBadge} ${styles.engineBadgeMssql}`
                  }
                  title={it.engine === "postgres" ? "PostgreSQL plan" : "MS SQL Server plan"}
                >
                  {it.engine === "postgres" ? "PG" : "MSSQL"}
                </span>
              )}
              <span className={styles.rowTs}>{formatTs(it.ts)}</span>
              <span className={styles.rowDuration}>{formatDuration(it.duration_us)}</span>
              <span className={styles.rowPlanSize}>
                план: {formatBytes(it.plan_size_bytes)}
              </span>
              {it.context && <span className={styles.rowContext}>{it.context}</span>}
            </div>
            <div className={styles.rowSql}>{it.sql_preview}</div>
          </button>
        ))}
      </div>
    </div>
  );
}

// === Format helpers ===

function formatTs(ts: string | null): string {
  if (!ts) return "—";
  try {
    const d = new Date(ts);
    return d.toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return ts;
  }
}

function formatDuration(us: number | null): string {
  if (us === null || us === undefined) return "—";
  // 1С duration_us в microseconds (с поправкой как в storage). Делим на 1000 → мс.
  const ms = us / 1000;
  if (ms < 1) return `${us} мкс`;
  if (ms < 1000) return `${ms.toFixed(0)} мс`;
  return `${(ms / 1000).toFixed(2)} с`;
}

function formatBytes(b: number): string {
  if (b < 1024) return `${b} Б`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} КБ`;
  return `${(b / 1024 / 1024).toFixed(2)} МБ`;
}
