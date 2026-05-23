/* SCREEN 15: Knowledge Base & Community */
function KnowledgeScreen() {
  const [tab, setTab] = React.useState('browse');

  const cases = [
    { title:'Slow query in virtual table Остатки() without period filter', tags:['УТ 11.5','BSL','Virtual Tables'], author:'1С:Эксперт И.Иванов', cert:true, votes:247, linked:12, cat:'Performance', sev:'err' },
    { title:'Deadlock between Реализация and КорректировкаДолга',          tags:['УТ','Deadlock','Регистры'],     author:'1С:Эксперт М.Соколов', cert:true, votes:184, linked:9,  cat:'Locking',     sev:'err' },
    { title:'Memory leak in rphost on большой обмен данными РИБ',         tags:['Платформа','RIB','Memory'],     author:'Старший DBA А.Семёнов', cert:false,votes:96,  linked:5,  cat:'Cluster',     sev:'warn' },
    { title:'Missing index after upgrade to platform 8.3.25',              tags:['Платформа','SQL','Indexes'],    author:'1С:Эксперт И.Иванов', cert:true, votes:142, linked:7,  cat:'Performance', sev:'warn' },
    { title:'Закрытие месяца — оптимизация РассчитатьСебестоимость()',     tags:['УТ','БП','Performance','Closing'],author:'Performance Engineer Е.Кузнецова', cert:false, votes:312, linked:23, cat:'Architecture', sev:'err' },
    { title:'Lock escalation при пересчёте итогов больших регистров',      tags:['Locking','MSSQL'],              author:'1С:Эксперт П.Иванов', cert:true, votes:88,  linked:4,  cat:'Locking',     sev:'warn' },
    { title:'Best practice: правильное использование Запрос.Кэш',         tags:['BSL','Best Practice'],          author:'Performance Engineer Е.Кузнецова', cert:false, votes:198, linked:11, cat:'Best Practice', sev:'info' },
    { title:'Tempdb pressure от cursor-based reports',                     tags:['MSSQL','Tempdb'],               author:'DBA Д.Морозов',         cert:false, votes:64,  linked:3,  cat:'SQL Server',  sev:'warn' },
  ];

  return (
    <div>
      <PageHeader breadcrumbs={['Manage','Knowledge Base']} title="Knowledge Base & Community"
        sub="2,847 cases · 412 contributors · ваш вклад: 18 cases"
        kpis={<>
          <KPI label="MY CASES" value="18" sub="3 cited this month"/>
          <KPI label="FOLLOWED PATTERNS" value="34" sub="auto-alerts on match"/>
          <KPI label="HELPFUL VOTES" value="1,247" sub="all-time"/>
          <KPI label="REPUTATION" value="Senior" sub="top 8% community"/>
        </>}
        right={<>
          <button className="h-7 px-2 text-[11px] border hl2 rounded text-ink-600 hover:bg-ink-50 flex items-center gap-1"><I.Plus size={11}/>Submit case</button>
        </>}/>

      <Tabs value={tab} onChange={setTab} tabs={[
        { id:'browse',    label:'Browse',    icon:I.Book, count:2847 },
        { id:'mycases',   label:'My Cases',  icon:I.User, count:18 },
        { id:'community', label:'Community', icon:I.Globe, count:'live' },
        { id:'submit',    label:'Submit Case', icon:I.Plus },
      ]}/>

      {tab==='browse' && (
        <div className="grid grid-cols-[260px_1fr] gap-3 p-3">
          {/* Filters */}
          <aside className="bg-white border hl2 rounded-md shadow-panel">
            <div className="px-3 py-2 border-b hl">
              <input placeholder="search 2,847 cases…" className="w-full h-7 px-2 text-[11.5px] mono border hl2 rounded"/>
            </div>
            <FilterGroup name="Category" items={[
              ['Performance', 1284],
              ['Locking', 412],
              ['Architecture', 298],
              ['SQL Server', 354],
              ['Cluster', 178],
              ['Best Practice', 244],
            ]}/>
            <FilterGroup name="Configuration" items={[
              ['УТ 11.5', 894],
              ['ERP 2.5', 712],
              ['БП 3.0', 482],
              ['УНФ 3.0', 184],
              ['Cross-config', 575],
            ]}/>
            <FilterGroup name="Severity" items={[
              ['Critical', 234],
              ['Warning', 1024],
              ['Info', 1589],
            ]}/>
            <FilterGroup name="Author" items={[
              ['1С:Эксперт', 1342],
              ['DBA', 521],
              ['Perf engineer', 612],
              ['Community', 372],
            ]}/>
          </aside>

          {/* Results */}
          <div className="space-y-2.5">
            <div className="flex items-center gap-2 text-[11.5px] text-ink-500 px-1">
              <span className="mono">2,847 results</span>
              <span className="mx-1">·</span>
              <SegGroup><SegBtn active>Most helpful</SegBtn><SegBtn>Recent</SegBtn><SegBtn>Most linked</SegBtn></SegGroup>
            </div>

            {cases.map((c,i)=>(
              <article key={i} className="bg-white border hl2 rounded-md shadow-panel p-3 hover:border-teal-700/30 cursor-pointer">
                <div className="flex items-start gap-3">
                  <div className="flex flex-col items-center pt-0.5 w-12 shrink-0">
                    <button className="text-ink-400 hover:text-teal-700"><I.Trend size={14}/></button>
                    <span className="mono tnum text-[14px] font-semibold">{c.votes}</span>
                    <span className="mono text-[10px] text-ink-400 -mt-0.5">helpful</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-1">
                      <Badge tone={c.sev}>{c.cat}</Badge>
                      {c.tags.map((t,j)=>(<Badge key={j} tone="mute" mono>{t}</Badge>))}
                    </div>
                    <h3 className="text-[14px] font-semibold leading-snug">{c.title}</h3>
                    <div className="mt-2 flex items-center gap-3 text-[11px] text-ink-500">
                      <span className="flex items-center gap-1.5">
                        <span className="w-4 h-4 rounded-full bg-teal-700 text-white text-[8px] grid place-items-center">{c.author.split(' ').slice(-1)[0][0]}</span>
                        {c.author}
                        {c.cert && <span className="text-teal-700 mono">●cert</span>}
                      </span>
                      <span>·</span>
                      <span className="mono">{c.linked} linked cases</span>
                      <span>·</span>
                      <span>2 weeks ago</span>
                      <button className="ml-auto text-teal-700 hover:underline flex items-center gap-0.5 mono">Read <I.ArrowRight size={10}/></button>
                    </div>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>
      )}

      {tab==='community' && (
        <div className="p-3 grid grid-cols-3 gap-3">
          <Panel className="col-span-2" title="Похожие проблемы в системах других пользователей" sub="anonymized · realtime">
            <ul className="divide-y divide-ink-100">
              {[
                ['Deadlock between Реализация и КорректировкаДолга', '12 систем сейчас расследуют', 'err'],
                ['Slow query в виртуальной таблице Остатки()',       '34 системы наблюдают',         'warn'],
                ['Memory leak in rphost на больших обменах',          '5 систем сейчас расследуют',  'warn'],
                ['Stale statistics на _AccumRgT5634',                 '88 систем имели в прошлом',   'mute'],
                ['Lock escalation на пересчёте итогов',              '23 системы наблюдают',         'warn'],
              ].map((r,i)=>(
                <li key={i} className="py-2.5 flex items-center gap-2">
                  <Sev level={r[2]} size={8}/>
                  <span className="text-[12.5px]">{r[0]}</span>
                  <span className="ml-auto text-[11px] mono text-ink-500">{r[1]}</span>
                  <button className="text-[11px] text-teal-700 hover:underline mono">Compare →</button>
                </li>
              ))}
            </ul>
          </Panel>
          <Panel title="Solution exchange" sub="trending fixes · last 7 days">
            <ul className="space-y-2 text-[12px]">
              {[
                ['CFE: virtual table period fix', '34 applies', 'teal'],
                ['Index seed for РасчётыСКонтрагентами', '47 applies', 'teal'],
                ['Refactor of СформироватьТаблицуРасчётов', '12 applies', 'info'],
              ].map((r,i)=>(
                <li key={i} className="border hl2 rounded p-2">
                  <div className="flex items-center gap-1.5">
                    <Badge tone={r[2]}>{r[1]}</Badge>
                  </div>
                  <div className="text-[12px] mt-0.5 font-medium">{r[0]}</div>
                  <button className="mt-1 text-[11px] text-teal-700 hover:underline mono">Try in test base →</button>
                </li>
              ))}
            </ul>
          </Panel>
        </div>
      )}

      {tab==='mycases' && <div className="p-6 text-[12px] text-ink-500">18 опубликованных кейсов · 3 в работе</div>}

      {tab==='submit' && (
        <div className="p-3 max-w-[820px]">
          <Panel title="Submit case to community" sub="ваш опыт поможет другим">
            <form className="space-y-3 text-[12px]">
              <div>
                <label className="block text-[10.5px] mono uppercase tracking-wider text-ink-400 mb-1">Title</label>
                <input className="w-full h-8 px-2.5 border hl2 rounded" placeholder="Slow query in virtual table Остатки() without period filter"/>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <select className="h-8 px-2 border hl2 rounded text-[12px]"><option>Category: Performance</option></select>
                <select className="h-8 px-2 border hl2 rounded text-[12px]"><option>Config: УТ 11.5</option></select>
                <select className="h-8 px-2 border hl2 rounded text-[12px]"><option>Severity: Warning</option></select>
              </div>
              <div>
                <label className="block text-[10.5px] mono uppercase tracking-wider text-ink-400 mb-1">Description</label>
                <textarea rows="6" defaultValue="Описание проблемы, шаги воспроизведения, рекомендация…" className="w-full px-2.5 py-2 border hl2 rounded mono"/>
              </div>
              <div className="flex items-center gap-2">
                <label className="flex items-center gap-1.5 text-[11.5px]"><input type="checkbox" defaultChecked/>Anonymize names и идентификаторы</label>
                <label className="flex items-center gap-1.5 text-[11.5px] ml-3"><input type="checkbox" defaultChecked/>Attach mock telemetry snapshot</label>
                <button className="ml-auto h-7 px-3 rounded bg-teal-700 text-white text-[12px]">Submit</button>
              </div>
            </form>
          </Panel>
        </div>
      )}
    </div>
  );
}

function FilterGroup({ name, items }) {
  return (
    <div className="px-3 py-2 border-b hl">
      <div className="text-[10px] mono uppercase tracking-wider text-ink-400 mb-1.5">{name}</div>
      <ul className="space-y-1 text-[11.5px]">
        {items.map((it,i)=>(
          <li key={i}>
            <label className="flex items-center gap-1.5">
              <input type="checkbox" className="w-3 h-3"/>
              <span className="flex-1 text-ink-700">{it[0]}</span>
              <span className="mono tnum text-[10.5px] text-ink-400">{it[1]}</span>
            </label>
          </li>
        ))}
      </ul>
    </div>
  );
}

window.KnowledgeScreen = KnowledgeScreen;
