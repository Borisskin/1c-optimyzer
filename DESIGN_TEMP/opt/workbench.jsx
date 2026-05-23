/* SCREEN 3: Investigation Workbench — 4-zone IDE */
function WorkbenchScreen() {
  const [tab, setTab] = React.useState('timeline');
  const [bottomTab, setBottomTab] = React.useState('events');

  const investigations = {
    active: [
      { name:'Deadlock pattern Реализация ↔ КорректировкаДолга', sev:'err', meta:'47 occ./24h · started 3d ago' },
    ],
    watched: [
      { name:'Проведение Документ.РеализацияТоваровУслуг', meta:'avg 1.2s · p95 3.4s', sev:'ok' },
      { name:'Закрытие месяца',                            meta:'Apdex 0.42 · 540s p99', sev:'err' },
      { name:'СформироватьТаблицуРасчётов()',              meta:'4.2s avg · 12k/day',   sev:'warn' },
      { name:'rphost #3 memory',                           meta:'+45 MB/h',             sev:'err' },
      { name:'NoлайтКоOpensql: HotPath SQL',               meta:'TempDB pressure',      sev:'warn' },
    ],
    recent: [
      { name:'Resolved: Slow query in НоменклатураСервер', meta:'3d ago · -68%', sev:'ok' },
      { name:'Closed: Memory leak hypothesis',             meta:'1w ago · invalid', sev:'mute' },
      { name:'Resolved: Index missing on _Reference234',   meta:'2w ago · +120ms→8ms', sev:'ok' },
      { name:'Postponed: Архитектура регистров',           meta:'нужна оценка', sev:'mute' },
    ],
    bookmarks: [
      { name:'High-impact pattern #1247', meta:'pinned' },
      { name:'Hot day baseline · 12.05', meta:'snapshot' },
      { name:'Production hotfix #2024-09', meta:'reference' },
    ],
  };

  const events = [
    { t:'14:32:14.821', src:'SQL',    sev:'err',  type:'deadlock', txt:'Process 47 was deadlock victim. Resource: _AccumRgT5634 (KEY)'},
    { t:'14:32:14.819', src:'SQL',    sev:'err',  type:'deadlock', txt:'Process 89 holding X lock on _AccumRgT5891, requesting S on _AccumRgT5634'},
    { t:'14:32:14.814', src:'1C',     sev:'warn', type:'long-tx',  txt:'Document.РеализацияТоваровУслуг.ОбработкаПроведения() > 30s'},
    { t:'14:32:11.402', src:'1C',     sev:'info', type:'event',    txt:'Сеанс 47 · Иванов И.С. начал транзакцию'},
    { t:'14:32:10.991', src:'SQL',    sev:'info', type:'query',    txt:'EXEC sp_executesql with @P1=...,@P2=... · 1.8s · 234K logical reads'},
    { t:'14:32:09.501', src:'1C',     sev:'info', type:'event',    txt:'Сеанс 89 · Петров А.В. начал транзакцию'},
    { t:'14:32:08.221', src:'System', sev:'info', type:'metric',   txt:'rphost #2 CPU 71% · memory 2.4 GB'},
    { t:'14:32:07.918', src:'SQL',    sev:'warn', type:'wait',     txt:'Long LCK_M_X wait (3.4s) on object_id=874003213'},
    { t:'14:32:06.114', src:'1C',     sev:'info', type:'event',    txt:'Регламент: Обмен данными.УзелОбмена_РЦ начат'},
    { t:'14:32:01.302', src:'1C',     sev:'err',  type:'exception',txt:'Превышено время ожидания блокировки в Документ.КорректировкаДолга'},
  ];

  const treeBlock = (title, items) => (
    <div className="mb-2">
      <div className="px-2 py-1 text-[10px] mono uppercase tracking-wider text-ink-400 flex items-center gap-1.5">
        <I.ChevronDown size={11}/>{title}
        <span className="ml-auto mono text-ink-300">{items.length}</span>
      </div>
      {items.map((it,i)=>(
        <button key={i} className={`w-full text-left px-2.5 py-1.5 hover:bg-ink-50 flex items-start gap-2 ${i===0&&title==='Active Investigation'?'bg-teal-50/60':''}`}>
          <Sev level={it.sev || 'mute'} size={7}/>
          <div className="flex-1 min-w-0">
            <div className="text-[12px] truncate">{it.name}</div>
            <div className="text-[10px] mono text-ink-400 truncate">{it.meta}</div>
          </div>
        </button>
      ))}
    </div>
  );

  return (
    <div className="flex flex-col h-[calc(100vh-48px-28px)]">
      <PageHeader breadcrumbs={['Investigation','Deadlock #1247']} title="Investigation Workbench"
        sub="multi-modal performance forensics"
        right={<>
          <button className="h-7 px-2 text-[11px] border hl2 rounded flex items-center gap-1 text-ink-600 hover:bg-ink-50"><I.Plus size={11}/>New</button>
          <button className="h-7 px-2 text-[11px] border hl2 rounded flex items-center gap-1 text-ink-600 hover:bg-ink-50"><I.Bookmark size={11}/>Bookmark</button>
          <button className="h-7 px-2 text-[11px] border hl2 rounded flex items-center gap-1 text-teal-700 bg-teal-50 hover:bg-teal-100"><I.Share size={11}/>Share investigation</button>
        </>}/>

      <div className="flex-1 grid grid-cols-[260px_1fr_360px] gap-0 overflow-hidden">
        {/* Zone 1: Investigation Tree */}
        <aside className="border-r hl bg-white overflow-y-auto">
          <div className="px-2.5 py-2 border-b hl">
            <div className="text-[10px] mono uppercase tracking-wider text-ink-400">Current</div>
            <div className="text-[12.5px] font-semibold leading-snug">Deadlock pattern: Реализация ↔ КорректировкаДолга</div>
            <div className="text-[10.5px] mono text-ink-500 mt-0.5">opened 3d · 12 nodes · 47 events</div>
          </div>
          {treeBlock('Active Investigation', investigations.active)}
          {treeBlock('Watched operations', investigations.watched)}
          {treeBlock('Recent investigations', investigations.recent)}
          {treeBlock('Bookmarks', investigations.bookmarks)}
        </aside>

        {/* Zone 2: Main view */}
        <section className="flex flex-col overflow-hidden bg-white">
          <Tabs value={tab} onChange={setTab} dense tabs={[
            { id:'timeline', label:'Timeline',  icon:I.Activity },
            { id:'topology', label:'Topology',  icon:I.Cluster },
            { id:'lockgraph',label:'Lock Graph',icon:I.Lock },
            { id:'plan',     label:'Query Plan',icon:I.Database },
            { id:'code',     label:'Code',      icon:I.Code },
            { id:'metrics',  label:'Metrics',   icon:I.Trend },
          ]}/>
          <div className="flex-1 overflow-auto">
            {tab==='timeline' && <WorkbenchTimeline/>}
            {tab==='topology' && <WorkbenchTopology/>}
            {tab==='lockgraph' && <WorkbenchLockGraph/>}
            {tab==='plan' && <WorkbenchQueryPlan/>}
            {tab==='code' && <WorkbenchCode/>}
            {tab==='metrics' && <WorkbenchMetrics/>}
          </div>

          {/* Zone 4: bottom dock */}
          <div className="border-t hl">
            <Tabs value={bottomTab} onChange={setBottomTab} dense tabs={[
              { id:'events',  label:'Events Stream', icon:I.Activity, count:1284 },
              { id:'chat',    label:'AI Chat',       icon:I.Sparkles },
              { id:'query',   label:'Query Inspector',icon:I.Database },
              { id:'console', label:'Console',       icon:I.Terminal },
              { id:'diff',    label:'Comparison Diff', icon:I.GitCompare },
            ]}/>
            <div className="h-[220px] overflow-auto bg-ink-25/40">
              {bottomTab==='events' && <EventsStream events={events}/>}
              {bottomTab==='chat' && <WorkbenchAIChatInline/>}
              {bottomTab==='query' && <WorkbenchQueryInspector/>}
              {bottomTab==='console' && <WorkbenchConsole/>}
              {bottomTab==='diff' && <div className="p-3 text-[12px] text-ink-500">Diff snapshot taken 14:32 vs baseline (yesterday 14:00) · открыть в Comparison →</div>}
            </div>
          </div>
        </section>

        {/* Zone 3: Inspector */}
        <aside className="border-l hl bg-white overflow-y-auto">
          <DeadlockInspector/>
        </aside>
      </div>
    </div>
  );
}

