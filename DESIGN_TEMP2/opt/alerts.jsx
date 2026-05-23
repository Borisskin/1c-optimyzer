/* SCREEN 16: Alerts & Incidents */
function AlertsScreen() {
  const [sel, setSel] = React.useState(0);

  const alerts = [
    { id:'#1247', t:'14:32', sev:'err',  type:'Deadlock',     title:'Recurring pattern Реализация ↔ КорректировкаДолга', status:'Investigating', owner:'Иванов И.С.' },
    { id:'#1246', t:'14:18', sev:'err',  type:'Memory Leak',  title:'rphost #3 +45 MB/min over 1h',                       status:'Open',          owner:'—' },
    { id:'#1245', t:'13:47', sev:'warn', type:'Slow Query',   title:'СформироватьТаблицуРасчётов — 4.2 s avg',             status:'Resolved',      owner:'Петрова Е.А.' },
    { id:'#1244', t:'13:22', sev:'info', type:'Apdex',        title:'Apdex dropped 0.91 → 0.78 over 12 min',               status:'Auto-resolved', owner:'system' },
    { id:'#1243', t:'12:55', sev:'info', type:'Schedule',     title:'Apdex collection timeout (transient)',                status:'Auto-resolved', owner:'system' },
    { id:'#1242', t:'12:33', sev:'warn', type:'Long Call',    title:'ЗакрытиеМесяца.Выполнить() — 340s, sid 131',          status:'Acknowledged',  owner:'Морозов Д.С.' },
    { id:'#1241', t:'12:11', sev:'err',  type:'Deadlock',     title:'Pattern #892 — Поступление ↔ ВнутреннееПеремещение', status:'Investigating', owner:'Сидорова Е.А.' },
    { id:'#1240', t:'11:48', sev:'warn', type:'CPU',          title:'rphost #4 sustained CPU > 80% (12 min)',             status:'Resolved',      owner:'Иванов И.С.' },
    { id:'#1239', t:'10:55', sev:'warn', type:'Tempdb',       title:'Tempdb usage > 8 GB (cursor reports)',                status:'Open',          owner:'—' },
    { id:'#1238', t:'10:14', sev:'info', type:'Index',        title:'Auto-applied: UPDATE STATISTICS _Document156',        status:'Auto-resolved', owner:'system' },
    { id:'#1237', t:'09:48', sev:'err',  type:'Connection',   title:'5 sessions disconnected unexpectedly · 30s',         status:'Resolved',      owner:'Кузнецова О.Н.' },
    { id:'#1236', t:'09:22', sev:'warn', type:'Slow Query',   title:'СрезПоследних() — 1.2 s · ЦенообразованиеСервер',     status:'Resolved',      owner:'Петрова Е.А.' },
  ];

  const rules = [
    { name:'Apdex < 0.80 for 5 min',         ch:['Email','Telegram'], priority:'critical', enabled:true,  fires:'4 in 24h' },
    { name:'New deadlock pattern (>10/h)',   ch:['Telegram'],         priority:'critical', enabled:true,  fires:'1 in 24h' },
    { name:'Memory growth > 50 MB/h rphost', ch:['Email'],            priority:'warning',  enabled:true,  fires:'1 in 24h' },
    { name:'Slow query family > 1s p95',     ch:['Email'],            priority:'warning',  enabled:true,  fires:'12 in 24h' },
    { name:'SQL CPU > 80% for 10 min',       ch:['Telegram'],         priority:'warning',  enabled:true,  fires:'2 in 24h' },
    { name:'Disk free < 20 GB',              ch:['Email','SMS'],      priority:'critical', enabled:true,  fires:'0' },
    { name:'rphost restart',                 ch:['Telegram'],         priority:'warning',  enabled:false, fires:'1 in 24h' },
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-48px-28px)]">
      <PageHeader breadcrumbs={['Manage','Alerts']} title="Alerts & Incidents"
        sub="real-time alerts · routing rules · incident history"
        kpis={<>
          <KPI label="OPEN" value="4" sub="2 critical" tone="err"/>
          <KPI label="ACKNOWLEDGED" value="2" sub="avg 8m to ack"/>
          <KPI label="RESOLVED TODAY" value="14" sub="MTTR 18 min"/>
          <KPI label="NOISE RATIO" value="6%" sub="auto-resolved transients"/>
        </>}/>

      <div className="flex-1 grid grid-cols-[220px_1fr_320px] overflow-hidden">
        {/* Quick filters */}
        <aside className="border-r hl bg-white overflow-y-auto">
          <FilterGroup name="Severity" items={[['Critical',2],['Warning',5],['Info',5]]}/>
          <FilterGroup name="Status"   items={[['Open',4],['Investigating',2],['Acknowledged',1],['Resolved',8]]}/>
          <FilterGroup name="Type"     items={[['Deadlock',2],['Slow Query',2],['Memory',1],['CPU',1],['Apdex',1],['System',5]]}/>
          <FilterGroup name="Owner"    items={[['Me',3],['Team Perf',7],['Unassigned',2]]}/>
          <div className="px-3 py-2 border-b hl">
            <div className="text-[10px] mono uppercase tracking-wider text-ink-400 mb-1.5">Saved filters</div>
            <ul className="space-y-1 text-[11.5px]">
              {['Critical · last 24h','Mine · open','Auto-resolved transients','By pattern #1247'].map(s=>(
                <li key={s}><button className="text-teal-700 hover:underline">{s}</button></li>
              ))}
            </ul>
          </div>
        </aside>

        {/* Center: alerts list */}
        <section className="overflow-auto bg-white">
          <table className="w-full text-[12px]">
            <thead className="bg-ink-25 sticky top-0">
              <tr>
                <Th w="74px">ID</Th>
                <Th w="50px">Time</Th>
                <Th w="40px">Sev</Th>
                <Th w="100px">Type</Th>
                <Th>Title</Th>
                <Th w="120px">Status</Th>
                <Th w="120px">Owner</Th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a,i)=>(
                <tr key={i} className="row border-t hl cursor-pointer" data-active={i===sel?'1':'0'} onClick={()=>setSel(i)}>
                  <Td mono className="text-ink-500">{a.id}</Td>
                  <Td mono>{a.t}</Td>
                  <Td><Sev level={a.sev} size={9}/></Td>
                  <Td mono>{a.type}</Td>
                  <Td className="text-[12px]">{a.title}</Td>
                  <Td><Badge tone={a.status==='Open'?'err':a.status==='Investigating'?'warn':a.status==='Acknowledged'?'info':'ok'}>{a.status}</Badge></Td>
                  <Td className="text-[11.5px] text-ink-600">{a.owner}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {/* Right: rules */}
        <aside className="border-l hl bg-white overflow-y-auto">
          <div className="px-3 h-9 border-b hl flex items-center">
            <span className="text-[12.5px] font-semibold">Active rules</span>
            <button className="ml-auto h-6 px-2 text-[11px] rounded border hl2 text-teal-700 hover:bg-teal-50 flex items-center gap-1"><I.Plus size={11}/>Add</button>
          </div>
          <ul className="divide-y divide-ink-100">
            {rules.map((r,i)=>(
              <li key={i} className={`px-3 py-2.5 ${!r.enabled?'opacity-60':''}`}>
                <div className="flex items-center gap-1.5 mb-0.5">
                  <Badge tone={r.priority==='critical'?'err':'warn'}>{r.priority}</Badge>
                  <span className="ml-auto text-[10.5px] mono text-ink-400">{r.fires}</span>
                </div>
                <div className="text-[12px] mono">{r.name}</div>
                <div className="mt-1 flex items-center gap-1.5">
                  {r.ch.map(c=>(<Badge key={c} tone="mute" mono>{c}</Badge>))}
                  <label className="ml-auto flex items-center gap-1.5 text-[10.5px] mono text-ink-500">
                    <span className={`w-6 h-3.5 rounded-full ${r.enabled?'bg-teal-700':'bg-ink-200'} relative inline-block`}>
                      <span className={`absolute ${r.enabled?'right-0.5':'left-0.5'} top-0.5 w-2.5 h-2.5 rounded-full bg-white`}/>
                    </span>
                  </label>
                </div>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </div>
  );
}
window.AlertsScreen = AlertsScreen;
