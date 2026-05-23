/* SCREEN 11: Configuration Comparison & Regression */
function ComparisonScreen() {
  const [selFile, setSelFile] = React.useState(0);

  const changedFiles = [
    { name:'СебестоимостьРасчётСервер.ОбщийМодуль', changes:'+24 −8', tone:'err',  ai:'high regression risk' },
    { name:'РасчётыСКонтрагентамиСервер.ОбщийМодуль', changes:'+12 −4', tone:'warn', ai:'minor refactor' },
    { name:'ОбменДаннымиСервер.ОбщийМодуль',          changes:'+18 −2', tone:'warn', ai:'new export format' },
    { name:'Документ.РеализацияТоваровУслуг.Модуль',  changes:'+4 −12', tone:'ok',   ai:'code simplification' },
    { name:'Справочник.Контрагенты.Модуль',           changes:'+2 −0',  tone:'mute', ai:'doc comments only' },
    { name:'РегистрНакопления.РасчётыСКонтрагентами.Модуль', changes:'+6 −1', tone:'mute', ai:'new property handlers' },
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-48px-28px)]">
      <PageHeader breadcrumbs={['Configuration','Compare']} title="Configuration Comparison & Regression"
        sub="статический diff конфигурации × runtime производительность"/>

      {/* Selectors */}
      <div className="px-3 py-2 bg-white border-b hl flex items-center gap-3 text-[11.5px]">
        <div className="flex items-center gap-2 border hl2 rounded px-2 h-8">
          <span className="text-ink-500 mono text-[10.5px]">BEFORE</span>
          <span className="font-semibold mono">УТ 11.5.18.230</span>
          <span className="text-ink-400 mono">prod · 10.04 – 17.04</span>
          <I.ChevronDown size={12} className="text-ink-400"/>
        </div>
        <I.ArrowRight size={14} className="text-ink-400"/>
        <div className="flex items-center gap-2 border hl2 rounded px-2 h-8 bg-teal-50/40">
          <span className="text-ink-500 mono text-[10.5px]">AFTER</span>
          <span className="font-semibold mono">УТ 11.5.18.235</span>
          <span className="text-ink-400 mono">prod · 17.04 – 24.04</span>
          <I.ChevronDown size={12} className="text-ink-400"/>
        </div>
        <button className="h-8 px-3 rounded bg-teal-700 text-white text-[12px] ml-2">Compare</button>
        <div className="ml-auto flex items-center gap-2 mono text-[11px] text-ink-500">
          <span>6 modules changed · 12 procedures · 38 lines</span>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-2 overflow-hidden">
        {/* Left: code diff */}
        <section className="flex flex-col border-r hl bg-white overflow-hidden">
          <div className="px-3 h-9 border-b hl flex items-center gap-2">
            <span className="text-[11px] mono text-ink-400 uppercase tracking-wider">Static configuration diff</span>
          </div>
          <div className="flex-1 grid grid-cols-[240px_1fr] overflow-hidden">
            <ul className="border-r hl bg-ink-25/40 overflow-y-auto py-1">
              {changedFiles.map((f,i)=>(
                <li key={i}>
                  <button onClick={()=>setSelFile(i)}
                    className={`w-full text-left px-2.5 py-1.5 hover:bg-white flex items-center gap-2 ${i===selFile?'bg-white border-l-2 border-teal-700':''}`}>
                    <Sev level={f.tone} size={6}/>
                    <span className="text-[11.5px] mono truncate flex-1">{f.name}</span>
                    <span className="mono text-[10.5px] text-ink-500 tnum">{f.changes}</span>
                  </button>
                  {i===selFile && <div className="px-3 pb-2 text-[10.5px] mono text-ink-400">AI: {f.ai}</div>}
                </li>
              ))}
            </ul>

            <div className="overflow-auto">
              <CodeDiff/>
            </div>
          </div>
        </section>

        {/* Right: runtime diff */}
        <section className="flex flex-col bg-white overflow-y-auto">
          <div className="px-3 h-9 border-b hl flex items-center gap-2">
            <span className="text-[11px] mono text-ink-400 uppercase tracking-wider">Performance runtime diff</span>
          </div>
          <RuntimeDiff/>
        </section>
      </div>

      {/* AI causal analysis */}
      <div className="border-t hl2 bg-teal-50/30 p-3 flex items-start gap-3">
        <div className="w-7 h-7 rounded-full bg-teal-700 text-white grid place-items-center shrink-0"><I.Sparkles size={14}/></div>
        <div className="flex-1">
          <div className="text-[11px] mono uppercase tracking-wider text-teal-800 font-semibold mb-0.5">AI causal analysis · confidence 91%</div>
          <div className="text-[12.5px] leading-relaxed text-ink-800 max-w-[1200px]">
            Регресс производительности операции <b>«Закрытие месяца»</b> (+46%, 280s → 410s) коррелирует с изменением процедуры <span className="mono">РассчитатьСебестоимость()</span> в общем модуле <span className="mono">СебестоимостьРасчётСервер</span> — добавлено новое чтение справочника <span className="mono">НастройкиПартионногоУчёта</span> в цикле по строкам ТЧ. На типичной операции это создаёт <b>1000+ дополнительных SQL queries</b> за одно проведение, что соответствует наблюдаемому спайку SQL CPU.
          </div>
          <div className="mt-2 flex gap-1.5">
            <button className="text-[11px] h-7 px-2 rounded bg-teal-700 text-white">Investigate →</button>
            <button className="text-[11px] h-7 px-2 rounded border hl2 bg-white text-teal-700">Show fix suggestion</button>
            <button className="text-[11px] h-7 px-2 rounded border hl2 bg-white text-ink-600">Open in Workbench</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function CodeDiff() {
  const lines = [
    { n:418, type:' ', t:'Процедура РассчитатьСебестоимость(Документ, Регистры) Экспорт' },
    { n:419, type:' ', t:'' },
    { n:420, type:' ', t:'    Для Каждого Строка Из Документ.Товары Цикл' },
    { n:421, type:'-', t:'        Партия = ПолучитьПартию(Строка.Номенклатура);' },
    { n:421, type:'+', t:'        Партия = ПолучитьПартию(Строка.Номенклатура);' },
    { n:422, type:'+', t:'        // ← регресс: новое чтение справочника в цикле' },
    { n:423, type:'+', t:'        Настройки = ПолучитьНастройкиПартионногоУчёта(' },
    { n:424, type:'+', t:'            Строка.Номенклатура, Документ.Организация);' },
    { n:425, type:' ', t:'' },
    { n:426, type:' ', t:'        Если Настройки.УчётСебестоимости = "FIFO" Тогда' },
    { n:427, type:' ', t:'            Себестоимость = Партия.СебестоимостьFIFO;' },
    { n:428, type:' ', t:'        Иначе' },
    { n:429, type:'+', t:'            Себестоимость = Партия.СебестоимостьСредняя' },
    { n:430, type:'+', t:'                * Настройки.КоэффициентКорректировки;' },
    { n:431, type:'-', t:'            Себестоимость = Партия.СебестоимостьСредняя;' },
    { n:432, type:' ', t:'        КонецЕсли;' },
    { n:433, type:' ', t:'        ДобавитьДвижение(Регистры, Строка, Себестоимость);' },
    { n:434, type:' ', t:'    КонецЦикла;' },
    { n:435, type:' ', t:'' },
    { n:436, type:' ', t:'КонецПроцедуры' },
  ];
  return (
    <table className="w-full text-[12px] mono leading-[1.55]">
      <tbody>
        {lines.map((l,i)=>{
          const bg = l.type==='+'? 'rgba(22,163,74,0.10)' : l.type==='-' ? 'rgba(220,38,38,0.10)' : 'transparent';
          return (
            <tr key={i} style={{background:bg}}>
              <td className="w-10 text-right text-ink-400 select-none border-r hl pr-2 tnum">{l.n}</td>
              <td className={`w-5 text-center ${l.type==='+'?'text-ok':l.type==='-'?'text-err':''}`}>{l.type==='+'?'+':l.type==='-'?'−':' '}</td>
              <td className="px-2 whitespace-pre">{l.t}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function RuntimeDiff() {
  const operations = [
    { name:'Закрытие месяца',                    before:280, after:410, unit:'s',  delta:46,  apdex:[0.71,0.42], tone:'err' },
    { name:'Проведение Реализация',              before:4.2, after:1.8, unit:'s',  delta:-57, apdex:[0.78,0.92], tone:'ok'  },
    { name:'Поступление товаров',                before:1.8, after:2.1, unit:'s',  delta:17,  apdex:[0.85,0.81], tone:'warn' },
    { name:'Отчёт «Продажи»',                    before:2.1, after:2.1, unit:'s',  delta:0,   apdex:[0.78,0.78], tone:'mute' },
    { name:'Регламент ОбменДанными_РЦ',          before:14,  after:18,  unit:'s',  delta:29,  apdex:[0.88,0.84], tone:'warn' },
    { name:'Открытие списка Контрагенты',        before:0.4, after:0.3, unit:'s',  delta:-25, apdex:[0.94,0.95], tone:'ok'  },
    { name:'Расчёт зарплаты',                    before:12,  after:13,  unit:'s',  delta:8,   apdex:[0.73,0.71], tone:'warn' },
    { name:'НачислениеАмортизации',              before:24,  after:24,  unit:'s',  delta:0,   apdex:[0.68,0.68], tone:'mute' },
    { name:'ПересчётИтогов регистров',           before:42,  after:48,  unit:'s',  delta:14,  apdex:[0.58,0.55], tone:'warn' },
  ];
  return (
    <div className="p-3 space-y-3">
      {/* High-level metrics */}
      <div className="grid grid-cols-4 gap-2">
        <RuntimeDelta label="Apdex (overall)" before="0.89" after="0.87" delta="−2.2%" tone="warn"/>
        <RuntimeDelta label="p95 latency"     before="2.4 s" after="2.8 s" delta="+16%" tone="warn"/>
        <RuntimeDelta label="Errors / hour"   before="3"    after="5"     delta="+67%" tone="warn"/>
        <RuntimeDelta label="Deadlocks / day" before="34"   after="67"    delta="+97%" tone="err"/>
      </div>

      <Panel pad={false} title="Operations · before vs after" sub="ranked by absolute delta" dense>
        <table className="w-full text-[12px]">
          <thead className="bg-ink-25">
            <tr>
              <Th>Operation</Th>
              <Th align="right" w="60px">Before</Th>
              <Th align="right" w="60px">After</Th>
              <Th align="right" w="60px">Δ</Th>
              <Th align="center" w="80px">Apdex</Th>
              <Th w="50px"></Th>
            </tr>
          </thead>
          <tbody>
            {operations.map((o,i)=>(
              <tr key={i} className="row border-t hl">
                <Td><span className="mono text-[11.5px]">{o.name}</span></Td>
                <Td mono align="right" className="tnum text-ink-500">{o.before}{o.unit}</Td>
                <Td mono align="right" className={`tnum font-semibold ${o.tone==='err'?'text-err':o.tone==='warn'?'text-warn':o.tone==='ok'?'text-ok':''}`}>{o.after}{o.unit}</Td>
                <Td mono align="right" className={`tnum ${o.delta>0?'text-err':o.delta<0?'text-ok':'text-ink-400'}`}>{o.delta>0?'+':''}{o.delta}%</Td>
                <Td align="center" className="mono text-[11px] tnum">
                  <span className="text-ink-400">{o.apdex[0]}</span>
                  <span className="mx-1 text-ink-300">→</span>
                  <span className={o.tone==='err'?'text-err':o.tone==='warn'?'text-warn':o.tone==='ok'?'text-ok':''}>{o.apdex[1]}</span>
                </Td>
                <Td><I.ChevronRight size={12} className="text-ink-300"/></Td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
    </div>
  );
}

function RuntimeDelta({ label, before, after, delta, tone }) {
  return (
    <div className="border hl2 rounded p-2.5">
      <div className="text-[10px] mono uppercase tracking-wider text-ink-400">{label}</div>
      <div className="flex items-end gap-1 mt-0.5">
        <span className="mono tnum text-[11px] text-ink-400">{before}</span>
        <I.ArrowRight size={10} className="text-ink-400 mb-0.5"/>
        <span className={`mono tnum text-[16px] font-semibold ${tone==='err'?'text-err':tone==='warn'?'text-warn':tone==='ok'?'text-ok':''}`}>{after}</span>
        <span className={`mono tnum text-[11px] ml-auto ${tone==='ok'?'text-ok':tone==='err'?'text-err':'text-warn'}`}>{delta}</span>
      </div>
    </div>
  );
}

window.ComparisonScreen = ComparisonScreen;
