import { useQuery } from "@tanstack/react-query";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { apiUsage } from "@/api/endpoints";

const COLORS = ["#0ea5a4", "#22d3ee", "#a855f7", "#f97316", "#eab308"];

export function Usage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["usage", "summary"],
    queryFn: () => apiUsage.summary(),
  });

  const chartData = data
    ? Object.entries(data.ai_operations_by_type).map(([key, value]) => ({
        name: key.replace("ai_", "").replace(/_/g, " "),
        value,
      }))
    : [];

  return (
    <>
      <div className="page__head">
        <h1 className="page__title">Использование</h1>
        <p className="page__lead">
          AI-операции за текущий месяц с разбивкой по типам.
        </p>
      </div>

      {isLoading && <div className="loader">Загружаем…</div>}
      {error && <div className="error-banner">Не удалось загрузить статистику</div>}

      {data && (
        <>
          <div className="grid-cards">
            <div className="metric">
              <div className="metric__label">AI-операций</div>
              <div className="metric__value">{data.ai_operations_count}</div>
            </div>
            <div className="metric">
              <div className="metric__label">Free квота</div>
              <div className="metric__value">
                {data.free_quota_used} / {data.free_quota_limit}
              </div>
            </div>
            <div className="metric">
              <div className="metric__label">Кредитов потрачено</div>
              <div className="metric__value">{data.credits_used_this_period}</div>
            </div>
            <div className="metric">
              <div className="metric__label">Активных устройств</div>
              <div className="metric__value">{data.devices_seen_count}</div>
            </div>
          </div>

          <div className="card">
            <h2 className="card__title">По типам операций</h2>
            {chartData.length === 0 ? (
              <div className="empty">В этом месяце нет AI-операций.</div>
            ) : (
              <div style={{ width: "100%", height: 300 }}>
                <ResponsiveContainer>
                  <PieChart>
                    <Pie
                      data={chartData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      label={(entry) => entry.name}
                    >
                      {chartData.map((_, index) => (
                        <Cell key={index} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </>
      )}
    </>
  );
}
