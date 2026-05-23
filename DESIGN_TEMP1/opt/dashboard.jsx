/* SCREEN 1: Operations Dashboard */
function DashboardScreen() {
  const apdexSeries = [0.91,0.92,0.90,0.88,0.87,0.85,0.84,0.86,0.89,0.91,0.92,0.90,0.87,0.83,0.78,0.81,0.86,0.88,0.87,0.85,0.82,0.84,0.87,0.87];
  const cpuSeries  = [42,38,40,45,52,58,61,63,67,72,68,64,70,75,82,78,71,66,69,72,68,65,67,67];

  const rphosts = [
    { id:'#1', pid:'12381', cpu:54, mem:'2.1', sess:24, status:'ok' },
    { id:'#2', pid:'12384', cpu:71, mem:'2.4', sess:31, status:'ok' },
    { id:'#3', pid:'12387', cpu:88, mem:'1.2', sess:28, status:'err',  growth:'+45 MB/h' },
    { id:'#4', pid:'12391', cpu:62, mem:'3.8', sess:22, status:'warn' },
    { id:'#5', pid:'12394', cpu:48, mem:'3.1', sess:19, status:'ok' },
    { id:'#6', pid:'12397', cpu:55, mem:'2.9', sess:23, status:'ok' },
  ];

  const sessions = [
    { user:'Иванов И.С.',     sid:47,  op:'Проведение Документ.РеализацияТоваровУслуг',      dur:47,  mem:234, cpu:23, alert:true  },
    { user:'Петров А.В.',     sid:89,  op:'Проведение Документ.КорректировкаДолга',          dur:34,  mem:188, cpu:18, alert:true  },
    { user:'Сидорова Е.А.',   sid:112, op:'Отчёт.ПродажиПоНоменклатуре.СформироватьОтчёт',    dur:18,  mem:412, cpu:12 },
    { user:'Морозов Д.С.',    sid:124, op:'Регламент.ОбменДанными.УзелОбмена_РЦ',            dur:12,  mem:96,  cpu:6  },
    { user:'Кузнецова О.Н.',  sid:131, op:'Обработка.ЗакрытиеМесяца.ВыполнитьПроцедуру',     dur:340, mem:892, cpu:41, alert:true },
  ];

  const waitTypes = [
    { name:'CPU', val:42 },
    { name:'PAGEIOLATCH', val:31 },
    { name:'LCK_M_X', val:18 },
    { name:'WRITELOG', val:14 },
    { name:'ASYNC_NETWORK', val:9 },
    { name:'SOS_SCHEDULER', val:6 },
  ];

  const events = [
    { t:'14:32:14', sev:'err',  txt:<>Deadlock между <b>Документ.КорректировкаДолга</b> и <b>Документ.РеализацияТоваровУслуг</b> · victim sid 89</> },
    { t:'14:18:02', sev:'err',  txt:<>Memory leak detected in <b className="mono">rphost #3</b> (+45 MB/min over 1h)</> },
    { t:'13:47:51', sev:'warn', txt:<>Slow query in <b className="mono">РасчётыСКонтрагентамиСервер.СформироватьТаблицуРасчётов</b> · avg 4.2s</> },
    { t:'13:22:08', sev:'info', txt:<>Apdex dropped from 0.91 → 0.78 over 12 min</> },
    { t:'12:55:00', sev:'ok',   txt:<>Auto-resolved: timeout in Apdex collection (transient)</> },
    { t:'12:33:41', sev:'warn', txt:<>Long server call <span className="mono">ЗакрытиеМесяца.Выполнить()</span> · 340s, sid 131</> },
  ];

  const insights = [
    { tag:'pattern', title:'Recurring Deadlock Pattern',
      body:<>47 deadlocks за 24h между <span className="mono">Документ.Реализация</span> и <span className="mono">Документ.КорректировкаДолга</span>. Корень: разный порядок изменения регистров.</>,
      impact:'High', conf:'94%', cta:'Investigate' },
    { tag:'query', title:'Query eats 23% of SQL CPU',
      body:<><span className="mono">РасчётыСКонтрагентамиСервер.СформироватьТаблицуРасчётов()</span> — 380s/day, p95 8.1s. Виртуальная таблица без фильтра по периоду.</>,
      impact:'High', conf:'High', cta:'View details' },
    { tag:'forecast', title:'Memory growth in rphost #3',
      body:<>+45 MB/h, текущая 1.2 GB. При тренде через ~3h упрётесь в лимит 4 GB. Подозрение — утечка в <span className="mono">ОбменДаннымиСервер</span>.</>,
      impact:'Medium', conf:'87%', cta:'Show forecast' },
  ];

  return (
    <div>
      {/* Page header */}
      <PageHeader
        breadcrumbs={['УТ 11.5 — Production', 'Operations']}
        title="Operations Dashboard"
        sub="real-time, last 24h"
        right={<>
          <SegGroup>
            <SegBtn active>1h</SegBtn><SegBtn>6h</SegBtn><SegBtn>24h</SegBtn><SegBtn>7d</SegBtn>
          </SegGroup>
          <button className="ml-2 h-7 px-2 text-[11px] flex items-center gap-1 border hl2 rounded text-ink-600 hover:bg-ink-50"><I.Refresh size={12}/>Refresh</button>
        </>}
      />

      {/* 1) Health Status Bar */}
      <div className="px-4 py-3 bg-white border-b hl flex items-center gap-6">
        <div className="flex items-center gap-3 pr-6 border-r hl">
          <div className="relative">
            <div className="w-10 h-10 rounded-full bg-warn-bg grid place-items-center"><I.AlertTriangle size={20} className="text-warn"/></div>
          </div>
          <div className="leading-tight">
            <div className="text-[15px] font-semibold text-warn">3 Active Warnings</div>
            <div className="text-[11px] text-ink-500">1 critical deadlock pattern · 1 memory anomaly · 1 slow query family</div>
          </div>
        </div>

        <div className="flex items-end gap-8 px-2">
          <KPI label="APDEX" value="0.87" sub={<span className="flex items-center gap-1">target 0.90 <I.ChevronDown size={12} className="text-warn"/></span>} tone="warn"/>
          <KPI label="AVG RESPONSE" value="340 ms" sub="p95 1.2 s · p99 4.8 s"/>
          <KPI label="ACTIVE SESSIONS" value="147" sub="peak today 213"/>
          <KPI label="ERRORS / MIN" value="3" sub="last incident 4m ago" tone="warn"/>
          <KPI label="DEADLOCKS / 1H" value="4" sub="pattern #1247 dominant" tone="err"/>
          <KPI label="SLA TODAY" value="96.4%" sub="target 99.0%" tone="warn"/>
        </div>

        <div className="ml-auto flex flex-col items-end gap-1.5">
          <div className="text-[11px] text-ink-500 mono">last updated <span className="text-ink-900">2 s ago</span></div>
          <label className="flex items-center gap-1.5 text-[11px] text-ink-600">
            <span className="w-7 h-4 rounded-full bg-teal-700 relative">
              <span className="absolute right-0.5 top-0.5 w-3 h-3 rounded-full bg-white"></span>
            </span>
            auto-refresh
          </label>
        </div>
      </div>

      {/* 2) Timeline Strip */}
      <div className="px-4 py-3 bg-white border-b hl">
        <div className="flex items-center text-[11px] text-ink-500 mono mb-1.5">
          <span>last 24h timeline</span>
          <span className="ml-auto flex items-center gap-3">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-teal-700"/>Apdex</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-err"/>Deadlocks</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rotate-45 bg-warn"/>Timeouts</span>
            <span className="flex items-center gap-1"><span className="w-3 h-2 bg-info"/>Scheduled jobs</span>
          </span>
        </div>
        <TimelineStrip apdex={apdexSeries}/>
      </div>

      {/* 3) Main 4-column grid */}
      <div className="grid grid-cols-12 gap-3 p-3">
        {/* Cluster Status */}
        <Panel className="col-span-3" title="1С Server Cluster" sub="6 rphost · 1 ragent" right={
          <button className="text-[11px] text-teal-700 hover:underline">Topology →</button>
        }>
          <div className="grid grid-cols-3 gap-2 mb-3">
            {rphosts.map(r => (
              <div key={r.id} className={`rounded border ${r.status==='err'?'border-err/40 bg-err-bg/40':r.status==='warn'?'border-warn/40 bg-warn-bg/40':'border-ink-150 bg-white'} p-2 leading-tight`}>
                <div className="flex items-center justify-between">
                  <span className="mono text-[11.5px] font-semibold">rphost {r.id}</span>
                  <Sev level={r.status} size={7}/>
                </div>
                <div className="mono text-[10px] text-ink-400">pid {r.pid}</div>
                <div className="mt-1.5 flex items-center gap-1.5 text-[10.5px] mono">
                  <span className="text-ink-400">CPU</span>
                  <div className="flex-1 h-1 bg-ink-100 rounded-sm overflow-hidden">
                    <div className={`h-full ${r.cpu>80?'bg-err':r.cpu>65?'bg-warn':'bg-teal-700'}`} style={{width:r.cpu+'%'}}/>
                  </div>
                  <span className="tnum w-6 text-right">{r.cpu}%</span>
                </div>
                <div className="mt-0.5 flex items-center gap-1.5 text-[10.5px] mono">
                  <span className="text-ink-400">MEM</span>
                  <span className="ml-auto tnum">{r.mem} GB</span>
                </div>
                <div className="mt-0.5 text-[10.5px] mono text-ink-500">{r.sess} sess.</div>
                {r.growth && <div className="mt-1 text-[10px] mono text-err">{r.growth} LEAK?</div>}
              </div>
            ))}
          </div>
          <div className="div-h mb-2"></div>
          <div className="grid grid-cols-3 text-[11px]">
            <div><div className="text-ink-400 mono text-[10px] uppercase tracking-wider">Sessions</div><div className="mono tnum font-semibold text-[15px]">147</div></div>
            <div><div className="text-ink-400 mono text-[10px] uppercase tracking-wider">Memory</div><div className="mono tnum font-semibold text-[15px]">15.5 GB</div></div>
            <div><div className="text-ink-400 mono text-[10px] uppercase tracking-wider">CPU avg</div><div className="mono tnum font-semibold text-[15px]">63%</div></div>
          </div>
        </Panel>

        {/* Active Sessions */}
        <Panel className="col-span-3" title="Top Active Sessions" sub={`${sessions.length} of 147`} right={<button className="text-[11px] text-teal-700 hover:underline">All sessions →</button>}>
          <table className="w-full text-[11.5px]">
            <tbody className="divide-y divide-ink-100">
              {sessions.map(s => (
                <tr key={s.sid} className="row">
                  <td className="py-1.5 pr-2">
                    <div className="flex items-center gap-1.5">
                      {s.alert && <Sev level="err" size={6}/>}
                      <span className="font-medium">{s.user}</span>
                      <span className="mono text-[10px] text-ink-400">sid {s.sid}</span>
                    </div>
                    <div className="mono text-[10.5px] text-ink-500 truncate max-w-[280px]">{s.op}</div>
                  </td>
                  <td className="py-1.5 mono tnum text-right align-top whitespace-nowrap">
                    <span className={s.dur>=30?'text-err font-semibold':'text-ink-700'}>{s.dur}s</span>
                    <div className="text-[10px] text-ink-400">{s.mem} MB · {s.cpu}%</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        {/* SQL Activity */}
        <Panel className="col-span-3" title="SQL Server Activity" sub="MS SQL 2022 · last 1h" right={<button className="text-[11px] text-teal-700 hover:underline">Slow queries →</button>}>
          <div className="text-[11px] text-ink-500 mono mb-1.5">Wait types · share of waits</div>
          <div className="space-y-1">
            {waitTypes.map(w=>(
              <div key={w.name} className="flex items-center gap-2 text-[11px]">
                <span className="mono w-28 truncate text-ink-700">{w.name}</span>
                <div className="flex-1 h-2.5 bg-ink-100 rounded-sm overflow-hidden">
                  <div className="h-full bg-teal-700" style={{width:`${(w.val/42)*100}%`, opacity: 0.55 + (w.val/42)*0.45}}/>
                </div>
                <span className="mono tnum w-7 text-right text-ink-600">{w.val}%</span>
              </div>
            ))}
          </div>
          <div className="div-h my-3"></div>
          <div className="grid grid-cols-2 gap-y-1.5 text-[11px]">
            <div className="flex justify-between"><span className="text-ink-500">Active queries</span><span className="mono tnum font-medium">23</span></div>
            <div className="flex justify-between"><span className="text-ink-500">Blocked sessions</span><span className="mono tnum font-medium text-warn">2</span></div>
            <div className="flex justify-between"><span className="text-ink-500">Deadlocks (1h)</span><span className="mono tnum font-medium text-err">4</span></div>
            <div className="flex justify-between"><span className="text-ink-500">Avg query time</span><span className="mono tnum font-medium">245 ms</span></div>
            <div className="flex justify-between"><span className="text-ink-500">Tempdb usage</span><span className="mono tnum font-medium">8.4 GB</span></div>
            <div className="flex justify-between"><span className="text-ink-500">Buffer hit ratio</span><span className="mono tnum font-medium text-ok">99.4%</span></div>
          </div>
        </Panel>

        {/* Recent Critical Events */}
        <Panel className="col-span-3" title="Critical Events" sub="last 1h" right={<button className="text-[11px] text-teal-700 hover:underline">Alerts →</button>}>
          <ul className="divide-y divide-ink-100 -mx-3 -my-3">
            {events.map((e,i)=>(
              <li key={i} className="px-3 py-2 flex items-start gap-2 hover:bg-ink-25 cursor-pointer">
                <div className="mt-0.5"><Sev level={e.sev} size={8}/></div>
                <div className="flex-1 min-w-0">
                  <div className="text-[11.5px] leading-snug text-ink-700">{e.txt}</div>
                  <div className="text-[10px] mono text-ink-400 mt-0.5">{e.t}</div>
                </div>
                <I.ChevronRight size={12} className="text-ink-300 mt-1"/>
              </li>
            ))}
          </ul>
        </Panel>

        {/* AI Insights */}
        <div className="col-span-12">
          <Panel title={<span className="flex items-center gap-1.5"><I.Sparkles size={13} className="text-teal-700"/>AI Insights</span>} sub="proactive, last 24h"
            right={<>
              <button className="text-[11px] text-ink-500 hover:text-ink-900">Pause AI</button>
              <button className="text-[11px] text-teal-700 hover:underline">Tune signals →</button>
            </>}>
            <div className="grid grid-cols-3 gap-3">
              {insights.map((it,i)=>(
                <div key={i} className="border hl2 rounded-md p-3 hover:border-teal-700/30 transition">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <Badge tone={it.tag==='forecast'?'info':it.tag==='query'?'warn':'err'} mono>{it.tag.toUpperCase()}</Badge>
                    <Badge tone="mute">impact: {it.impact}</Badge>
                    <span className="ml-auto text-[10.5px] mono text-ink-400">conf {it.conf}</span>
                  </div>
                  <div className="text-[13.5px] font-semibold mb-1">{it.title}</div>
                  <div className="text-[12px] text-ink-600 leading-snug">{it.body}</div>
                  <div className="mt-2.5 flex items-center gap-2">
                    <button className="text-[11px] h-6 px-2 rounded border hl2 bg-white hover:bg-teal-50 text-teal-700 flex items-center gap-1">{it.cta} <I.ArrowRight size={11}/></button>
                    <button className="text-[11px] text-ink-500 hover:text-ink-900">Dismiss</button>
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

function TimelineStrip({ apdex }) {
  const w = 1380, h = 56;
  const px = 0, py = 4;
  const W = w, H = h - 8;
  const min = 0.6, max = 1.0;
  const xAt = i => px + (i/(apdex.length-1))*W;
  const yAt = v => py + H - ((v-min)/(max-min))*H;
  const path = apdex.map((v,i)=> (i?'L':'M') + xAt(i).toFixed(1) + ' ' + yAt(v).toFixed(1)).join(' ');
  const area = path + ` L${w} ${h-4} L0 ${h-4} Z`;
  // events markers
  const ev = [
    { i:6,  type:'sched' },
    { i:8,  type:'dl' },
    { i:14, type:'dl' },
    { i:15, type:'to' },
    { i:18, type:'dl' },
    { i:21, type:'sched' },
  ];
  return (
    <div className="relative">
      <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="w-full h-14">
        {/* gridlines */}
        {[0,0.25,0.5,0.75,1].map(t => (
          <line key={t} x1={0} x2={w} y1={py + H - t*H} y2={py + H - t*H} stroke="#F0F0F0" strokeWidth="1"/>
        ))}
        <path d={area} fill="#0F766E" opacity="0.08"/>
        <path d={path} fill="none" stroke="#0F766E" strokeWidth="1.6"/>
        {/* target line */}
        <line x1={0} x2={w} y1={yAt(0.90)} y2={yAt(0.90)} stroke="#16A34A" strokeDasharray="4 4" opacity="0.6"/>
        {/* scheduled job blue blocks */}
        {ev.filter(e=>e.type==='sched').map((e,i)=>(<rect key={i} x={xAt(e.i)} y={h-3} width={50} height={3} fill="#2563EB" opacity="0.7"/>))}
        {ev.filter(e=>e.type==='dl').map((e,i)=>(<circle key={i} cx={xAt(e.i)} cy={yAt(apdex[e.i])} r={3.5} fill="#DC2626"/>))}
        {ev.filter(e=>e.type==='to').map((e,i)=>(<polygon key={i} points={`${xAt(e.i)-3},${yAt(apdex[e.i])+4} ${xAt(e.i)+3},${yAt(apdex[e.i])+4} ${xAt(e.i)},${yAt(apdex[e.i])-2}`} fill="#D97706"/>))}
        {/* cursor */}
        <line x1={xAt(20)} x2={xAt(20)} y1={0} y2={h} stroke="#0A0A0A" strokeWidth="1" opacity="0.85"/>
      </svg>
      <div className="flex justify-between mt-1 text-[10px] mono text-ink-400">
        <span>15:00 (yesterday)</span><span>21:00</span><span>03:00</span><span>09:00</span><span>15:00 today</span>
      </div>
    </div>
  );
}

window.DashboardScreen = DashboardScreen;
