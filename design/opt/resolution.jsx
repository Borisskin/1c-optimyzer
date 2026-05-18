/* SCREEN 12: Resolution Workflow */
function ResolutionScreen() {
  const cols = [
    { id:'identified',   name:'Identified',   count:8 },
    { id:'investigating',name:'Investigating',count:5 },
    { id:'designed',     name:'Fix Designed', count:3 },
    { id:'testing',      name:'Testing',      count:2 },
    { id:'deployed',     name:'Deployed',     count:4 },
    { id:'verified',     name:'Verified',     count:12 },
  ];

  const cards = {
    identified: [
      { title:'Slow query in СрезПоследних(ЦеныНоменклатуры)', sev:'warn', age:'2h', owner:'—', impact:'p95 2.8s', tag:'query' },
      { title:'Missing index _Reference234(_Fld234_ИНН)',      sev:'warn', age:'5h', owner:'—', impact:'+30% gain', tag:'index' },
      { title:'Long Apdex collection (transient)',             sev:'info', age:'1d', owner:'—', impact:'minor', tag:'system' },
      { title:'Lock escalation on _AccumRgT5891',              sev:'warn', age:'3d', owner:'—', impact:'12 inc/24h', tag:'lock' },
    ],
    investigating: [
      { title:'Deadlock #1247 — Реализация ↔ КорректировкаДолга', sev:'err', age:'3d', owner:'Иванов И.С.', impact:'Critical · 312/7d', tag:'deadlock', pinned:true },
      { title:'Memory leak in rphost #3',                         sev:'err', age:'1d', owner:'Петров А.В.', impact:'+45 MB/h', tag:'system' },
      { title:'Query СформироватьТаблицуРасчётов · 4.2s avg',     sev:'warn', age:'4h', owner:'Сидорова Е.А.', impact:'23% SQL CPU', tag:'query' },
    ],
    designed: [
      { title:'Index IX__AccumRgT5634_Period_Fld5640',         sev:'warn', age:'8h', owner:'Сидорова Е.А.', impact:'+70% to top query', tag:'index' },
      { title:'Sequence change in ОбработкаПроведения()',      sev:'err',  age:'12h',owner:'Иванов И.С.', impact:'fix #1247', tag:'deadlock' },
    ],
    testing: [
      { title:'CFE: virtual table period fix',                 sev:'warn', age:'1d', owner:'Морозов Д.С.', impact:'staging green', tag:'cfe' },
    ],
    deployed: [
      { title:'Drop unused IX_Document156_LegacyHash',         sev:'mute', age:'2d', owner:'Кузнецова О.Н.', impact:'+writes 8%', tag:'index' },
      { title:'Update statistics on _Document156',             sev:'mute', age:'2d', owner:'Кузнецова О.Н.', impact:'minor', tag:'stats' },
    ],
    verified: [
      { title:'Resolved: Slow query in НоменклатураСервер',    sev:'ok',   age:'3d', owner:'Сидорова Е.А.', impact:'−68%', tag:'query' },
      { title:'Resolved: Missing index _Reference234',         sev:'ok',   age:'2w', owner:'Иванов И.С.', impact:'120ms→8ms', tag:'index' },
    ],
  };

  return (
    <div className="flex flex-col h-[calc(100vh-48px-28px)]">
      <PageHeader breadcrumbs={['Manage','Resolution']} title="Resolution Workflow"
        sub="34 active items · 12 verified this month"
        kpis={<>
          <KPI label="MTTR" value="2.4 d" sub="median across critical" tone="ok"/>
          <KPI label="ACTIVE CRITICAL" value="6" sub="2 over SLA budget" tone="warn"/>
          <KPI label="VERIFIED THIS MONTH" value="12" sub="+38% impact recovered"/>
          <KPI label="AUTOMATED FIXES" value="34" sub="of 67 applied (CFE)"/>
        </>}
        right={<>
          <button className="h-7 px-2 text-[11px] border hl2 rounded text-ink-600 hover:bg-ink-50 flex items-center gap-1"><I.Filter size={11}/>Filter</button>
          <button className="h-7 px-2 text-[11px] rounded bg-teal-700 text-white flex items-center gap-1"><I.Plus size={11}/>New resolution</button>
        </>}/>

      <Tabs value="active" onChange={()=>{}} tabs={[
        { id:'active', label:'Active Resolutions', icon:I.Workflow, count:34 },
        { id:'archive',label:'Archive', icon:I.Inbox, count:182 },
        { id:'cfe',    label:'CFE Library', icon:I.Code, count:18 },
      ]}/>

      <div className="flex-1 overflow-x-auto bg-ink-25">
        <div className="grid p-3 gap-3" style={{gridTemplateColumns:'repeat(6, 264px)', minWidth: 'fit-content'}}>
          {cols.map(c=>(
            <div key={c.id} className="bg-white border hl2 rounded-md shadow-panel flex flex-col">
              <header className="px-3 h-9 border-b hl flex items-center gap-2">
                <span className="text-[12px] font-semibold">{c.name}</span>
                <span className="text-[10.5px] mono tnum text-ink-500">{c.count}</span>
                <button className="ml-auto h-6 w-6 grid place-items-center hover:bg-ink-50 rounded"><I.Plus size={12} className="text-ink-400"/></button>
              </header>
              <div className="p-2 space-y-2 max-h-[calc(100vh-48px-28px-180px)] overflow-y-auto">
                {(cards[c.id]||[]).map((cd,i)=>(
                  <article key={i} className={`border hl2 rounded p-2 hover:border-teal-700/30 ${cd.pinned?'ring-1 ring-teal-700/30':''}`}>
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <Sev level={cd.sev} size={7}/>
                      <Badge tone="mute" mono>{cd.tag}</Badge>
                      <span className="ml-auto mono text-[10px] text-ink-400">{cd.age}</span>
                    </div>
                    <div className="text-[12px] font-medium leading-snug">{cd.title}</div>
                    <div className="mt-2 flex items-center justify-between text-[10.5px] mono">
                      {cd.owner==='—' ? <span className="text-ink-400">unassigned</span> : <span className="flex items-center gap-1"><span className="w-3.5 h-3.5 rounded-full bg-teal-700 text-white text-[8px] grid place-items-center">{cd.owner.split(' ')[0][0]}</span>{cd.owner.split(' ')[0]}</span>}
                      <span className={cd.sev==='err'?'text-err':cd.sev==='warn'?'text-warn':'text-ink-500'}>{cd.impact}</span>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Detail strip — pinned card */}
      <div className="border-t hl bg-white">
        <div className="px-3 py-2.5 flex items-center gap-3 border-b hl">
          <Badge tone="err">Critical</Badge>
          <span className="text-[13px] font-semibold">Deadlock #1247 — Реализация ↔ КорректировкаДолга</span>
          <Badge tone="mute">opened 3d · owner Иванов И.С. · 12 events</Badge>
          <div className="ml-auto flex gap-1.5">
            <button className="text-[11px] h-7 px-2 rounded border hl2">Apply to Test base</button>
            <button className="text-[11px] h-7 px-2 rounded border hl2">Postpone</button>
            <button className="text-[11px] h-7 px-2 rounded bg-teal-700 text-white">Apply as CFE</button>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-0 max-h-[280px]">
          {/* Timeline */}
          <div className="border-r hl p-3">
            <div className="text-[10.5px] mono uppercase tracking-wider text-ink-400 mb-1.5">Timeline</div>
            <ol className="space-y-2 text-[11.5px]">
              {[
                ['3d ago',  'Detected pattern via AI Insights', 'info'],
                ['3d ago',  'Иванов И.С. начал investigation',  'mute'],
                ['2d ago',  'Lock graph + root cause confirmed', 'ok'],
                ['1d ago',  'AI proposed 3 fix options', 'info'],
                ['12h ago', 'Иванов выбрал «Code fix» вариант', 'mute'],
                ['8h ago',  'CFE сгенерирован', 'ok'],
                ['now',     'Ожидает деплоя на test', 'warn'],
              ].map((e,i)=>(
                <li key={i} className="flex gap-2">
                  <Sev level={e[2]} size={7}/>
                  <span className="mono text-[10.5px] text-ink-400 w-12">{e[0]}</span>
                  <span className="text-ink-700">{e[1]}</span>
                </li>
              ))}
            </ol>
          </div>

          {/* Diff */}
          <div className="border-r hl p-3 overflow-y-auto">
            <div className="text-[10.5px] mono uppercase tracking-wider text-ink-400 mb-1.5">Selected fix · code diff</div>
            <pre className="mono text-[11.5px] codebox p-2 leading-[1.55]">
{`Документ.КорректировкаДолга.ОбработкаПроведения()
  120   …
  121   // Старый порядок:
- 122   ВыполнитьДвиженияВзаиморасчёты(Документ);
- 123   ВыполнитьДвиженияРасчётыСКонтрагентами(Документ);
  124   …
  125   // Новый порядок (унифицировано):
+ 126   ВыполнитьДвиженияРасчётыСКонтрагентами(Документ);
+ 127   ВыполнитьДвиженияВзаиморасчёты(Документ);
  128   …`}
            </pre>
          </div>

          {/* CFE scaffold */}
          <div className="p-3 overflow-y-auto">
            <div className="text-[10.5px] mono uppercase tracking-wider text-ink-400 mb-1.5">CFE scaffold · auto-generated</div>
            <BSLBlock className="!text-[11px]">{`// Расширение конфигурации: optimyzer__1247_deadlock_fix
// Цель: унифицировать порядок изменения регистров
Процедура ОбработкаПроведения_ИЗМЕНЕНО(Отказ, РежимПроведения)
  // call inherited but в нужном порядке
  ВыполнитьДвиженияРасчётыСКонтрагентами(ЭтотОбъект);
  ВыполнитьДвиженияВзаиморасчёты(ЭтотОбъект);
КонецПроцедуры`}</BSLBlock>
            <div className="mt-2 flex items-center gap-1.5 text-[10.5px] mono text-ink-500"><I.Sparkles size={10} className="text-teal-700"/>Изменения изолированы в CFE — основная конфигурация не модифицируется</div>
          </div>
        </div>
      </div>
    </div>
  );
}
window.ResolutionScreen = ResolutionScreen;
