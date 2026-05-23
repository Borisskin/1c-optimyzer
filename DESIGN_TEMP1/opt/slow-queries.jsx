/* SCREEN 4: Slow Queries Analyzer */
function SlowQueriesScreen() {
  const [sel, setSel] = React.useState(0);
  const queries = [
    { rank:1, q:`ВЫБРАТЬ ... ИЗ РегистрНакопления.РасчётыСКонтрагентами.Остатки() ГДЕ Контрагент В (&Контрагенты)`, avg:'4.2s', total:'380s', share:23, count:'47', p95:'8.1s', reads:'234K', last:'2m ago', module:'РасчётыСКонтрагентамиСервер', tone:'err' },
    { rank:2, q:`ВЫБРАТЬ ... ИЗ Документ.РеализацияТоваровУслуг ГДЕ Дата >= &Начало И Дата <= &Окончание`, avg:'2.1s', total:'184s', share:11, count:'89', p95:'4.5s', reads:'89K', last:'30s ago', module:'ОтчётыСервер', tone:'warn' },
    { rank:3, q:`ВЫБРАТЬ ... ИЗ Справочник.Номенклатура ГДЕ Группа В ИЕРАРХИИ (&Группы)`, avg:'1.8s', total:'145s', share:9, count:'78', p95:'3.9s', reads:'67K', last:'1m ago', module:'НоменклатураСервер', tone:'warn' },
    { rank:4, q:`ВЫБРАТЬ ... ИЗ РегистрНакопления.ТоварыНаСкладах.Остатки(&Дата) ГДЕ Склад = &Склад`, avg:'1.5s', total:'120s', share:7, count:'80', p95:'3.2s', reads:'54K', last:'15s ago', module:'СкладСервер', tone:'warn' },
    { rank:5, q:`ВЫБРАТЬ ... ИЗ РегистрСведений.ЦеныНоменклатуры.СрезПоследних(&Дата) ГДЕ Номенклатура = &Номенклатура`, avg:'1.2s', total:'98s', share:6, count:'82', p95:'2.8s', reads:'42K', last:'8s ago', module:'ЦенообразованиеСервер', tone:'warn' },
    { rank:6, q:`ВЫБРАТЬ ... ИЗ Документ.КорректировкаДолга.КонтрагентыИзТЧ ГДЕ Ссылка = &Документ`, avg:'0.94s', total:'76s', share:5, count:'81', p95:'2.1s', reads:'18K', last:'45s ago', module:'РасчётыСКонтрагентамиСервер', tone:'mute' },
    { rank:7, q:`SELECT TOP 100 ... FROM _AccumRg7821 WHERE _Period >= @P1 AND _Fld7825RRef IN (...)`, avg:'0.81s', total:'65s', share:4, count:'80', p95:'1.8s', reads:'15K', last:'1m ago', module:'OptimyzerQL ad-hoc', tone:'mute' },
    { rank:8, q:`ВЫБРАТЬ ... ИЗ РегистрНакопления.Взаиморасчёты.Обороты(&Начало, &Конец)`, avg:'0.74s', total:'59s', share:4, count:'80', p95:'1.6s', reads:'14K', last:'45s ago', module:'ОтчётыСервер', tone:'mute' },
    { rank:9, q:`ВЫБРАТЬ ... ИЗ Справочник.Контрагенты ГДЕ Наименование ПОДОБНО &Шаблон`, avg:'0.68s', total:'54s', share:3, count:'79', p95:'1.5s', reads:'12K', last:'3m ago', module:'КонтрагентыСервер', tone:'mute' },
    { rank:10,q:`ВЫБРАТЬ ... ИЗ РегистрСведений.КурсыВалют.СрезПоследних(&Дата)`, avg:'0.41s', total:'33s', share:2, count:'80', p95:'0.9s', reads:'8K', last:'12s ago', module:'ВалютыСервер', tone:'mute' },
    { rank:11,q:`ВЫБРАТЬ ... ИЗ Справочник.Номенклатура.ЕдиницыИзмерения ГДЕ Владелец = &Ном`, avg:'0.32s', total:'26s', share:2, count:'81', p95:'0.7s', reads:'4.2K', last:'8s ago', module:'НоменклатураСервер', tone:'mute' },
    { rank:12,q:`SELECT ... FROM _Document156 INNER JOIN _Reference234 ON ...`, avg:'0.28s', total:'22s', share:1, count:'78', p95:'0.6s', reads:'3.8K', last:'2m ago', module:'OptimyzerQL ad-hoc', tone:'mute' },
    { rank:13,q:`ВЫБРАТЬ ... ИЗ Документ.ПоступлениеТоваровУслуг.Товары`, avg:'0.21s', total:'17s', share:1, count:'81', p95:'0.5s', reads:'2.8K', last:'4m ago', module:'ОтчётыСервер', tone:'mute' },
  ];
  const q = queries[sel];

  return (
    <div className="flex flex-col h-[calc(100vh-48px-28px)]">
      <PageHeader breadcrumbs={['Analyze','Slow Queries']} title="Slow Queries Analyzer"
        sub={`${queries.length} normalized · 1,247 raw executions captured`}
        kpis={<>
          <KPI label="TOTAL TIME / DAY" value="1,653 s" sub="27.5 min of SQL"/>
          <KPI label="SHARE OF SQL CPU" value="68.4%" sub="top 13 queries" tone="warn"/>
          <KPI label="QUERIES > 1S" value="423" sub="last 1h"/>
        </>}
        right={<>
          <SegGroup><SegBtn>15m</SegBtn><SegBtn>1h</SegBtn><SegBtn active>24h</SegBtn><SegBtn>7d</SegBtn></SegGroup>
          <button className="ml-2 h-7 px-2 text-[11px] flex items-center gap-1 border hl2 rounded text-ink-600 hover:bg-ink-50"><I.Filter size={11}/>Filters</button>
          <button className="h-7 px-2 text-[11px] flex items-center gap-1 border hl2 rounded text-ink-600 hover:bg-ink-50"><I.Download size={11}/>Export</button>
        </>}/>

      {/* Filter bar */}
      <div className="px-3 py-2 bg-white border-b hl flex items-center gap-2 text-[11px]">
        <input placeholder="search: text · module · table" className="h-7 px-2 mono border hl2 rounded w-[300px]"/>
        <SegGroup><SegBtn active>All sources</SegBtn><SegBtn>1С запросы</SegBtn><SegBtn>SQL raw</SegBtn></SegGroup>
        <SegGroup><SegBtn>CPU bound</SegBtn><SegBtn>IO bound</SegBtn><SegBtn>Lock bound</SegBtn></SegGroup>
        <span className="mono text-ink-400 ml-2">module: <button className="underline">любой</button></span>
        <span className="mono text-ink-400 ml-2">база: <button className="underline">УТ 11.5 prod</button></span>
        <span className="ml-auto mono text-[10.5px] text-ink-400">sort by total time desc</span>
      </div>

      <div className="flex-1 grid grid-cols-[1fr_420px] overflow-hidden">
        {/* Table */}
        <div className="overflow-auto bg-white">
          <table className="w-full text-[12px]">
            <thead className="bg-ink-25 sticky top-0">
              <tr>
                <Th w="32px" align="right">#</Th>
                <Th>Normalized query</Th>
                <Th align="right" w="78px">Avg</Th>
                <Th align="right" w="92px">Total · share</Th>
                <Th align="right" w="60px">Count</Th>
                <Th align="right" w="60px">p95</Th>
                <Th align="right" w="64px">Reads</Th>
                <Th align="center" w="76px">Trend</Th>
                <Th w="170px">Module</Th>
                <Th align="right" w="70px">Last seen</Th>
              </tr>
            </thead>
            <tbody>
              {queries.map((qq,i)=>(
                <tr key={i} className="row border-t hl cursor-pointer" data-active={i===sel?'1':'0'} onClick={()=>setSel(i)}>
                  <Td align="right" mono className="text-ink-400">{qq.rank}</Td>
                  <Td><div className="mono text-[11.5px] truncate max-w-[480px]">{qq.q}</div></Td>
                  <Td align="right" mono className={`tnum font-semibold ${qq.tone==='err'?'text-err':qq.tone==='warn'?'text-warn':'text-ink-900'}`}>{qq.avg}</Td>
                  <Td align="right" mono className="tnum">
                    <div>{qq.total}</div>
                    <div className="text-[10px] text-ink-400">{qq.share}%</div>
                  </Td>
                  <Td align="right" mono className="tnum">{qq.count}</Td>
                  <Td align="right" mono className="tnum text-ink-600">{qq.p95}</Td>
                  <Td align="right" mono className="tnum text-ink-500">{qq.reads}</Td>
                  <Td align="center"><Spark data={Array.from({length:18},()=>0.4 + Math.random()*0.6)} w={64} h={16} strokeW={1.2}/></Td>
                  <Td><span className="mono text-[11px] text-ink-700">{qq.module}</span></Td>
                  <Td align="right" mono className="tnum text-ink-400">{qq.last}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Inspector */}
        <aside className="border-l hl bg-white overflow-y-auto">
          <SlowQueryInspector q={q}/>
        </aside>
      </div>
    </div>
  );
}

function SlowQueryInspector({ q }) {
  return (
    <div className="p-3">
      <div className="flex items-center gap-2">
        <Badge tone={q.tone==='err'?'err':q.tone==='warn'?'warn':'mute'}>rank #{q.rank}</Badge>
        <Badge tone="mute" mono>fingerprint f3a2c1</Badge>
      </div>
      <h3 className="text-[14px] font-semibold mt-1.5 leading-snug">{q.module}</h3>
      <div className="text-[11px] mono text-ink-500">procedure СформироватьТаблицуРасчётов() · line 247</div>

      <div className="mt-3 grid grid-cols-4 gap-1.5">
        <Stat2 label="avg" value={q.avg} tone="warn"/>
        <Stat2 label="p95" value={q.p95}/>
        <Stat2 label="total" value={q.total}/>
        <Stat2 label="reads" value={q.reads}/>
      </div>

      <div className="div-h my-3"></div>

      <div className="text-[10px] mono uppercase tracking-wider text-ink-400 mb-1">Query (parameterized)</div>
      <SQLBlock>{`ВЫБРАТЬ
    Расчёты.Контрагент,
    СУММА(Расчёты.СуммаОстаток) КАК Сумма
ИЗ
    РегистрНакопления.РасчётыСКонтрагентами.Остатки() КАК Расчёты
ГДЕ
    Расчёты.Контрагент В (&Контрагенты)
СГРУППИРОВАТЬ ПО Расчёты.Контрагент`}</SQLBlock>

      <div className="mt-2 text-[10px] mono uppercase tracking-wider text-ink-400 mb-1">Sample binding · sid 47 · 14:32:11</div>
      <pre className="codebox p-2 mono text-[11px] leading-tight">{`@Контрагенты = TVP[24]:
  001a3e..  Ромашка ООО
  003ff8..  СтройМаркет
  004f12..  Партнёр-Плюс
  + 21 more`}</pre>

      <div className="div-h my-3"></div>

      <div className="text-[10px] mono uppercase tracking-wider text-ink-400 mb-1">Execution time · distribution</div>
      <div className="codebox p-2">
        <Histogram/>
      </div>

      <div className="div-h my-3"></div>

      <div className="text-[10px] mono uppercase tracking-wider text-ink-400 mb-1">Related code</div>
      <BSLBlock className="!leading-[1.5]">{`// Module: РасчётыСКонтрагентамиСервер
Процедура СформироватьТаблицуРасчётов(Контрагенты, Период)
  Запрос = Новый Запрос(
    "ВЫБРАТЬ ... ИЗ РегистрНакопления.РасчётыСКонтрагентами.Остатки()
     ГДЕ Контрагент В (&Контрагенты)"); // ← line 247
  Запрос.УстановитьПараметр("Контрагенты", Контрагенты);
  Возврат Запрос.Выполнить().Выгрузить();
КонецПроцедуры`}</BSLBlock>

      <div className="div-h my-3"></div>

      <div className="flex items-center gap-1.5 mb-2">
        <I.Sparkles size={13} className="text-teal-700"/>
        <span className="text-[11.5px] font-semibold mono text-teal-800">AI Recommendations</span>
        <span className="ml-auto text-[10px] mono text-ink-400">ranked by expected gain</span>
      </div>
      <ol className="space-y-1.5">
        <RecItem n={1} gain="95%" tone="teal" title="Code fix · добавить &Период"
          body={<>Передавать <span className="mono">&Период</span> в виртуальную таблицу <span className="mono">.Остатки(&Период, …)</span>. SQL получит sargable predicate и сможет seek по индексу.</>}/>
        <RecItem n={2} gain="70%" tone="info" title="Add covering index"
          body={<><span className="mono">IX__AccumRgT5634_Period_Fld5640RRef</span> include (Fld5642). Размер ~145 MB.</>}/>
        <RecItem n={3} gain="10%" tone="mute" title="Update statistics"
          body={<>Статистика устарела (last updated 14 days ago).</>}/>
      </ol>

      <div className="div-h my-3"></div>

      <div className="grid grid-cols-2 gap-1.5">
        <button className="text-[11.5px] h-7 border hl2 rounded bg-teal-700 text-white hover:bg-teal-800 flex items-center justify-center gap-1.5 col-span-2"><I.Sparkles size={11}/>Generate Fix as CFE</button>
        <button className="text-[11.5px] h-7 border hl2 rounded hover:bg-ink-50 flex items-center justify-center gap-1.5"><I.Layers size={11}/>Open in Workbench</button>
        <button className="text-[11.5px] h-7 border hl2 rounded hover:bg-ink-50 flex items-center justify-center gap-1.5"><I.Bookmark size={11}/>Add to Watch</button>
      </div>
    </div>
  );
}

function Stat2({label, value, tone}) {
  return <div className="border hl2 rounded px-2 py-1.5">
    <div className="text-[9.5px] text-ink-400 uppercase tracking-wider mono">{label}</div>
    <div className={`tnum mono font-semibold text-[13px] ${tone==='warn'?'text-warn':tone==='err'?'text-err':'text-ink-900'}`}>{value}</div>
  </div>;
}

function RecItem({ n, gain, tone='mute', title, body }) {
  return (
    <li className="border hl2 rounded p-2">
      <div className="flex items-center gap-1.5">
        <span className="w-4 h-4 grid place-items-center mono text-[9.5px] rounded bg-ink-100 tnum">{n}</span>
        <span className="font-semibold text-[12px]">{title}</span>
        <Badge tone={tone} className="ml-auto">+{gain}</Badge>
      </div>
      <div className="text-[11px] text-ink-600 mt-1 leading-snug">{body}</div>
    </li>
  );
}

function Histogram() {
  // execution time distribution
  const buckets = [
    {l:'0-500ms', c:12},
    {l:'500ms-1s', c:18},
    {l:'1-2s', c:42},
    {l:'2-4s', c:68},
    {l:'4-6s', c:54},
    {l:'6-10s', c:31},
    {l:'10-15s', c:14},
    {l:'15s+', c:6},
  ];
  const max = Math.max(...buckets.map(b=>b.c));
  return (
    <div>
      <div className="flex items-end gap-1 h-[80px]">
        {buckets.map((b,i)=>(
          <div key={i} className="flex-1 flex flex-col items-center">
            <div className="w-full bg-teal-700/80 rounded-sm" style={{height: (b.c/max)*72 + 'px', minHeight:'2px'}}/>
          </div>
        ))}
      </div>
      <div className="flex justify-between text-[9.5px] mono text-ink-400 mt-1">
        {buckets.map((b,i)=>(<span key={i} style={{width:`${100/buckets.length}%`, textAlign:'center'}}>{b.l}</span>))}
      </div>
    </div>
  );
}

window.SlowQueriesScreen = SlowQueriesScreen;
