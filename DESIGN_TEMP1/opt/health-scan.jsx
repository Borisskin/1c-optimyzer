/* SCREEN 10: Configuration Health Scan */
function HealthScanScreen() {
  const [expanded, setExpanded] = React.useState('perf');

  const categories = [
    { id:'perf', name:'Performance-Critical Issues', count:47, tone:'err', items:[
      { name:'Queries without indexes',             count:12, sev:'err',  desc:'Запросы без поддерживающих индексов SQL · scan по большим таблицам' },
      { name:'Tabular sections without limits',     count:8,  sev:'warn', desc:'ТЧ документов без ограничения количества строк · OOM-риск' },
      { name:'Heavy ОбработкаПроведения',           count:15, sev:'warn', desc:'Процедуры проведения дольше 5с avg, требуют рефакторинга' },
      { name:'Inefficient virtual tables',          count:12, sev:'err',  desc:'.Остатки() / .Обороты() без фильтра по периоду — full scan' },
    ]},
    { id:'lock', name:'Locking Issues', count:23, tone:'err', items:[
      { name:'Unmanaged locks in managed mode',     count:5, sev:'err',  desc:'Явные блокировки в режиме «управляемые блокировки»' },
      { name:'Long transactions in BSL',            count:8, sev:'warn', desc:'Транзакции > 5с — повышают вероятность deadlock' },
      { name:'Lock escalations',                    count:6, sev:'warn', desc:'Эскалация блокировок при пересчёте итогов' },
      { name:'Cross-document lock patterns',        count:4, sev:'warn', desc:'Документы с пересечением модифицируемых регистров' },
    ]},
    { id:'arch', name:'Architectural Issues', count:14, tone:'warn', items:[
      { name:'Cyclic module dependencies',          count:3,  sev:'warn', desc:'Циклы в графе зависимостей общих модулей' },
      { name:'Privileged mode misuse',              count:4,  sev:'warn', desc:'Использование привилегированного режима без необходимости' },
      { name:'Server calls in loops',               count:7,  sev:'warn', desc:'Серверные вызовы внутри циклов клиента' },
    ]},
    { id:'code', name:'Code Quality Issues', count:89, tone:'info', items:[
      { name:'Magic strings in queries',            count:34, sev:'info', desc:'Жёстко зашитые строки в текстах запросов' },
      { name:'Duplicated queries',                  count:18, sev:'warn', desc:'Похожие запросы дублируются в разных модулях' },
      { name:'Deprecated platform methods',         count:37, sev:'info', desc:'Использование устаревших методов платформы' },
    ]},
    { id:'sec', name:'Security & Compliance', count:11, tone:'warn', items:[
      { name:'Missing access rights checks',        count:4,  sev:'err',  desc:'Серверные вызовы без проверки прав' },
      { name:'SQL injection risk',                  count:1,  sev:'err',  desc:'Конкатенация в текст запроса (пользовательский ввод)' },
      { name:'Sensitive data in logs',              count:6,  sev:'warn', desc:'Запись паролей/токенов в журнал регистрации' },
    ]},
  ];

  return (
    <div>
      <PageHeader breadcrumbs={['Configuration','Health Scan']} title="Configuration Health Scan"
        sub="статический + динамический анализ конфигурации · 27,432 объектов проверено"
        kpis={<>
          <KPI label="OVERALL HEALTH" value="C+" sub="184 issues · 17 critical" tone="warn"/>
          <KPI label="ESTIMATED LIFT" value="+38%" sub="if all critical resolved" tone="teal"/>
          <KPI label="CRITICAL" value="17" sub="action this week" tone="err"/>
          <KPI label="LAST SCAN" value="2 d ago" sub="next auto-scan tonight"/>
        </>}
        right={<>
          <button className="h-7 px-2 text-[11px] border hl2 rounded text-ink-600 hover:bg-ink-50 flex items-center gap-1"><I.Download size={11}/>Export report</button>
          <button className="h-7 px-2 text-[11px] rounded bg-teal-700 text-white flex items-center gap-1"><I.Play size={11}/>Run new scan</button>
        </>}/>

      <div className="px-3 py-2 bg-white border-b hl flex items-center gap-3 text-[11px]">
        <span className="mono text-ink-500">Scope:</span>
        <SegGroup><SegBtn active>УТ 11.5.18.235</SegBtn><SegBtn>+ Расширения (4)</SegBtn><SegBtn>+ Внешние обработки</SegBtn></SegGroup>
        <span className="mono text-ink-500 ml-2">Profile:</span>
        <SegGroup><SegBtn active>Full</SegBtn><SegBtn>Quick</SegBtn><SegBtn>Security only</SegBtn></SegGroup>
      </div>

      <div className="grid grid-cols-12 gap-3 p-3">
        {/* Categories tree */}
        <div className="col-span-7 space-y-3">
          {categories.map(c=>{
            const open = expanded === c.id;
            return (
              <div key={c.id} className="bg-white border hl2 rounded-md shadow-panel">
                <button onClick={()=>setExpanded(open?null:c.id)} className="w-full h-12 px-3 flex items-center gap-2 border-b hl">
                  {open ? <I.ChevronDown size={13} className="text-ink-400"/> : <I.ChevronRight size={13} className="text-ink-400"/>}
                  <Sev level={c.tone} size={9}/>
                  <span className="text-[13.5px] font-semibold">{c.name}</span>
                  <span className="ml-auto mono tnum text-[16px] font-semibold tabular-nums">{c.count}</span>
                </button>
                {open && (
                  <ul className="divide-y divide-ink-100">
                    {c.items.map((it,i)=>(
                      <li key={i} className="px-3 py-2 hover:bg-ink-25 cursor-pointer flex items-center gap-2">
                        <Sev level={it.sev} size={8}/>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5">
                            <span className="text-[12.5px] font-medium">{it.name}</span>
                            <Badge tone={it.sev}>{it.sev==='err'?'Critical':it.sev==='warn'?'Warning':'Info'}</Badge>
                          </div>
                          <div className="text-[11px] text-ink-500">{it.desc}</div>
                        </div>
                        <span className="mono tnum text-[14px] font-semibold w-10 text-right">{it.count}</span>
                        <I.ChevronRight size={12} className="text-ink-300"/>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </div>

        {/* Drill in: example occurrence */}
        <div className="col-span-5 space-y-3">
          <Panel title="Inefficient virtual tables · 12 occurrences" sub="ranked by impact" pad={false}>
            <ul className="divide-y divide-ink-100">
              {[
                { mod:'РасчётыСКонтрагентамиСервер', proc:'СформироватьТаблицуРасчётов', line:247, why:'Остатки() без &Период', impact:'High' },
                { mod:'ОтчётыСервер',               proc:'СформироватьВыручкуПоКонтрагентам', line:182, why:'Обороты() без фильтра', impact:'High' },
                { mod:'СкладСервер',                proc:'ПолучитьОстаткиТоваровНаСкладах', line:88,  why:'Остатки() в цикле', impact:'High' },
                { mod:'ЗакрытиеМесяца',             proc:'РассчитатьСебестоимость',     line:418, why:'Остатки() с фильтром не на индексе', impact:'Med' },
                { mod:'НоменклатураСервер',         proc:'ПолучитьАктуальныеЦены',      line:62,  why:'СрезПоследних() без &Дата', impact:'Med' },
              ].map((it,i)=>(
                <li key={i} className="px-3 py-2 hover:bg-ink-25 cursor-pointer">
                  <div className="flex items-center gap-2">
                    <span className="mono text-[11.5px]">{it.mod}<span className="text-ink-400">.</span>{it.proc}<span className="text-ink-400">()</span></span>
                    <Badge tone={it.impact==='High'?'err':'warn'} className="ml-auto">{it.impact}</Badge>
                  </div>
                  <div className="flex items-center gap-2 text-[11px] text-ink-500">
                    <span className="mono">line {it.line}</span>
                    <span>·</span>
                    <span>{it.why}</span>
                  </div>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title="Example occurrence" sub="РасчётыСКонтрагентамиСервер.СформироватьТаблицуРасчётов · line 247">
            <BSLBlock>{`Запрос.Текст =
   "ВЫБРАТЬ Контрагент, СУММА(Сумма) КАК Сумма
    ИЗ РегистрНакопления.РасчётыСКонтрагентами.Остатки()
    ГДЕ Контрагент В (&Контрагенты)";  // ←── line 247 · нет &Период`}</BSLBlock>
            <div className="mt-2 text-[11.5px] flex items-center gap-1.5 text-teal-700">
              <I.Sparkles size={12}/>Suggested fix: добавить параметр <span className="mono">&Период</span> в виртуальную таблицу
            </div>
            <div className="mt-2 flex gap-1.5">
              <button className="text-[11px] h-7 px-2 rounded border hl2">Show diff</button>
              <button className="text-[11px] h-7 px-2 rounded bg-teal-700 text-white">Generate fix as CFE</button>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
window.HealthScanScreen = HealthScanScreen;
