/* SCREEN 5: Locks & Deadlocks Center */
function LocksScreen() {
  const [tab, setTab] = React.useState('patterns');

  const patterns = [
    { id:'#1247', a:'Документ.РеализацияТоваровУслуг', b:'Документ.КорректировкаДолга', d24:47, d7:312, sev:'err',  cause:'разный порядок изменения регистров РасчётыСКонтрагентами и Взаиморасчёты' },
    { id:'#892',  a:'Документ.ПоступлениеТоваровУслуг', b:'Документ.ВнутреннееПеремещение', d24:8,  d7:34,  sev:'warn', cause:'одновременная запись в РегистрНакопления.ТоварыНаСкладах' },
    { id:'#1031', a:'Документ.РеализацияТоваровУслуг', b:'Регламент.ЗакрытиеМесяца',          d24:6,  d7:21,  sev:'warn', cause:'эскалация блокировок при пересчёте итогов' },
    { id:'#774',  a:'Документ.НачислениеЗарплаты',     b:'Документ.КорректировкаЗарплаты',     d24:3,  d7:14,  sev:'mute', cause:'разный порядок чтения справочника Сотрудники' },
    { id:'#921',  a:'Документ.ОприходованиеТоваров',   b:'Документ.СписаниеТоваров',           d24:2,  d7:9,   sev:'mute', cause:'параллельное движение по партиям' },
    { id:'#1188', a:'Документ.ВнутреннееПеремещение',  b:'Документ.ВнутреннееПеремещение',     d24:1,  d7:7,   sev:'mute', cause:'self-cycle при batched processing' },
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-48px-28px)]">
      <PageHeader breadcrumbs={['Analyze','Locks & Deadlocks']} title="Locks & Deadlocks Center"
        sub="real-time lock topology · 7-day pattern grouping"
        kpis={<>
          <KPI label="DEADLOCKS / 24H" value="67" sub="up from 41 yesterday" tone="err"/>
          <KPI label="DEADLOCKS / 7D" value="397" sub="+18% vs week prior" tone="warn"/>
          <KPI label="ACTIVE BLOCKED" value="2" sub="lead blocker sid 89"/>
          <KPI label="LONGEST LOCK WAIT" value="3.4 s" sub="LCK_M_X · _AccumRgT5634"/>
        </>}
        right={<>
          <SegGroup><SegBtn>1h</SegBtn><SegBtn active>24h</SegBtn><SegBtn>7d</SegBtn><SegBtn>30d</SegBtn></SegGroup>
        </>}/>

      <Tabs value={tab} onChange={setTab} tabs={[
        { id:'patterns', label:'Patterns', icon:I.Layers, count:6 },
        { id:'live',     label:'Live Locks', icon:I.Lock, count:2 },
        { id:'history',  label:'Deadlock History', icon:I.Activity, count:397 },
        { id:'heatmap',  label:'Heatmap', icon:I.Trend },
      ]}/>

      <div className="flex-1 overflow-auto p-3 bg-ink-25">
        {tab==='patterns' && (
          <div className="grid grid-cols-2 gap-3">
            {patterns.map((p,i)=>(
              <div key={p.id} className={`bg-white border ${p.sev==='err'?'border-err/30':p.sev==='warn'?'border-warn/30':'hl2'} rounded-md shadow-panel p-3.5`}>
                <div className="flex items-start gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <Badge tone={p.sev==='err'?'err':p.sev==='warn'?'warn':'mute'} mono>{p.id}</Badge>
                      <span className="text-[11px] text-ink-500 mono">deadlock pattern</span>
                      <Badge tone="mute" className="ml-1">{p.sev==='err'?'Critical':p.sev==='warn'?'Elevated':'Low'}</Badge>
                    </div>
                    <h3 className="text-[14px] font-semibold mt-2 leading-snug">
                      <span className="mono">{p.a}</span>
                      <span className="text-ink-400 mx-1.5">↔</span>
                      <span className="mono">{p.b}</span>
                    </h3>
                    <div className="text-[11.5px] text-ink-500 mt-1">{p.cause}</div>
                  </div>
                  <PatternMiniGraph sev={p.sev}/>
                </div>

                <div className="mt-3 grid grid-cols-4 gap-2">
                  <div><div className="mono text-[10px] text-ink-400 uppercase tracking-wider">24h</div><div className={`mono tnum font-semibold text-[18px] ${p.sev==='err'?'text-err':p.sev==='warn'?'text-warn':'text-ink-900'}`}>{p.d24}</div></div>
                  <div><div className="mono text-[10px] text-ink-400 uppercase tracking-wider">7d</div><div className="mono tnum font-semibold text-[18px]">{p.d7}</div></div>
                  <div><div className="mono text-[10px] text-ink-400 uppercase tracking-wider">trend</div><Spark data={Array.from({length:18},()=>Math.random())} w={80} h={26}/></div>
                  <div className="flex flex-col items-end justify-end">
                    <button className="text-[12px] h-7 px-2 border hl2 rounded text-teal-700 bg-teal-50 hover:bg-teal-100 flex items-center gap-1">Investigate <I.ArrowRight size={11}/></button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
        {tab==='live' && <LiveLocks/>}
        {tab==='history' && <DeadlockHistory/>}
        {tab==='heatmap' && (
          <div className="bg-white border hl2 rounded-md p-4 shadow-panel">
            <div className="text-[12px] text-ink-500 mb-2">Deadlocks · day × hour · last 30 days</div>
            <Heatmap data={Array.from({length:7},(_,d)=>Array.from({length:24},(_,h)=>{
              const peak = (h>=9&&h<=12 && d<5) ? 0.92 : (h>=14&&h<=17 && d<5) ? 0.6 : (h<6||h>21) ? 0.05 : 0.25;
              return Math.min(1, peak + (Math.random()*0.15 - 0.05));
            }))} w={900} h={220}/>
            <div className="mt-3 text-[11.5px] text-ink-500">Pattern: peak load Mon–Fri 09:00–12:00 → 41 deadlocks/hour. Recommend ограничить пиковую нагрузку или применить fix паттерна #1247.</div>
          </div>
        )}
      </div>
    </div>
  );
}

function PatternMiniGraph({ sev }) {
  const c = sev==='err'?'#DC2626':sev==='warn'?'#D97706':'#737373';
  return (
    <svg viewBox="0 0 110 80" width="110" height="80" className="ml-auto shrink-0">
      <defs>
        <marker id={`mg-${sev}`} markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill={c}/>
        </marker>
      </defs>
      <circle cx="25" cy="20" r="10" fill="#FFFFFF" stroke={c} strokeWidth="1.5"/>
      <text x="25" y="23" textAnchor="middle" fontSize="9" className="mono" fill="#0A0A0A">A</text>
      <circle cx="85" cy="20" r="10" fill="#FFFFFF" stroke={c} strokeWidth="1.5"/>
      <text x="85" y="23" textAnchor="middle" fontSize="9" className="mono" fill="#0A0A0A">B</text>
      <circle cx="25" cy="60" r="10" fill="#FFFFFF" stroke="#A3A3A3" strokeWidth="1.2"/>
      <text x="25" y="63" textAnchor="middle" fontSize="9" className="mono" fill="#525252">R1</text>
      <circle cx="85" cy="60" r="10" fill="#FFFFFF" stroke="#A3A3A3" strokeWidth="1.2"/>
      <text x="85" y="63" textAnchor="middle" fontSize="9" className="mono" fill="#525252">R2</text>
      <line x1="25" y1="30" x2="25" y2="50" stroke="#737373" strokeWidth="1.2"/>
      <line x1="85" y1="30" x2="85" y2="50" stroke="#737373" strokeWidth="1.2"/>
      <line x1="35" y1="60" x2="75" y2="22" stroke={c} strokeDasharray="2 2" strokeWidth="1.2" markerEnd={`url(#mg-${sev})`}/>
      <line x1="75" y1="60" x2="35" y2="22" stroke={c} strokeDasharray="2 2" strokeWidth="1.2" markerEnd={`url(#mg-${sev})`}/>
    </svg>
  );
}

function LiveLocks() {
  return (
    <div className="grid grid-cols-3 gap-3">
      <div className="col-span-2 bg-white border hl2 rounded-md shadow-panel p-3">
        <div className="text-[12px] text-ink-500 mb-2">Active lock graph · 2 blocked, 5 waiters</div>
        <svg viewBox="0 0 720 360" className="w-full">
          {/* nodes — sessions */}
          <SessionNode x={120} y={70}  sid="47"  user="Иванов И.С." state="blocked" duration="3.4s"/>
          <SessionNode x={120} y={220} sid="89"  user="Петров А.В." state="lead-blocker" duration="0s"/>
          <SessionNode x={400} y={50}  sid="112" user="Сидорова Е.А." state="waiting" duration="1.1s"/>
          <SessionNode x={400} y={160} sid="124" user="Морозов Д.С."  state="waiting" duration="0.8s"/>
          <SessionNode x={400} y={270} sid="131" user="Кузнецова О.Н." state="waiting" duration="2.2s"/>
          <SessionNode x={620} y={160} sid="89"  user="Петров А.В."   state="holding" duration="—"/>
          {/* edges */}
          {[[200,70, 320,50],[200,70, 320,160],[200,220, 320,270],[480,50, 540,160],[480,160, 540,160],[480,270, 540,160]].map((c,i)=>(
            <line key={i} x1={c[0]} y1={c[1]} x2={c[2]} y2={c[3]} stroke="#D4D4D4" strokeWidth="1.4"/>
          ))}
        </svg>
      </div>
      <div className="bg-white border hl2 rounded-md shadow-panel p-3">
        <div className="text-[12px] font-semibold mb-2">Top resources contended</div>
        <ul className="space-y-2 text-[11.5px]">
          {[
            { name:'_AccumRgT5634', desc:'РасчётыСКонтрагентами', waits:'3.4s', tone:'err' },
            { name:'_AccumRgT5891', desc:'Взаиморасчёты', waits:'2.2s', tone:'warn' },
            { name:'_Reference234', desc:'Контрагенты', waits:'1.1s', tone:'warn' },
            { name:'_InfoRg5891',   desc:'НастройкиПартионногоУчёта', waits:'0.6s', tone:'mute' },
          ].map((r,i)=>(
            <li key={i} className="border hl2 rounded p-2">
              <div className="flex items-center justify-between">
                <span className="mono font-semibold">{r.name}</span>
                <span className={`mono tnum text-[11px] ${r.tone==='err'?'text-err':r.tone==='warn'?'text-warn':'text-ink-500'}`}>{r.waits}</span>
              </div>
              <div className="text-[10.5px] text-ink-500">{r.desc}</div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function SessionNode({ x, y, sid, user, state, duration }) {
  const palette = {
    'blocked':     { stroke:'#DC2626', bg:'#FEF2F2' },
    'lead-blocker':{ stroke:'#D97706', bg:'#FFFBEB' },
    'waiting':     { stroke:'#737373', bg:'#FFFFFF' },
    'holding':     { stroke:'#0F766E', bg:'#F0FDFA' },
  }[state];
  return (
    <g>
      <rect x={x-80} y={y-26} width="160" height="52" rx="6" fill={palette.bg} stroke={palette.stroke}/>
      <text x={x} y={y-8} textAnchor="middle" fontSize="11" fontWeight="600" fill="#0A0A0A" className="mono">sid {sid}</text>
      <text x={x} y={y+6} textAnchor="middle" fontSize="10" fill="#525252">{user}</text>
      <text x={x} y={y+20} textAnchor="middle" fontSize="9.5" fill={palette.stroke} className="mono">{state} · {duration}</text>
    </g>
  );
}

function DeadlockHistory() {
  const rows = [
    { id:'#15089', t:'14:32:14', pattern:'#1247', a:'Реализация', b:'КорректировкаДолга', victim:'sid 47', dur:'11 ms' },
    { id:'#15088', t:'13:58:02', pattern:'#1247', a:'Реализация', b:'КорректировкаДолга', victim:'sid 64', dur:'8 ms' },
    { id:'#15087', t:'13:41:55', pattern:'#892',  a:'ПоступлениеТоваров', b:'ВнутреннееПеремещение', victim:'sid 112', dur:'14 ms' },
    { id:'#15086', t:'13:20:39', pattern:'#1247', a:'Реализация', b:'КорректировкаДолга', victim:'sid 78', dur:'9 ms' },
    { id:'#15085', t:'12:55:41', pattern:'#1031', a:'Реализация', b:'ЗакрытиеМесяца', victim:'sid 131', dur:'42 ms' },
    { id:'#15084', t:'12:33:12', pattern:'#1247', a:'Реализация', b:'КорректировкаДолга', victim:'sid 88', dur:'7 ms' },
    { id:'#15083', t:'12:11:48', pattern:'#774',  a:'НачислениеЗарплаты', b:'КорректировкаЗарплаты', victim:'sid 24', dur:'18 ms' },
    { id:'#15082', t:'11:54:19', pattern:'#1247', a:'Реализация', b:'КорректировкаДолга', victim:'sid 102', dur:'12 ms' },
    { id:'#15081', t:'11:32:00', pattern:'#892',  a:'ПоступлениеТоваров', b:'ВнутреннееПеремещение', victim:'sid 47', dur:'11 ms' },
  ];
  return (
    <Panel pad={false} title="Deadlock history" sub="last 24h · 67 events">
      <table className="w-full text-[12px]">
        <thead className="bg-ink-25">
          <tr>
            <Th w="90px">ID</Th>
            <Th w="80px">Time</Th>
            <Th w="80px">Pattern</Th>
            <Th>Document A</Th>
            <Th>Document B</Th>
            <Th w="100px">Victim</Th>
            <Th w="80px" align="right">Duration</Th>
            <Th w="40px"></Th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r=>(
            <tr key={r.id} className="row border-t hl cursor-pointer">
              <Td mono className="text-ink-500">{r.id}</Td>
              <Td mono>{r.t}</Td>
              <Td><Badge tone="mute" mono>{r.pattern}</Badge></Td>
              <Td><span className="mono text-[11.5px]">{r.a}</span></Td>
              <Td><span className="mono text-[11.5px]">{r.b}</span></Td>
              <Td mono>{r.victim}</Td>
              <Td mono align="right" className="tnum">{r.dur}</Td>
              <Td><I.ChevronRight size={12} className="text-ink-300"/></Td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}

window.LocksScreen = LocksScreen;
