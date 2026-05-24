import type { CSSProperties } from "react";
import { Fragment, useMemo, useState } from "react";
import { backend } from "@/api/backend";
import { ExportMenu } from "@/components/exports/ExportMenu";
import { ViewShell } from "@/components/views/ViewShell";
import { colIndex, useView } from "@/components/views/useView";
import { useStickyTableHead } from "@/components/views/useStickyTableHead";
import { useTableState } from "@/components/tables/useTableState";
import { TableFilter } from "@/components/tables/TableFilter";
import { EventTypeFilter } from "@/components/tables/EventTypeFilter";
import { ContextFilter, type ContextPresenceFilter } from "@/components/tables/ContextFilter";
import { LimitSelector } from "@/components/tables/LimitSelector";
import { filtersToDto, useAppStore } from "@/store/appStore";
import { EmptyArchiveHint } from "@/components/views/EmptyArchiveHint";
import vshellStyles from "@/components/views/ViewShell.module.css";

interface Props {
  archiveId: string | null;
}

export function ErrorsFeedScreen({ archiveId }: Props) {
  const filters = useAppStore((s) => s.filters);
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());
  // По умолчанию «есть контекст» — обычно интересны именно бизнес-операции
  // с контекстом, а не безконтекстный системный трафик 1С. Юзер всегда может
  // переключить на «все» или «нет» через ContextFilter в шапке таблицы.
  const [contextPresence, setContextPresence] = useState<ContextPresenceFilter>("with");
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [limit, setLimit] = useState(500);
  // Фильтр по event_type — server-side. Это критично: при limit=10000 редкий
  // тип (например, 1 TLOCK в архиве из 100K) может полностью выпасть из top-N
  // по ts DESC, если расположен в начале архива. Передаём selectedTypes в RPC.
  const selectedTypesArr = useMemo(() => [...selectedTypes], [selectedTypes]);
  // Фильтр по наличию context — тоже server-side. Без этого «есть» при
  // limit=500 часто давал пусто: первые 500 ts DESC — обычно SCALL/CALL
  // без контекста, а DBMSSQL с контекстом сидит дальше по архиву.
  const contextPresenceParam: "with" | "without" | undefined =
    contextPresence === "any" ? undefined : contextPresence;
  const { data, loading, error } = useView(
    () =>
      archiveId
        ? backend.viewErrorsFeed(
            archiveId,
            filtersToDto(filters),
            limit,
            selectedTypesArr,
            contextPresenceParam,
          )
        : Promise.resolve({ ok: true, columns: [], rows: [], row_count: 0 }),
    [archiveId, filters, limit, selectedTypesArr.join("|"), contextPresenceParam],
  );

  const idx = useMemo(() => colIndex(data?.columns), [data?.columns]);

  // Список всех типов в архиве (counts — независимо от selectedTypes, чтобы
  // юзер мог переключать выбор без потери видимых counts). Сортировка
  // severity-based: ошибки → блокировки → запросы/звонки → служебные.
  const availableTypes = useMemo(() => {
    const raw = data?.event_types ?? [];
    const order = ["EXCP", "EXCPCNTX", "TDEADLOCK", "TLOCK", "DBMSSQL", "CALL", "SCALL", "Context"];
    return [...raw]
      .map(([value, count]) => ({ value, count }))
      .sort((a, b) => {
        const ia = order.indexOf(a.value);
        const ib = order.indexOf(b.value);
        if (ia !== -1 && ib !== -1) return ia - ib;
        if (ia !== -1) return -1;
        if (ib !== -1) return 1;
        return a.value.localeCompare(b.value);
      });
  }, [data?.event_types]);

  // Индекс колонки context — нужен только для условного показа ContextFilter
  // (если бэкенд по какой-то причине не вернул колонку — фильтр скрываем).
  // Сама фильтрация теперь server-side (см. contextPresenceParam выше).
  const ctxIdx = useMemo(() => {
    const cols = data?.columns ?? [];
    return cols.findIndex((c) => c.name === "context");
  }, [data?.columns]);

  // useTableState — substring filter + sort внутри уже отфильтрованных бэком
  // строк. Client-side фильтр по контексту убран (был у первых 500 загруженных
  // строк, что давало пусто на real-data — DBMSSQL с контекстом могут быть
  // за пределами top-500 по ts DESC).
  const table = useTableState({
    rows: data?.rows ?? [],
    columns: data?.columns ?? [],
    defaultSortKey: "ts",
    defaultSortDir: "desc",
  });

  const typesSummary =
    selectedTypes.size === 0
      ? availableTypes.length > 0
        ? availableTypes.map((t) => t.value).join(" / ")
        : "все типы"
      : [...selectedTypes].join(" / ");

  const { panelHeadRef, panelStyle } = useStickyTableHead<HTMLDivElement>();

  return (
    <ViewShell
      breadcrumbs={["Анализ", "События ТЖ"]}
      title={<>События ТЖ</>}
      sub={`${typesSummary} — последние сначала`}
      right={
        <ExportMenu
          defaultName="errors_feed"
          columns={data?.columns ?? []}
          rows={table.rows}
        />
      }
    >
      <div className={vshellStyles.panel} style={panelStyle}>
        <div ref={panelHeadRef} className={vshellStyles.panel_head}>
          <LimitSelector
            value={limit}
            onChange={setLimit}
            loaded={data?.rows?.length ?? 0}
            total={data?.total_rows ?? null}
            unitLabel="событий"
          />
          {data && (
            <div className={vshellStyles.panel_sub}>
              за {(data.executed_ms ?? 0).toFixed(0)} мс
            </div>
          )}
          <div style={toolsGroup}>
            {availableTypes.length > 0 && (
              <EventTypeFilter
                options={availableTypes}
                selected={selectedTypes}
                onChange={setSelectedTypes}
              />
            )}
            {ctxIdx >= 0 && (data?.rows?.length ?? 0) > 0 && (
              <ContextFilter
                value={contextPresence}
                onChange={setContextPresence}
              />
            )}
            {(data?.rows?.length ?? 0) > 0 && (
              <TableFilter
                value={table.filter}
                onChange={table.setFilter}
                total={table.totalRows}
                visible={table.visibleRows}
                placeholder="Поиск по контексту, PID…"
              />
            )}
          </div>
        </div>
        {!archiveId && <EmptyArchiveHint what="чтобы увидеть события ТЖ" />}
        {archiveId && loading && <div className={vshellStyles.loading}>Загрузка…</div>}
        {archiveId && error && <div className={vshellStyles.error}>{error}</div>}
        {archiveId && !loading && !error && table.rows.length > 0 && (
          <div className={vshellStyles.table_wrap}>
            <table className={vshellStyles.table}>
              <thead>
                <tr>
                  <th {...table.headerProps("ts")}>Время</th>
                  <th {...table.headerProps("event_type")}>Тип</th>
                  <th {...table.headerProps("process_role")}>Роль</th>
                  <th {...table.headerProps("process_pid")}>PID</th>
                  <th {...table.headerProps("context")}>Контекст</th>
                  <th {...table.headerProps("duration_ms")}>ms</th>
                </tr>
              </thead>
              <tbody>
                {table.rows.map((row, ri) => {
                  const tone = badgeTone(String(row[idx["event_type"]] ?? ""));
                  const context = String(row[idx["context"]] ?? "");
                  const isExpanded = expanded.has(ri);
                  const toggle = () => {
                    setExpanded((prev) => {
                      const next = new Set(prev);
                      if (next.has(ri)) next.delete(ri);
                      else next.add(ri);
                      return next;
                    });
                  };
                  return (
                    <Fragment key={ri}>
                      <tr
                        className={`${vshellStyles.clickable}`}
                        onClick={toggle}
                      >
                        <td className={vshellStyles.mono} style={nowrapCell}>
                          {formatTs(row[idx["ts"]])}
                        </td>
                        <td style={nowrapCell}>
                          <span style={badgeStyle(tone)}>{String(row[idx["event_type"]] ?? "")}</span>
                        </td>
                        <td style={nowrapCell}>{String(row[idx["process_role"]] ?? "—")}</td>
                        <td className={vshellStyles.mono} style={nowrapCell}>
                          {String(row[idx["process_pid"]] ?? "—")}
                        </td>
                        <td style={contextCellStyle}>
                          <span style={contextTextStyle(isExpanded)}>{context || "—"}</span>
                        </td>
                        <td className={vshellStyles.mono} style={nowrapCell}>
                          {fmtMs(row[idx["duration_ms"]])}
                        </td>
                      </tr>
                      {isExpanded && context && (
                        <tr className={vshellStyles.expandRow}>
                          <td colSpan={6} style={expandedCellStyle}>
                            <pre style={expandedPreStyle}>{context}</pre>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {archiveId && !loading && !error && (!data?.rows || data.rows.length === 0) && (
          <div className={vshellStyles.empty}>
            {contextPresence === "with"
              ? "В архиве нет ни одного события с заполненным контекстом" +
                (selectedTypes.size > 0 ? ` (среди типов: ${[...selectedTypes].join(", ")})` : "")
              : contextPresence === "without"
                ? "В архиве нет ни одного события без контекста" +
                  (selectedTypes.size > 0 ? ` (среди типов: ${[...selectedTypes].join(", ")})` : "")
                : selectedTypes.size > 0
                  ? `Нет событий выбранных типов (${[...selectedTypes].join(", ")})`
                  : "Нет событий в архиве"}
          </div>
        )}
        {archiveId && !loading && !error && (data?.rows?.length ?? 0) > 0 && table.rows.length === 0 && (
          <div className={vshellStyles.empty}>
            {table.filter
              ? `Фильтр «${table.filter}» не дал совпадений`
              : "Нет совпадений"}
          </div>
        )}
      </div>
    </ViewShell>
  );
}

const toolsGroup: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 10,
  marginLeft: "auto",
};

function badgeTone(type: string): "err" | "warn" | "mute" {
  if (type === "EXCP" || type === "TDEADLOCK") return "err";
  if (type === "TLOCK") return "warn";
  return "mute";
}

function badgeStyle(tone: "err" | "warn" | "mute"): CSSProperties {
  const bg = tone === "err" ? "rgba(220,38,38,0.1)" : tone === "warn" ? "rgba(245,158,11,0.1)" : "var(--o-subtle)";
  const fg = tone === "err" ? "#DC2626" : tone === "warn" ? "#B45309" : "var(--o-text-3)";
  return {
    display: "inline-block",
    padding: "2px 8px",
    borderRadius: 3,
    fontSize: 10.5,
    fontFamily: "var(--o-font-mono)",
    background: bg,
    color: fg,
  };
}

function formatTs(v: unknown): string {
  if (v == null) return "—";
  const s = String(v);
  return s.length >= 19 ? s.slice(0, 19).replace("T", " ") : s;
}

function fmtMs(v: unknown): string {
  if (v == null || typeof v !== "number") return "—";
  if (v >= 1000) return (v / 1000).toFixed(2) + " с";
  return v.toFixed(1);
}

// Колонка контекста — единственная без nowrap; забирает остаток ширины
// после того, как короткие колонки (ts/type/role/pid/ms) заняли свой
// natural width.
const contextCellStyle: CSSProperties = {
  maxWidth: 0,
  width: "100%",
  overflow: "hidden",
};

const nowrapCell: CSSProperties = {
  whiteSpace: "nowrap",
};

function contextTextStyle(expanded: boolean): CSSProperties {
  if (expanded) {
    return {
      display: "block",
      whiteSpace: "normal",
      wordBreak: "break-word",
      color: "var(--o-text-1)",
    };
  }
  return {
    display: "block",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    color: "var(--o-text-2)",
  };
}

const expandedCellStyle: CSSProperties = {
  background: "var(--o-codebox-bg)",
  borderBottom: "1px solid var(--o-border-2)",
  padding: "12px 14px",
};

const expandedPreStyle: CSSProperties = {
  margin: 0,
  fontFamily: "var(--o-font-mono)",
  fontSize: 11.5,
  lineHeight: 1.55,
  color: "var(--o-text-1)",
  whiteSpace: "pre-wrap",
  wordBreak: "break-word",
};
