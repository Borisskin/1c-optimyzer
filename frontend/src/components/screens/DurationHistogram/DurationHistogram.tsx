import { useMemo } from "react";
import { backend } from "@/api/backend";
import { HistogramChart } from "@/components/charts";
import { ViewShell } from "@/components/views/ViewShell";
import { colIndex, useView } from "@/components/views/useView";
import { filtersToDto, useAppStore } from "@/store/appStore";
import vshellStyles from "@/components/views/ViewShell.module.css";

interface Props {
  archiveId: string | null;
}

export function DurationHistogramScreen({ archiveId }: Props) {
  const filters = useAppStore((s) => s.filters);
  const { data, loading, error } = useView(
    () =>
      archiveId
        ? backend.viewDurationHistogram(archiveId, filtersToDto(filters))
        : Promise.resolve({ ok: true, columns: [], rows: [], row_count: 0 }),
    [archiveId, filters],
  );

  const buckets = useMemo(() => {
    if (!data?.rows) return [];
    const idx = colIndex(data.columns);
    return data.rows.map((r) => ({
      label: String(r[idx["label"]] ?? ""),
      count: Number(r[idx["count"]] ?? 0),
      percent: Number(r[idx["percent"]] ?? 0),
    }));
  }, [data]);

  const total = buckets.reduce((acc, b) => acc + b.count, 0);

  return (
    <ViewShell
      breadcrumbs={["Анализ", "Распределение длительностей"]}
      title={<>Распределение длительностей</>}
      sub="Гистограмма events по бакетам длительности (логарифмическая Y-шкала)"
    >
      <div className={vshellStyles.panel}>
        <div className={vshellStyles.panel_head}>
          <div className={vshellStyles.panel_title}>{total.toLocaleString("ru-RU")} событий</div>
        </div>
        {!archiveId && <div className={vshellStyles.empty}>Загрузите архив</div>}
        {archiveId && error && <div className={vshellStyles.error}>{error}</div>}
        {archiveId && !error && (
          <HistogramChart
            data={buckets}
            height={300}
            logScale
            isLoading={loading}
            emptyMessage="Нет событий"
          />
        )}
        {archiveId && !loading && !error && total > 0 && (
          <div className={vshellStyles.table_wrap}>
            <table className={vshellStyles.table}>
              <thead>
                <tr>
                  <th>Bucket</th>
                  <th>Count</th>
                  <th>%</th>
                </tr>
              </thead>
              <tbody>
                {buckets.map((b) => (
                  <tr key={b.label}>
                    <td>{b.label}</td>
                    <td className={vshellStyles.mono}>{b.count.toLocaleString("ru-RU")}</td>
                    <td className={vshellStyles.mono}>{b.percent.toFixed(2)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </ViewShell>
  );
}
