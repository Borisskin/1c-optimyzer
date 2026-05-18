import { useMemo } from "react";
import { backend } from "@/api/backend";
import { LineChart } from "@/components/charts";
import { ViewShell } from "@/components/views/ViewShell";
import { colIndex, useView } from "@/components/views/useView";
import { filtersToDto, useAppStore } from "@/store/appStore";
import vshellStyles from "@/components/views/ViewShell.module.css";

interface Props {
  archiveId: string | null;
}

export function LocksTimelineScreen({ archiveId }: Props) {
  const filters = useAppStore((s) => s.filters);
  const { data, loading, error } = useView(
    () =>
      archiveId
        ? backend.viewLocksTimeline(archiveId, filtersToDto(filters))
        : Promise.resolve({ ok: true, columns: [], rows: [], row_count: 0 }),
    [archiveId, filters],
  );

  const series = useMemo(() => {
    if (!data?.rows) return [];
    const idx = colIndex(data.columns);
    return data.rows.map((row) => ({
      bucket: formatTs(row[idx["bucket"]]),
      locks: Number(row[idx["locks"]] ?? 0),
      deadlocks: Number(row[idx["deadlocks"]] ?? 0),
    }));
  }, [data]);

  const totalLocks = series.reduce((acc, s) => acc + s.locks, 0);
  const totalDeadlocks = series.reduce((acc, s) => acc + s.deadlocks, 0);

  return (
    <ViewShell
      breadcrumbs={["Анализ", "Блокировки"]}
      title={<>Блокировки</>}
      sub={`Распределение TLOCK и TDEADLOCK по времени (bucket: ${data?.bucket ?? "—"})`}
    >
      <div className={vshellStyles.panel}>
        <div className={vshellStyles.panel_head}>
          <div className={vshellStyles.panel_title}>
            {totalLocks.toLocaleString("ru-RU")} locks · {totalDeadlocks.toLocaleString("ru-RU")} deadlocks
          </div>
        </div>
        {!archiveId && <div className={vshellStyles.empty}>Загрузите архив, чтобы увидеть блокировки</div>}
        {archiveId && error && <div className={vshellStyles.error}>{error}</div>}
        {archiveId && !error && (
          <LineChart
            data={series}
            xKey="bucket"
            series={[
              { key: "locks", label: "Locks", color: "#0F766E" },
              { key: "deadlocks", label: "Deadlocks", color: "#DC2626" },
            ]}
            height={280}
            isLoading={loading}
            emptyMessage="Нет блокировок"
          />
        )}
      </div>
    </ViewShell>
  );
}

function formatTs(v: unknown): string {
  if (v == null) return "—";
  const s = String(v);
  // ISO -> 'YYYY-MM-DD HH:MM' (без секунд)
  return s.length >= 16 ? s.slice(0, 16).replace("T", " ") : s;
}