function WorkbenchTimeline() {
  const lanes = [
    { name:'CPU · 1С',  color:'#0F766E', data:[42,38,40,45,52,58,61,63,67,72,68,64,70,75,82,78,71,66,69,72,68,65,67,67,73,80,84,79] },
    { name:'CPU · SQL', color:'#0D9488', data:[51,49,53,55,58,62,65,68,71,74,72,69,72,78,85,82,75,71,73,76,72,69,71,73,77,84,89,86] },
    { name:'Apdex',     color:'#16A34A', data:[0.91,0.92,0.90,0.88,0.87,0.85,0.84,0.86,0.89,0.91,0.92,0.90,0.87,0.83,0.78,0.81,0.86,0.88,0.87,0.85,0.82,0.84,0.87,0.87,0.83,0.78,0.74,0.78], scale:[0.6,1] },
    { name:'Memory',    color:'#7C3AED', data:[12.1,12.3,12.5,12.6,12.8,13.0,13.2,13.4,13.6,13.8,14.0,14.2,14.4,14.6,14.8,15.0,15.2,15.4,15.5,15.5,15.5,15.5,15.5,15.5,15.5,15.5,15.5,15.5], scale:[10,18] },
  ];
  const events = [
    {lane:2, i:14, type:'err', label:'deadlock'},
    {lane:2, i:18, type:'err', label:'deadlock'},
    {lane:2, i:25, type:'err', label:'deadlock'},
    {lane:0, i:8,  type:'info',label:'schedule'},
    {lane:0, i:22, type:'warn',label:'long call'},
    {lane:3, i:15, type:'warn',label:'leak begin'},
  ];
  return (
    <div className="p-3">
      <div className="flex items-center gap-2 mb-2 text-[11px] text-ink-500">
        <SegGroup>
          <SegBtn>15m</SegBtn><SegBtn active>1h</SegBtn><SegBtn>6h</SegBtn><SegBtn>24h</SegBtn>
        </SegGroup>
        <button className="h-7 px-2 text-[11px] border hl2 rounded text-ink-600 flex items-center gap-1 ml-2"><I.Maximize size={11}/>Zoom to selection</button>
        <button className="h-7 px-2 text-[11px] border hl2 rounded text-ink-600 flex items-center gap-1"><I.Filter size={11}/>Lanes</button>
        <div className="ml-auto mono text-[10.5px] text-ink-400">cursor 14:32:14 · selection 14:30 – 14:34 · 4 min</div>
      </div>

      <div className="border hl2 rounded-md overflow-hidden">
        {/* time axis */}
        <div className="flex items-center px-2 h-6 border-b hl bg-ink-25 mono text-[10.5px] text-ink-500">
          {['14:00','14:05','14:10','14:15','14:20','14:25','14:30','14:35','14:40','14:45','14:50','14:55','15:00'].map(t => (
            <div key={t} className="flex-1 border-l hl pl-1 last:border-r">{t}</div>
          ))}
        </div>

        {/* lanes */}
        {lanes.map((l,li)=>(
          <div key={li} className="flex border-b hl last:border-0 relative">
            <div className="w-[110px] px-2 py-2 border-r hl bg-ink-25/50">
              <div className="text-[11px] font-medium">{l.name}</div>
              <div className="mono text-[10px] text-ink-400">range {l.scale?l.scale.join('–'):'auto'}</div>
            </div>
            <div className="flex-1 relative" style={{height: 72}}>
              <svg viewBox="0 0 1000 72" preserveAspectRatio="none" className="absolute inset-0 w-full h-full">
                {(() => {
                  const min = l.scale?l.scale[0]:Math.min(...l.data);
                  const max = l.scale?l.scale[1]:Math.max(...l.data);
                  const range = (max-min)||1;
                  const pts = l.data.map((v,i)=>[i/(l.data.length-1)*1000, 72 - 4 - ((v-min)/range)*64]);
                  const path = pts.map((p,i)=> (i?'L':'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
                  const area = path + ' L1000 72 L0 72 Z';
                  return <>
                    <path d={area} fill={l.color} opacity="0.07"/>
                    <path d={path} fill="none" stroke={l.color} strokeWidth="1.4"/>
                  </>;
                })()}
              </svg>
              {/* events */}
              {events.filter(e=>e.lane===li).map((e,i)=>{
                const x = (e.i/(l.data.length-1))*100;
                return (
                  <span key={i} className="absolute top-1.5"
                    style={{left:`${x}%`}}>
                    <span className={`block w-2.5 h-2.5 rounded-full ${e.type==='err'?'bg-err':e.type==='warn'?'bg-warn':'bg-info'} ring-2 ring-white`}></span>
                    <span className={`absolute -top-3.5 left-1 text-[9.5px] mono ${e.type==='err'?'text-err':e.type==='warn'?'text-warn':'text-info'} whitespace-nowrap`}>{e.label}</span>
                  </span>
                );
              })}
              {/* cursor at 14:32 */}
              <div className="absolute top-0 bottom-0 w-px bg-ink-900" style={{left:'53.5%'}}></div>
              {/* selection */}
              <div className="absolute top-0 bottom-0 bg-teal-700/8 border-l border-r border-teal-700/30" style={{left:'50%', width:'8%'}}></div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-3 grid grid-cols-3 gap-3">
        <Panel dense title="Correlations" sub="auto-detected">
          <ul className="space-y-1 text-[11.5px]">
            <li className="flex items-center gap-2"><I.Bolt size={11} className="text-warn"/><span>SQL CPU спайки коррелируют с pattern #1247 (r=0.78)</span></li>
            <li className="flex items-center gap-2"><I.Bolt size={11} className="text-warn"/><span>Apdex падает после deploy 11.5.18.235</span></li>
            <li className="flex items-center gap-2"><I.Bolt size={11} className="text-info"/><span>Memory rphost #3 растёт линейно с числом обменов (r=0.93)</span></li>
          </ul>
        </Panel>
        <Panel dense title="Span breakdown" sub="14:32:14 transaction">
          <ul className="space-y-1 text-[11px] mono">
            <li className="flex justify-between"><span>SQL execute</span><span className="tnum">1.81s</span></li>
            <li className="flex justify-between"><span>Wait LCK_M_X</span><span className="tnum text-warn">3.42s</span></li>
            <li className="flex justify-between"><span>BSL ОбработкаПроведения</span><span className="tnum">0.74s</span></li>
            <li className="flex justify-between"><span>Сериализация</span><span className="tnum">0.12s</span></li>
            <li className="flex justify-between"><span>Network</span><span className="tnum">0.03s</span></li>
          </ul>
        </Panel>
        <Panel dense title="System pulse" sub="snapshot 14:32:14">
          <ul className="space-y-1 text-[11px]">
            <li className="flex justify-between text-ink-500"><span>rphost #2 CPU</span><span className="mono tnum text-ink-900">71%</span></li>
            <li className="flex justify-between text-ink-500"><span>rphost #3 CPU</span><span className="mono tnum text-err">88%</span></li>
            <li className="flex justify-between text-ink-500"><span>SQL Server CPU</span><span className="mono tnum text-warn">82%</span></li>
            <li className="flex justify-between text-ink-500"><span>Tempdb GB</span><span className="mono tnum">8.4</span></li>
            <li className="flex justify-between text-ink-500"><span>Lock waits</span><span className="mono tnum text-warn">12</span></li>
          </ul>
        </Panel>
      </div>
    </div>
  );
}

function WorkbenchTopology() {
  return (
    <div className="p-4">
      <div className="text-[12px] text-ink-500 mb-2">Cluster topology · selected: rphost #3</div>
      <svg viewBox="0 0 880 320" className="w-full max-w-[900px] border hl2 rounded-md bg-ink-25/30">
        {/* connections */}
        {[
          [120,160, 320,90],  [120,160, 320,160], [120,160, 320,230],
          [320,90, 540,90],   [320,160, 540,160], [320,230, 540,230],
          [540,90, 740,160],  [540,160, 740,160], [540,230, 740,160],
        ].map((c,i)=>(
          <line key={i} x1={c[0]} y1={c[1]} x2={c[2]} y2={c[3]} stroke="#D4D4D4" strokeWidth="1.4"/>
        ))}
        {/* nodes */}
        <Node x={120} y={160} label="ragent" sub="cluster mgr" color="#0F766E"/>
        <Node x={320} y={90}  label="rphost #1" sub="24 sess" color="#16A34A"/>
        <Node x={320} y={160} label="rphost #2" sub="31 sess" color="#16A34A"/>
        <Node x={320} y={230} label="rphost #3" sub="28 sess · LEAK" color="#DC2626" highlight/>
        <Node x={540} y={90}  label="rphost #4" sub="22 sess" color="#D97706"/>
        <Node x={540} y={160} label="rphost #5" sub="19 sess" color="#16A34A"/>
        <Node x={540} y={230} label="rphost #6" sub="23 sess" color="#16A34A"/>
        <Node x={740} y={160} label="SQL Server" sub="MSSQL 2022" color="#0F766E" big/>
      </svg>
    </div>
  );
}
function Node({ x, y, label, sub, color, big, highlight }) {
  const r = big?40:28;
  return (
    <g>
      {highlight && <circle cx={x} cy={y} r={r+4} fill="none" stroke="#DC2626" strokeWidth="1" strokeDasharray="3 3" opacity="0.7"/>}
      <circle cx={x} cy={y} r={r} fill="#FFFFFF" stroke={color} strokeWidth="2"/>
      <circle cx={x} cy={y} r={r-9} fill={color} opacity="0.15"/>
      <text x={x} y={y-1} fontSize="12" textAnchor="middle" fill="#0A0A0A" fontWeight="600" className="mono">{label}</text>
      <text x={x} y={y+12} fontSize="10" textAnchor="middle" fill="#737373" className="mono">{sub}</text>
    </g>
  );
}

function WorkbenchLockGraph() {
  return (
    <div className="p-4">
      <div className="text-[12px] text-ink-500 mb-2">Deadlock #1247 · resource graph at 14:32:14</div>
      <svg viewBox="0 0 720 340" className="w-full max-w-[820px] border hl2 rounded-md bg-ink-25/30">
        <defs>
          <marker id="ahr" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto">
            <path d="M0,0 L10,5 L0,10 Z" fill="#DC2626"/>
          </marker>
          <marker id="ahg" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto">
            <path d="M0,0 L10,5 L0,10 Z" fill="#737373"/>
          </marker>
        </defs>
        {/* sessions */}
        <g>
          <rect x="40" y="60" width="200" height="80" rx="6" fill="#FEF2F2" stroke="#DC2626"/>
          <text x="140" y="84" textAnchor="middle" fontSize="13" fontWeight="600" fill="#0A0A0A">Session #47</text>
          <text x="140" y="100" textAnchor="middle" fontSize="11" fill="#525252" className="mono">Иванов И.С.</text>
          <text x="140" y="116" textAnchor="middle" fontSize="11" fill="#525252">Документ.РеализацияТоваровУслуг</text>
          <text x="140" y="132" textAnchor="middle" fontSize="10" fill="#DC2626" className="mono">VICTIM · rolled back</text>
        </g>
        <g>
          <rect x="480" y="60" width="200" height="80" rx="6" fill="#FFFBEB" stroke="#D97706"/>
          <text x="580" y="84" textAnchor="middle" fontSize="13" fontWeight="600" fill="#0A0A0A">Session #89</text>
          <text x="580" y="100" textAnchor="middle" fontSize="11" fill="#525252" className="mono">Петров А.В.</text>
          <text x="580" y="116" textAnchor="middle" fontSize="11" fill="#525252">Документ.КорректировкаДолга</text>
          <text x="580" y="132" textAnchor="middle" fontSize="10" fill="#D97706" className="mono">survived</text>
        </g>
        {/* resources */}
        <g>
          <rect x="100" y="220" width="200" height="80" rx="6" fill="#FFFFFF" stroke="#A3A3A3"/>
          <text x="200" y="244" textAnchor="middle" fontSize="13" fontWeight="600" className="mono">_AccumRgT5634</text>
          <text x="200" y="260" textAnchor="middle" fontSize="11" fill="#525252">РегистрНакопления.</text>
          <text x="200" y="276" textAnchor="middle" fontSize="11" fill="#525252">РасчётыСКонтрагентами</text>
          <text x="200" y="292" textAnchor="middle" fontSize="10" fill="#DC2626" className="mono">X lock held by #47</text>
        </g>
        <g>
          <rect x="420" y="220" width="200" height="80" rx="6" fill="#FFFFFF" stroke="#A3A3A3"/>
          <text x="520" y="244" textAnchor="middle" fontSize="13" fontWeight="600" className="mono">_AccumRgT5891</text>
          <text x="520" y="260" textAnchor="middle" fontSize="11" fill="#525252">РегистрНакопления.</text>
          <text x="520" y="276" textAnchor="middle" fontSize="11" fill="#525252">Взаиморасчёты</text>
          <text x="520" y="292" textAnchor="middle" fontSize="10" fill="#D97706" className="mono">X lock held by #89</text>
        </g>
        {/* edges */}
        <line x1="140" y1="140" x2="200" y2="220" stroke="#737373" strokeWidth="1.6" markerEnd="url(#ahg)"/>
        <text x="135" y="190" fontSize="10" fill="#525252" className="mono">holds X</text>
        <line x1="200" y1="220" x2="480" y2="100" stroke="#DC2626" strokeDasharray="4 3" strokeWidth="1.6" markerEnd="url(#ahr)"/>
        <text x="320" y="170" fontSize="10" fill="#DC2626" className="mono">requests S — blocked</text>

        <line x1="580" y1="140" x2="520" y2="220" stroke="#737373" strokeWidth="1.6" markerEnd="url(#ahg)"/>
        <text x="555" y="190" fontSize="10" fill="#525252" className="mono">holds X</text>
        <line x1="520" y1="220" x2="240" y2="100" stroke="#DC2626" strokeDasharray="4 3" strokeWidth="1.6" markerEnd="url(#ahr)"/>
        <text x="360" y="210" fontSize="10" fill="#DC2626" className="mono">requests S — cycle</text>
      </svg>
    </div>
  );
}

function WorkbenchQueryPlan() {
  return (
    <div className="p-4">
      <div className="text-[12px] text-ink-500 mb-2">Execution plan · query #f3a2c1 · cost 2342.7</div>
      <div className="border hl2 rounded-md bg-white p-3 mono text-[12px] leading-[1.6]">
        <div className="flex items-center gap-2 mb-2"><Badge tone="err">Hot</Badge><span>SELECT cost 2342.7 · 234,891 logical reads</span></div>
        <pre className="text-[11.5px]">
{`SELECT  cost=2342.7  rows=89,302  reads=234,891
├─ Hash Match (Aggregate)        cost=412.0   rows=89.3K
│  └─ Hash Match (Inner Join)    cost=1842.0  rows=89.3K  WARN: spilled to tempdb
│     ├─ Clustered Index Scan _AccumRgT5634   cost=1240.5 rows=2.1M ◀ FULL SCAN
│     │     • Predicate: _Period >= @P1 AND _Period <= @P2  (not sargable on _Fld5640RRef)
│     │     • Missing index suggestion (impact 89%): IX_Period_Fld5640RRef INCLUDE(_Fld5642)
│     └─ Index Seek _Reference234.PK         cost=88.7    rows=24.3K
└─ Compute Scalar                 cost=12.3   rows=89.3K`}
        </pre>
      </div>
    </div>
  );
}

function WorkbenchCode() {
  return (
    <div className="grid grid-cols-2 gap-3 p-3">
      <div>
        <div className="text-[11px] mono text-ink-500 mb-1.5">Module: РасчётыСКонтрагентамиСервер · ОбщийМодуль · Server</div>
        <BSLBlock>{`Процедура ВыполнитьДвиженияРасчёты(Документ, Движения) Экспорт
    Запрос = Новый Запрос;
    Запрос.Текст =
        "ВЫБРАТЬ
        |    Расчёты.Контрагент,
        |    Расчёты.СуммаОстаток
        |ИЗ
        |    РегистрНакопления.РасчётыСКонтрагентами.Остатки() КАК Расчёты
        |ГДЕ
        |    Расчёты.Контрагент В (&Контрагенты)";
    Запрос.УстановитьПараметр("Контрагенты", Документ.КонтрагентыИзТЧ());
    Результат = Запрос.Выполнить();
    // ↑ виртуальная таблица без &Период — full scan
КонецПроцедуры`}</BSLBlock>
      </div>
      <div>
        <div className="text-[11px] mono text-ink-500 mb-1.5">Generated SQL · 1.81s · 234K reads</div>
        <SQLBlock>{`SELECT
  T1._Fld5640RRef AS Контрагент,
  SUM(T1._Fld5642) AS СуммаОстаток
FROM _AccumRgT5634 T1 WITH (NOLOCK, READUNCOMMITTED)
INNER JOIN @TVP_Контрагенты T2 ON T1._Fld5640RRef = T2.Value
WHERE T1._Active = 0x01
GROUP BY T1._Fld5640RRef
OPTION (RECOMPILE)`}</SQLBlock>
      </div>
    </div>
  );
}

function WorkbenchMetrics() {
  return (
    <div className="p-3 grid grid-cols-2 gap-3">
      {[
        {t:'CPU 1C cluster',  v:'67%', s:'avg 1h, peak 88%', d:[40,45,50,55,60,65,70,75,80,70,60,55,50,55,60,65,70,67,67]},
        {t:'CPU SQL server',  v:'82%', s:'peak 89%',         d:[55,60,65,70,75,80,85,80,75,80,85,90,85,80,75,80,85,82,82]},
        {t:'Memory cluster',  v:'15.5 GB',s:'allocated 24 GB',d:[12,12.5,13,13.5,14,14.2,14.5,14.8,15,15.2,15.3,15.4,15.4,15.5,15.5]},
        {t:'Disk IO SQL',     v:'82 MB/s',s:'reads 65, writes 17', d:[40,50,55,60,65,70,75,80,82,82,80,75,70,75,80,82]},
      ].map((m,i)=>(
        <Panel key={i} dense title={m.t} sub={m.s}>
          <Spark data={m.d} w={420} h={70} strokeW={1.4}/>
          <div className="display text-[28px] font-semibold mono tnum mt-1">{m.v}</div>
        </Panel>
      ))}
    </div>
  );
}

function EventsStream({ events }) {
  return (
    <div>
      <div className="px-2.5 h-7 border-b hl flex items-center gap-2 bg-white">
        <input placeholder="filter:  source=SQL severity>=warn …" className="flex-1 h-6 bg-ink-25 px-2 text-[11px] mono outline-none rounded border hl2"/>
        <SegGroup><SegBtn active>All</SegBtn><SegBtn>1С</SegBtn><SegBtn>SQL</SegBtn><SegBtn>System</SegBtn></SegGroup>
        <label className="text-[11px] text-ink-500 flex items-center gap-1"><input type="checkbox" defaultChecked/>auto-scroll</label>
      </div>
      <table className="w-full text-[11.5px]">
        <thead className="bg-ink-25 sticky top-0">
          <tr>
            <Th w="120px">Timestamp</Th>
            <Th w="60px">Source</Th>
            <Th w="60px">Sev</Th>
            <Th w="90px">Type</Th>
            <Th>Description</Th>
          </tr>
        </thead>
        <tbody>
          {events.map((e,i)=>(
            <tr key={i} className="row border-t hl">
              <Td mono className="text-ink-500">{e.t}</Td>
              <Td mono><Badge tone={e.src==='SQL'?'info':e.src==='1C'?'teal':'mute'}>{e.src}</Badge></Td>
              <Td><Sev level={e.sev} size={8}/></Td>
              <Td mono className="text-ink-600">{e.type}</Td>
              <Td className="mono text-ink-700 text-[11.5px]">{e.txt}</Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function WorkbenchAIChatInline() {
  return (
    <div className="p-3 text-[12.5px] space-y-2 max-w-[820px]">
      <div className="text-ink-500">AI · scoped to current investigation</div>
      <div className="bg-teal-50/40 border hl rounded-md p-2.5">
        <div className="flex items-center gap-1.5 mb-1 text-[11px] text-teal-800 mono font-semibold"><I.Sparkles size={11}/>AI</div>
        <p>За последние 24h pattern #1247 повторился <b>47 раз</b>. В 100% случаев <span className="mono">Реализация</span> и <span className="mono">КорректировкаДолга</span> модифицируют регистры в обратном порядке. Минимальный инвазивный fix — переупорядочить движения в <span className="mono">КорректировкаДолга.ОбработкаПроведения()</span> (поменять местами строки 124 и 138).</p>
        <div className="mt-2 flex gap-1.5">
          <button className="text-[11px] h-6 px-2 rounded border hl2 bg-white text-teal-700">Show diff</button>
          <button className="text-[11px] h-6 px-2 rounded border hl2 bg-white text-teal-700">Generate CFE</button>
          <button className="text-[11px] h-6 px-2 rounded border hl2 bg-white text-ink-600">Show similar patterns</button>
        </div>
      </div>
      <div className="flex items-center gap-2 border hl2 rounded-md px-2 py-1.5">
        <I.Sparkles size={13} className="text-teal-700"/>
        <input className="flex-1 bg-transparent outline-none text-[12.5px]" placeholder="Спросить по investigation…"/>
        <KBD>↵</KBD>
      </div>
    </div>
  );
}

function WorkbenchQueryInspector() {
  return (
    <div className="p-3 max-w-[800px]">
      <div className="text-[11px] mono text-ink-500 mb-2">Selected: query #f3a2c1 · sid 47 · 14:32:11</div>
      <SQLBlock>{`SELECT T1._Fld5640RRef, T1._Fld5641, SUM(T1._Fld5642)
FROM _AccumRgT5634 T1
WHERE T1._Period >= @P1 AND T1._Period <= @P2
GROUP BY T1._Fld5640RRef, T1._Fld5641`}</SQLBlock>
      <div className="mt-2 grid grid-cols-4 gap-2 text-[11px] mono">
        <Stat label="duration" value="1.81s" tone="warn"/>
        <Stat label="logical reads" value="234,891"/>
        <Stat label="cpu time" value="780 ms"/>
        <Stat label="rows" value="89,302"/>
      </div>
    </div>
  );
}

function Stat({label, value, tone}) {
  return <div className="border hl2 rounded px-2 py-1.5">
    <div className="text-[10px] text-ink-400 uppercase tracking-wider">{label}</div>
    <div className={`tnum font-semibold text-[14px] ${tone==='warn'?'text-warn':tone==='err'?'text-err':'text-ink-900'}`}>{value}</div>
  </div>;
}

function WorkbenchConsole() {
  return (
    <div className="p-3 mono text-[11.5px] leading-relaxed text-ink-700">
      <div className="text-ink-400">// OptimyzerQL inline shell — выполнить запрос против live данных</div>
      <div><span className="text-teal-700">{'>'}</span> events | where Type == "deadlock" | timerange 1h | count by victim_session</div>
      <div className="text-ink-400">// → 4 rows</div>
      <pre className="text-[11px]">{`sid_47   3
sid_89   0
sid_112  1
sid_131  0`}</pre>
      <div><span className="text-teal-700">{'>'}</span> <span className="bg-ink-50 px-1">_</span></div>
    </div>
  );
}

function DeadlockInspector() {
  return (
    <div className="p-3">
      <div className="text-[10px] mono uppercase tracking-wider text-ink-400 mb-1">Selected event</div>
      <div className="flex items-center gap-2">
        <Badge tone="err">CRITICAL</Badge>
        <Badge tone="mute" mono>#1247</Badge>
      </div>
      <h3 className="text-[15px] font-semibold mt-1.5">Deadlock — 14:32:14.821</h3>
      <p className="text-[11.5px] text-ink-500 mt-0.5 leading-snug">2 sessions · 2 tables · session 47 chosen as victim · rolled back 14:32:14.832 (11ms)</p>

      <div className="div-h my-3"></div>

      <div className="flex items-center gap-1.5 mb-1.5">
        <I.Sparkles size={12} className="text-teal-700"/>
        <span className="text-[11px] font-semibold mono text-teal-800">AI Analysis</span>
        <Badge tone="ok" className="ml-auto">conf: high</Badge>
      </div>
      <div className="text-[11.5px] leading-relaxed text-ink-700 space-y-2">
        <p>Транзакция <b>A</b> (sid 47, Иванов) выполняла <span className="mono">Документ.РеализацияТоваровУслуг.ОбработкаПроведения()</span>. Удерживала <b>X-lock</b> на <span className="mono">_AccumRgT5634</span> (РасчётыСКонтрагентами). Запросила <b>S-lock</b> на <span className="mono">_AccumRgT5891</span> (Взаиморасчёты).</p>
        <p>Транзакция <b>B</b> (sid 89, Петров) выполняла <span className="mono">Документ.КорректировкаДолга.ОбработкаПроведения()</span>. Удерживала X на <span className="mono">_AccumRgT5891</span>, запросила S на <span className="mono">_AccumRgT5634</span>.</p>
        <p><b>Root cause:</b> разный порядок изменения регистров в двух процедурах <span className="mono">ОбработкаПроведения()</span>. Цикл блокировок неизбежен при пересечении партий.</p>
      </div>
      <button className="mt-2 text-[11px] text-teal-700 hover:underline flex items-center gap-1">Show full reasoning <I.ArrowRight size={11}/></button>

      <div className="div-h my-3"></div>

      <div className="text-[10px] mono uppercase tracking-wider text-ink-400 mb-1">Related</div>
      <ul className="text-[11.5px] space-y-1.5">
        <li className="flex justify-between"><span>this pattern (24h)</span><span className="mono tnum text-err font-semibold">47×</span></li>
        <li className="flex justify-between"><span>this pattern (7d)</span><span className="mono tnum">312×</span></li>
        <li className="flex justify-between"><span>similar (other pairs)</span><span className="mono tnum">12</span></li>
      </ul>

      <div className="div-h my-3"></div>

      <div className="text-[10px] mono uppercase tracking-wider text-ink-400 mb-1">Recommendations</div>
      <ol className="space-y-2 text-[12px]">
        <li className="border hl2 rounded p-2">
          <div className="flex items-center gap-1.5"><Badge tone="teal">RECOMMENDED</Badge><span className="font-semibold">Code fix</span></div>
          <div className="text-[11.5px] text-ink-600 mt-1">Унифицировать порядок изменения регистров. Поменять местами вызовы в <span className="mono">КорректировкаДолга</span> строки 124↔138.</div>
          <div className="mt-1.5 flex gap-1.5"><button className="text-[11px] h-6 px-2 rounded border hl2 bg-teal-50 text-teal-700">Show diff →</button></div>
        </li>
        <li className="border hl2 rounded p-2">
          <div className="font-semibold text-[12px]">Schema redesign</div>
          <div className="text-[11.5px] text-ink-600 mt-1">Объединить регистры <span className="mono">РасчётыСКонтрагентами</span> и <span className="mono">Взаиморасчёты</span> — они часто меняются совместно.</div>
        </li>
        <li className="border hl2 rounded p-2 opacity-75">
          <div className="font-semibold text-[12px]">Workaround</div>
          <div className="text-[11.5px] text-ink-600 mt-1">Сериализовать выполнение проведений этих документов (Управляемая транзакция · Семафор).</div>
        </li>
      </ol>

      <div className="div-h my-3"></div>

      <div className="grid grid-cols-2 gap-1.5">
        <button className="text-[11.5px] h-7 border hl2 rounded hover:bg-ink-50 flex items-center justify-center gap-1.5"><I.Lock size={11}/>Lock Graph</button>
        <button className="text-[11.5px] h-7 border hl2 rounded hover:bg-ink-50 flex items-center justify-center gap-1.5"><I.Code size={11}/>BSL Code</button>
        <button className="text-[11.5px] h-7 border hl2 rounded bg-teal-700 text-white hover:bg-teal-800 flex items-center justify-center gap-1.5 col-span-2"><I.Sparkles size={11}/>Generate Fix as CFE</button>
        <button className="text-[11.5px] h-7 border hl2 rounded hover:bg-ink-50 flex items-center justify-center gap-1.5"><I.Eye size={11}/>Investigating</button>
        <button className="text-[11.5px] h-7 border hl2 rounded hover:bg-ink-50 flex items-center justify-center gap-1.5"><I.Bookmark size={11}/>Add to Watch</button>
      </div>
    </div>
  );
}

window.WorkbenchScreen = WorkbenchScreen;
