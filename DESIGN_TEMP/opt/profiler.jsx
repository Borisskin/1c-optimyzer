/* SCREEN 8: BSL Profiler */
function ProfilerScreen() {
  const tree = [
    { d:0, name:'Документ.РеализацияТоваровУслуг.ОбработкаПроведения()', total:3.4, self:0.2, calls:'12K', hot:0.9, sel:false },
    { d:1, name:'ВыполнитьДвиженияТовары()', total:2.1, self:0.3, calls:'12K', hot:0.8 },
    { d:2, name:'ПолучитьОстаткиТоваровНаСкладах()', total:1.8, self:0.1, calls:'12K', hot:0.95, sel:true },
    { d:3, name:'SQL: ВЫБРАТЬ … ИЗ ТоварыНаСкладах.Остатки()', total:1.7, self:1.7, calls:'12K', hot:1.0, leaf:'sql' },
    { d:2, name:'СформироватьДвижения()', total:0.3, self:0.3, calls:'12K', hot:0.3 },
    { d:1, name:'ВыполнитьДвиженияРасчёты()', total:1.1, self:0.1, calls:'12K', hot:0.55 },
    { d:2, name:'СформироватьТаблицуРасчётов()', total:1.0, self:0.05, calls:'12K', hot:0.6 },
    { d:3, name:'SQL: ВЫБРАТЬ … ИЗ РасчётыСКонтрагентами.Остатки()', total:0.95, self:0.95, calls:'12K', hot:0.85, leaf:'sql' },
    { d:1, name:'ПровестиВТабличныхРегистрах()', total:0.2, self:0.2, calls:'12K', hot:0.15 },
    { d:1, name:'ЗаписатьДокумент()', total:0.06, self:0.06, calls:'12K', hot:0.05 },
  ];

  const totalT = tree[0].total;

  const code = [
    [241, 'Процедура ВыполнитьДвиженияТовары(Документ, Регистры) Экспорт', null, null],
    [242, '', null, null],
    [243, '    Запрос = Новый Запрос;', '12K', '2 ms'],
    [244, '    Запрос.Текст = ', null, null],
    [245, '        "ВЫБРАТЬ', null, null],
    [246, '        |    Остатки.Номенклатура,', null, null],
    [247, '        |    Остатки.КоличествоОстаток', null, null],
    [248, '        |ИЗ', null, null],
    [249, '        |    РегистрНакопления.ТоварыНаСкладах.Остатки()', null, null, 'warn'],
    [250, '        |        КАК Остатки', null, null],
    [251, '        |ГДЕ', null, null],
    [252, '        |    Остатки.Склад = &Склад";', null, null],
    [253, '    Запрос.УстановитьПараметр("Склад", Документ.Склад);', '12K', '<1 ms'],
    [254, '    Результат = Запрос.Выполнить();', '12K', '1.8 s avg', 'hot'],
    [255, '    Выборка = Результат.Выбрать();', '12K', '<1 ms'],
    [256, '    Пока Выборка.Следующий() Цикл', '892K', '0.4 ms'],
    [257, '        Если Выборка.КоличествоОстаток < 0 Тогда', '892K', '<1 ms'],
    [258, '            ВыполнитьПартионнуюКоррекцию(Выборка);', '12K', '8 ms'],
    [259, '        КонецЕсли;', null, null],
    [260, '    КонецЦикла;', null, null],
    [261, '', null, null],
    [262, 'КонецПроцедуры', null, null],
  ];

  return (
    <div className="flex flex-col">
      <PageHeader breadcrumbs={['Analyze','BSL Profiler']} title="BSL Profiler"
        sub="hot path · ВыполнитьДвиженияТовары · 12,847 executions / 24h"
        kpis={<>
          <KPI label="TOTAL TIME / DAY" value="42,118 s" sub="11.7 hours of BSL"/>
          <KPI label="TOP HOT PATH" value="3.4 s" sub="avg per ОбработкаПроведения" tone="warn"/>
          <KPI label="HOT FUNCTIONS" value="17" sub="≥ 90% of total time"/>
          <KPI label="SQL TIME / BSL TIME" value="76%" sub="SQL-bound" tone="warn"/>
        </>}
        right={<>
          <SegGroup><SegBtn>cpu</SegBtn><SegBtn active>wall</SegBtn><SegBtn>allocs</SegBtn></SegGroup>
          <button className="ml-2 h-7 px-2 text-[11px] border hl2 rounded text-ink-600 hover:bg-ink-50">Profile a session →</button>
        </>}/>

      <div className="grid grid-cols-12 gap-3 p-3">
        {/* Hot path tree */}
        <Panel className="col-span-5" title="Call tree" sub="aggregated · self+children · sampling 1ms" pad={false}>
          <div className="px-2.5 py-1.5 border-b hl bg-ink-25 flex items-center text-[10.5px] mono uppercase tracking-wider text-ink-400">
            <span className="flex-1">Function</span>
            <span className="w-16 text-right">Total</span>
            <span className="w-16 text-right">Self</span>
            <span className="w-16 text-right">Calls</span>
          </div>
          <ul className="text-[11.5px] mono">
            {tree.map((n,i)=>{
              const pct = (n.total/totalT)*100;
              const heat = n.hot;
              const bg = heat>0.8?'rgba(220,38,38,0.06)':heat>0.5?'rgba(217,119,6,0.05)':heat>0.3?'rgba(22,163,74,0.04)':'transparent';
              return (
                <li key={i} className={`flex items-center gap-1 px-2.5 py-1 border-b hl ${n.sel?'bg-teal-50':''}`} style={{background: n.sel?undefined:bg}}>
                  <span style={{ width: n.d*14 }}/>
                  {!n.leaf && <I.ChevronDown size={11} className="text-ink-400"/>}
                  {n.leaf==='sql' && <Badge tone="info" className="mr-0.5">SQL</Badge>}
                  <span className="truncate flex-1">{n.name}</span>
                  <span className="w-16 text-right tnum">{n.total.toFixed(2)}s</span>
                  <span className="w-16 text-right tnum text-ink-500">{n.self.toFixed(2)}s</span>
                  <span className="w-16 text-right tnum text-ink-500">{n.calls}</span>
                  {/* heat bar */}
                  <span className="absolute -right-0 top-0 bottom-0" style={{width:`${pct}%`, background:'rgba(15,118,110,0.04)'}}/>
                </li>
              );
            })}
          </ul>
          <div className="p-2 text-[10px] mono text-ink-400">Heatmap by self-time · click row to drill into function · ▼ expand</div>
        </Panel>

        {/* Code with line profiling */}
        <Panel className="col-span-7" title="ПолучитьОстаткиТоваровНаСкладах()"
          sub="ОбщийМодуль СкладСервер · server · Module лежит в УТ 11.5.18.235 / РасчётыСКонтрагентамиСервер"
          right={<>
            <SegGroup><SegBtn active>profile</SegBtn><SegBtn>annotations</SegBtn><SegBtn>blame</SegBtn></SegGroup>
            <button className="text-[11px] h-7 px-2 border hl2 rounded text-ink-600 hover:bg-ink-50 ml-2">Open in 1С Configurator →</button>
          </>}
          pad={false}>
          <div className="codebox m-3 overflow-hidden">
            <table className="w-full text-[12px] mono leading-[1.55]">
              <tbody>
                {code.map((row,i)=>{
                  const [num, txt, calls, time, tone] = row;
                  const bg = tone==='hot'?'rgba(220,38,38,0.10)':tone==='warn'?'rgba(217,119,6,0.08)':'transparent';
                  return (
                    <tr key={i} style={{background:bg}}>
                      <td className="text-right pr-2 pl-2 text-ink-400 select-none tnum w-10">{num}</td>
                      <td className="pr-3 whitespace-pre">{renderBSL(txt)}</td>
                      <td className="w-20 text-right text-ink-500 tnum">{calls}</td>
                      <td className={`w-20 text-right tnum ${tone==='hot'?'text-err font-semibold':tone==='warn'?'text-warn':'text-ink-500'} pr-2`}>{time}</td>
                      <td className="w-3">{tone==='hot' && <span className="mono text-[10px] text-err">◀</span>}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Panel>

        {/* Recommendations */}
        <Panel className="col-span-7" title={<span className="flex items-center gap-1.5"><I.Sparkles size={13} className="text-teal-700"/>AI suggestions for this code</span>} sub="line-level">
          <ul className="divide-y divide-ink-100">
            <Suggestion line="249" tone="warn" title="Virtual table .Остатки() без фильтра по периоду"
              body={<>Добавьте параметр <span className="mono">&Период</span> в виртуальную таблицу. Это снимет полное сканирование и даст SQL возможность seek по индексу <span className="mono">_Period_Fld5640RRef</span>.</>}
              ai="Confidence 92% — паттерн встречается в Knowledge Base (Slow query in virtual table Остатки without period filter)"/>
            <Suggestion line="254" tone="err"  title="Этот запрос выполняется 12K раз в день · 1.8s avg"
              body={<>Кэшируйте результат на длительность транзакции через <span className="mono">МеждуЗапросный.Кэш</span> или измените архитектуру: вынесите выборку остатков в один батч-запрос по всем строкам ТЧ, а не в цикле по строкам.</>}
              ai="Predicted impact: −85% времени проведения · −1.5s avg"/>
            <Suggestion line="256" tone="info" title="Цикл по 892K строк · подозрительно"
              body={<>Документ редко содержит больше 200 строк — но цикл срабатывает 892K раз/сутки. Похоже, есть отрицательные остатки, которые провоцируют коррекцию на каждой итерации.</>}
              ai="Possibly false positive — стоит проверить распределение размеров ТЧ"/>
          </ul>
        </Panel>

        <Panel className="col-span-5" title="Hot SQL spawned by this function" sub="aggregated · 24h">
          <SQLBlock>{`SELECT TOP 100
    T1._Fld5641 AS Номенклатура,
    SUM(T1._Fld5642) AS КоличествоОстаток
FROM _AccumRgT5634 T1 WITH (NOLOCK)
WHERE T1._Fld5645RRef = @P1 -- &Склад
GROUP BY T1._Fld5641
OPTION (RECOMPILE)`}</SQLBlock>
          <div className="mt-2 grid grid-cols-3 gap-1.5">
            <Stat2 label="avg" value="1.81s" tone="err"/>
            <Stat2 label="calls/day" value="12K"/>
            <Stat2 label="reads/call" value="234K"/>
          </div>
          <button className="mt-2 w-full h-7 text-[11.5px] border hl2 rounded bg-teal-50 text-teal-700">Open in Slow Queries →</button>
        </Panel>
      </div>
    </div>
  );
}

function Suggestion({ line, tone, title, body, ai }) {
  return (
    <li className="py-2.5 flex gap-2.5">
      <Badge tone={tone}>line {line}</Badge>
      <div className="flex-1">
        <div className="text-[12.5px] font-semibold">{title}</div>
        <div className="text-[11.5px] text-ink-600 mt-0.5">{body}</div>
        <div className="text-[10.5px] mono text-ink-400 mt-1 flex items-center gap-1"><I.Sparkles size={10} className="text-teal-700"/>{ai}</div>
      </div>
      <div className="flex gap-1">
        <button className="text-[10.5px] h-6 px-1.5 border hl2 rounded hover:bg-ink-50">Diff</button>
        <button className="text-[10.5px] h-6 px-1.5 border hl2 rounded bg-teal-700 text-white hover:bg-teal-800">Apply</button>
      </div>
    </li>
  );
}

function renderBSL(line) {
  if (!line) return '';
  const kws = /\b(Процедура|Функция|КонецПроцедуры|КонецФункции|Возврат|Если|Тогда|Иначе|КонецЕсли|Для|Каждого|Из|Цикл|КонецЦикла|Новый|Запрос|Перем|Знач|Истина|Ложь|Неопределено|И|ИЛИ|НЕ|Пока|Прервать|Продолжить|Экспорт)\b/g;
  // simple coloring
  let parts = [{t: line, c: null}];
  const apply = (regex, c) => {
    const out=[]; for (const p of parts) {
      if (p.c) { out.push(p); continue; }
      let last=0,m; regex.lastIndex=0;
      while((m=regex.exec(p.t))) {
        if (m.index>last) out.push({t:p.t.slice(last,m.index),c:null});
        out.push({t:m[0], c});
        last=m.index+m[0].length;
      }
      if (last<p.t.length) out.push({t:p.t.slice(last),c:null});
    }
    parts = out;
  };
  apply(/"([^"\\]|\\.)*"/g, '#16A34A');
  apply(/\/\/.*$/g, '#737373');
  apply(kws, '#0F766E');
  apply(/\b\d+(\.\d+)?\b/g, '#D97706');
  return parts.map((p,i)=> p.c ? <span key={i} style={{color:p.c}}>{p.t}</span> : <span key={i}>{p.t}</span>);
}

window.ProfilerScreen = ProfilerScreen;
