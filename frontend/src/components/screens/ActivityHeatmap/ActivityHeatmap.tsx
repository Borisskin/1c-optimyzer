import type { CSSProperties } from "react";
import { useMemo, useState } from "react";
import { backend } from "@/api/backend";
import { HeatmapChart } from "@/components/charts";
import type { HeatmapCell } from "@/components/charts";
import { ViewShell } from "@/components/views/ViewShell";
import { colIndex, useView } from "@/components/views/useView";
import { filtersToDto, useAppStore } from "@/store/appStore";
import vshellStyles from "@/components/views/ViewShell.module.css";

type Metric = "count" | "total_duration_ms" | "peak_duration_ms" | "error_count";

interface Props {
  archiveId: string | null;
}

export function ActivityHeatmapScreen({ archiveId }: Props) {
  const filters = useAppStore((s) => s.filters);
  const setFilters = useAppStore((s) => s.setFilters);
  const [metric, setMetric] = useState<Metric>("count");

  const { data, loading, error } = useView(
    () =>
      archiveId
        ? backend.viewActivityHeatmap(archiveId, filtersToDto(filters), metric)
        : Promise.resolve({ ok: true, columns: [], rows: [], row_count: 0 }),
    [archiveId, filters, metric],
  );

  const cells: HeatmapCell[] = useMemo(() => {
    if (!data?.rows) return [];
    const idx = colIndex(data.columns);
    return data.rows.map((r) => ({
      x: Number(r[idx["x"]] ?? 0),
      y: Number(r[idx["y"]] ?? 0),
      value: Number(r[idx["value"]] ?? 0),
    }));
  }, [data]);

  return (
    <ViewShell
      breadcrumbs={["Анализ", "Активность"]}
      title={<>Активность</>}
      sub="Тепловая карта events по часам и дням недели"
      right={
        <select
          value={metric}
          onChange={(e) => setMetric(e.target.value as Metric)}
          style={selectStyle}
        >
          <option value="count">Количество событий</option>
          <option value="total_duration_ms">Σ длительность</option>
          <option value="peak_duration_ms">Пик длительности</option>
          <option value="error_count">Количество ошибок</option>
        </select>
      }
    >
      <div className={vshellStyles.panel}>
        {!archiveId && <div className={vshellStyles.empty}>Загрузите архив</div>}
        {archiveId && error && <div className={vshellStyles.error}>{error}</div>}
        {archiveId && !error && (
          <HeatmapChart
            data={cells}
            height={320}
            isLoading={loading}
            emptyMessage="Нет событий за период"
            formatValue={(v) =>
              metric === "total_duration_ms" || metric === "peak_duration_ms"
                ? (v / 1000).toFixed(1) + " с"
                : v.toLocaleString("ru-RU")
            }
            onCellClick={(cell) => {
              // Cross-filter: устанавливаем time range на выбранный час.
              // Без знания даты архива используем "сегодня" как маркер;
              // для real-data backend проигнорирует out-of-range cells.
              const today = new Date();
              const dayOffset = cell.y; // 0 = Mon, 1 = Tue, ...
              const monday = new Date(today);
              monday.setDate(today.getDate() - ((today.getDay() + 6) % 7));
              monday.setHours(0, 0, 0, 0);
              const start = new Date(monday);
              start.setDate(monday.getDate() + dayOffset);
              start.setHours(cell.x, 0, 0, 0);
              const end = new Date(start);
              end.setHours(start.getHours() + 1);
              setFilters({
                time_from: start.toISOString(),
                time_to: end.toISOString(),
                source_view: "activity",
              });
            }}
          />
        )}
      </div>
    </ViewShell>
  );
}

const selectStyle: CSSProperties = {
  height: 28,
  padding: "0 8px",
  fontSize: 11.5,
  border: "1px solid var(--o-border-2)",
  borderRadius: 4,
  background: "var(--o-panel)",
  color: "var(--o-text-1)",
};
