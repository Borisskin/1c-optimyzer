/* SCREEN 9: Predictive Performance */
function PredictiveScreen() {
  return (
    <div>
      <PageHeader breadcrumbs={['Configuration','Predictive']} title="Predictive Performance"
        sub="capacity forecast · ML anomaly detection · release impact"
        kpis={<>
          <KPI label="ANOMALY SCORE" value="0.34" sub="threshold 0.70 · normal" tone="ok"/>
          <KPI label="ML MODELS" value="14" sub="auto-trained per signal"/>
          <KPI label="PREDICTIONS / 7D" value="38" sub="29 confirmed · 9 false positive"/>
          <KPI label="NEXT FORECAST AT" value="03:00" sub="daily retrain"/>
        </>}/>

      <div className="grid grid-cols-12 gap-3 p-3">
        {/* Capacity forecasting */}
        <Panel className="col-span-8" title="Capacity forecasting" sub="growth · 90-day projection">
          <ForecastChart/>
          <div className="mt-3 grid grid-cols-3 gap-3 text-[11.5px]">
            <div className="border hl2 rounded p-2.5">
              <div className="text-[10px] mono uppercase text-ink-400 tracking-wider">Table _AccumRgT5634</div>
              <div className="mono tnum font-semibold text-[16px] mt-0.5">2.34 M → 3.12 M</div>
              <div className="text-ink-500 text-[11px]">+33% in 90 days · ~8K rows/day</div>
            </div>
            <div className="border hl2 rounded p-2.5">
              <div className="text-[10px] mono uppercase text-ink-400 tracking-wider">Query p95</div>
              <div className="mono tnum font-semibold text-[16px] mt-0.5 text-warn">4.2 s → 5.4 s</div>
              <div className="text-ink-500 text-[11px]">linear correlation r = 0.94</div>
            </div>
            <div className="border hl2 rounded p-2.5">
              <div className="text-[10px] mono uppercase text-ink-400 tracking-wider">Storage</div>
              <div className="mono tnum font-semibold text-[16px] mt-0.5">412 GB → 548 GB</div>
              <div className="text-ink-500 text-[11px]">+136 GB · нужен план</div>
            </div>
          </div>
        </Panel>

        <Panel className="col-span-4" title={<span className="flex items-center gap-1.5"><I.AlertTriangle size={13} className="text-warn"/>Capacity alert</span>} sub="78 days ahead">
          <div className="bg-warn-bg border border-warn/20 rounded p-3">
            <div className="text-[12.5px] leading-relaxed">При текущем темпе роста таблицы <span className="mono">_AccumRgT5634</span> — <b>через ~78 дней</b> средний response time для запросов с этой таблицей превысит <b className="text-warn">5 секунд</b>.</div>
            <div className="mt-2 text-[11px] mono text-ink-500">trigger: p95(query_id=f3a2c1) &gt; 5000ms</div>
          </div>
          <div className="mt-3">
            <div className="text-[11px] font-semibold mb-1">Рекомендации</div>
            <ul className="text-[11.5px] text-ink-600 space-y-1.5">
              <li className="flex items-start gap-1.5"><I.ArrowRight size={11} className="mt-0.5 text-teal-700"/>Партиционирование по <span className="mono">_Period</span> (YEAR)</li>
              <li className="flex items-start gap-1.5"><I.ArrowRight size={11} className="mt-0.5 text-teal-700"/>Архивация записей старше 5 лет в отдельную FG</li>
              <li className="flex items-start gap-1.5"><I.ArrowRight size={11} className="mt-0.5 text-teal-700"/>Перейти на columnstore для исторической партиции</li>
            </ul>
          </div>
        </Panel>

        {/* Anomaly */}
        <Panel className="col-span-8" title="ML anomaly score" sub="isolation forest + LSTM ensemble · per-signal">
          <AnomalyTimeline/>
          <div className="div-h my-3"></div>
          <div className="grid grid-cols-2 gap-2 text-[11.5px]">
            {[
              { t:'Yesterday 14:00', label:'Predicted memory leak in rphost #3 (60 min before incident). Avoided via auto-restart.', tone:'ok', conf:'92%' },
              { t:'3 days ago',      label:'Predicted Apdex degradation due to backup window. False positive — backup был отменён.', tone:'mute', conf:'71%' },
              { t:'5 days ago',      label:'Predicted SQL CPU saturation. Confirmed; ручной shedding по top-3 запросам.', tone:'ok', conf:'88%' },
              { t:'7 days ago',      label:'Predicted lock storm на закрытии месяца. Confirmed; advised reschedule.', tone:'ok', conf:'95%' },
            ].map((p,i)=>(
              <div key={i} className="border hl2 rounded p-2">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <Badge tone={p.tone}>{p.tone==='ok'?'confirmed':'false +'}</Badge>
                  <span className="mono text-[10.5px] text-ink-400">{p.t} · conf {p.conf}</span>
                </div>
                <div className="text-[11.5px] text-ink-700">{p.label}</div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel className="col-span-4" title="Release impact prediction" sub="diff vs runtime data">
          <div className="text-[11px] text-ink-500 mb-1.5">Last detected configuration change · 2 hours ago</div>
          <div className="border hl2 rounded p-2.5 bg-ink-25/40">
            <div className="text-[12px] mono">УТ 11.5.18.235 ← 11.5.18.230</div>
            <div className="text-[11px] text-ink-500 mt-0.5">deploy 12:48 · автор Сидоров А.В.</div>
          </div>

          <div className="mt-3">
            <div className="text-[11px] mono uppercase tracking-wider text-ink-400 mb-1">AI predicted regressions</div>
            <ul className="text-[12px] space-y-2">
              <li className="border hl2 rounded p-2 bg-err-bg/30">
                <div className="flex items-center gap-1.5"><Badge tone="err">−25 to −40%</Badge><span className="font-semibold">Закрытие месяца</span></div>
                <div className="text-[11.5px] text-ink-600 mt-1">Изменена <span className="mono">РассчитатьСебестоимость()</span> в <span className="mono">СебестоимостьРасчётСервер</span> — добавлено чтение <span className="mono">НастройкиПартионногоУчёта</span> в цикле по строкам ТЧ. +1000 SQL/проведение.</div>
                <button className="mt-2 text-[11px] h-6 px-2 rounded bg-teal-700 text-white">Investigate fix →</button>
              </li>
              <li className="border hl2 rounded p-2 bg-warn-bg/30">
                <div className="flex items-center gap-1.5"><Badge tone="warn">−5 to −10%</Badge><span className="font-semibold">Обмен данными_РЦ</span></div>
                <div className="text-[11.5px] text-ink-600 mt-1">Новые правила конвертации увеличили объём передаваемых данных.</div>
              </li>
            </ul>
          </div>
        </Panel>
      </div>
    </div>
  );
}

function ForecastChart() {
  const w=720, h=200, px=46, py=14, pb=24;
  const W=w-px-8, H=h-py-pb;
  const days = Array.from({length:120}, (_,i)=>i);
  const actual = days.slice(0,30).map(d => 2.0 + d*0.008 + Math.random()*0.05);
  const forecast = days.slice(30).map((d) => 2.24 + (d-30)*0.0088);
  const upper = forecast.map(v => v + 0.08);
  const lower = forecast.map(v => v - 0.08);
  const min = 1.9, max = 3.2;
  const xAt = i => px + (i/(days.length-1))*W;
  const yAt = v => py + H - ((v-min)/(max-min))*H;
  const pathOf = arr => arr.map((v,i)=> (i?'L':'M') + xAt(i + (arr===actual?0:30)).toFixed(1) + ' ' + yAt(v).toFixed(1)).join(' ');
  // confidence area
  const confArea = forecast.map((_,i)=>[xAt(i+30), yAt(upper[i])]).concat(forecast.map((_,i)=>[xAt(forecast.length-1-i+30), yAt(lower[forecast.length-1-i])])).map((p,i)=>(i?'L':'M')+p[0]+' '+p[1]).join(' ')+' Z';
  return (
    <svg width={w} height={h}>
      {[0,0.25,0.5,0.75,1].map((t,i)=>{
        const v = min + t*(max-min);
        return <g key={i}>
          <line x1={px} x2={px+W} y1={yAt(v)} y2={yAt(v)} stroke="#F0F0F0"/>
          <text x={px-6} y={yAt(v)+3} fontSize="10" textAnchor="end" fill="#A3A3A3" className="mono">{v.toFixed(1)} M</text>
        </g>;
      })}
      <path d={confArea} fill="#0F766E" opacity="0.10"/>
      <path d={pathOf(actual)} fill="none" stroke="#0F766E" strokeWidth="1.6"/>
      <path d={pathOf(forecast)} fill="none" stroke="#0F766E" strokeWidth="1.6" strokeDasharray="4 3"/>
      <line x1={xAt(30)} x2={xAt(30)} y1={py} y2={py+H} stroke="#0A0A0A" strokeDasharray="2 2"/>
      <text x={xAt(30)+4} y={py+10} fontSize="10" fill="#0A0A0A" className="mono">today</text>
      {/* threshold */}
      <line x1={px} x2={px+W} y1={yAt(3.0)} y2={yAt(3.0)} stroke="#DC2626" strokeDasharray="3 3"/>
      <text x={px+W-4} y={yAt(3.0)-4} fontSize="10" fill="#DC2626" textAnchor="end" className="mono">capacity ceiling 3.0 M</text>

      <text x={px} y={h-6} fontSize="10" fill="#A3A3A3" className="mono">−30 d</text>
      <text x={xAt(30)} y={h-6} fontSize="10" fill="#0A0A0A" textAnchor="middle" className="mono">today</text>
      <text x={px+W} y={h-6} fontSize="10" fill="#A3A3A3" textAnchor="end" className="mono">+90 d</text>
    </svg>
  );
}

function AnomalyTimeline() {
  // 7 days hourly anomaly score
  const w = 880, h = 130, px = 30, py = 10, pb = 16;
  const data = Array.from({length: 7*24}, (_,i)=>{
    const base = 0.15 + Math.sin(i*0.3)*0.05 + Math.random()*0.08;
    const spike = (i===56 || i===96 || i===150) ? 0.7 + Math.random()*0.2 : 0;
    return Math.min(1, base + spike);
  });
  const xAt = i => px + (i/(data.length-1))*(w-px-8);
  const yAt = v => py + (h-py-pb) - v*(h-py-pb);
  const path = data.map((v,i)=> (i?'L':'M') + xAt(i).toFixed(1) + ' ' + yAt(v).toFixed(1)).join(' ');
  return (
    <svg width={w} height={h}>
      {[0,0.25,0.5,0.75,1].map((t,i)=>(
        <g key={i}>
          <line x1={px} x2={w-8} y1={yAt(t)} y2={yAt(t)} stroke="#F0F0F0"/>
          <text x={px-4} y={yAt(t)+3} fontSize="10" textAnchor="end" fill="#A3A3A3" className="mono">{t.toFixed(1)}</text>
        </g>
      ))}
      <line x1={px} x2={w-8} y1={yAt(0.7)} y2={yAt(0.7)} stroke="#DC2626" strokeDasharray="3 3"/>
      <text x={w-12} y={yAt(0.7)-3} fontSize="10" textAnchor="end" fill="#DC2626" className="mono">threshold 0.70</text>
      <path d={path} fill="none" stroke="#0F766E" strokeWidth="1.4"/>
      {data.map((v,i)=> v>0.5 && <circle key={i} cx={xAt(i)} cy={yAt(v)} r={v>0.7?4:2.5} fill={v>0.7?'#DC2626':'#D97706'}/>)}
      {[0,24,48,72,96,120,144].map((d,i)=>(
        <text key={i} x={xAt(d)} y={h-3} fontSize="10" fill="#A3A3A3" textAnchor="middle" className="mono">{['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][i]}</text>
      ))}
    </svg>
  );
}

window.PredictiveScreen = PredictiveScreen;
