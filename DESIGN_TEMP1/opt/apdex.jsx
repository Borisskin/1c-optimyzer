/* SCREEN 2: Apdex & SLA */
function ApdexScreen() {
  const apdexHistory = [0.89,0.88,0.91,0.92,0.90,0.87,0.88,0.86,0.87,0.85,0.84,0.86,0.89,0.88,0.87,0.85,0.83,0.86,0.88,0.87,0.85,0.84,0.86,0.87,0.88,0.85,0.83,0.87];
  const operations = [
    { name:'Проведение Документ.РеализацияТоваровУслуг', apdex:0.92, p50:'1.2s', p95:'3.4s', p99:'8.1s', count:'12,847', trend:'up',   tone:'ok'  },
    { name:'Проведение Документ.ПоступлениеТоваровУслуг', apdex:0.81, p50:'1.8s', p95:'5.2s', p99:'12.3s', count:'8,234', trend:'down', tone:'warn'},
    { name:'Закрытие месяца',                              apdex:0.42, p50:'187s', p95:'320s', p99:'540s', count:'23',     trend:'down', tone:'err' },
    { name:'Формирование отчёта «Продажи по контрагентам»', apdex:0.78, p50:'2.1s', p95:'6.7s', p99:'14.2s', count:'4,567', trend:'flat', tone:'warn'},
    { name:'Открытие списка Справочник.Контрагенты',        apdex:0.95, p50:'0.3s', p95:'0.8s', p99:'1.4s', count:'23,489',  trend:'flat', tone:'ok'  },
    { name:'Открытие формы Документ.Реализация',            apdex:0.93, p50:'0.4s', p95:'1.1s', p99:'2.2s', count:'18,234',  trend:'up',   tone:'ok'  },
    { name:'Проведение Документ.КорректировкаДолга',        apdex:0.76, p50:'2.3s', p95:'6.1s', p99:'13.4s', count:'1,892',  trend:'down', tone:'warn'},
    { name:'Расчёт зарплаты — Документ.НачислениеЗарплаты', apdex:0.71, p50:'12.4s',p95:'34s',  p99:'78s',  count:'347',     trend:'flat', tone:'warn'},
    { name:'Обмен данными с РИБ — узел РЦ',                 apdex:0.84, p50:'14s',  p95:'42s',  p99:'95s',  count:'288',     trend:'up',   tone:'warn'},
    { name:'Документ.ВнутреннееПеремещение.ОбработкаПроведения', apdex:0.88, p50:'1.4s', p95:'3.8s', p99:'7.9s', count:'2,341', trend:'flat', tone:'ok' },
    { name:'Документ.ОприходованиеТоваров.ОбработкаПроведения',  apdex:0.91, p50:'0.9s', p95:'2.4s', p99:'5.1s', count:'987',   trend:'up', tone:'ok' },
    { name:'Регламент.НачислениеАмортизации',                apdex:0.68, p50:'24s',  p95:'58s',  p99:'120s', count:'12',     trend:'down', tone:'err' },
    { name:'Отчёт.ОстаткиТоваровНаСкладах',                  apdex:0.86, p50:'1.2s', p95:'3.9s', p99:'8.4s', count:'3,128',   trend:'flat', tone:'ok' },
    { name:'Открытие списка Документ.РеализацияТоваровУслуг',apdex:0.94, p50:'0.4s', p95:'1.2s', p99:'2.6s', count:'9,832',   trend:'up',   tone:'ok' },
    { name:'Регламент.ПересчётИтоговРегистровНакопления',    apdex:0.55, p50:'42s',  p95:'128s', p99:'240s', count:'8',       trend:'flat', tone:'err' },
  ];

  // 7×24 heatmap
  const heatmap = Array.from({length:7}, (_, d) => Array.from({length:24}, (_, h) => {
    const base = (h>=9&&h<=12)?0.85:(h>=13&&h<=18)?0.55:0.15;
    const dayBoost = d===0?0.15:d===4?0.10:0;
    return Math.min(1, base + dayBoost + (Math.random()*0.1 - 0.05));
  }));

  return (
    <div>
      <PageHeader breadcrumbs={['УТ 11.5 — Production','Apdex & SLA']} title="Apdex & SLA" sub="executive view"
        right={<>
          <SegGroup>
            <SegBtn>1h</SegBtn><SegBtn>24h</SegBtn><SegBtn active>7d</SegBtn><SegBtn>30d</SegBtn><SegBtn>Custom</SegBtn>
          </SegGroup>
          <button className="ml-2 h-7 px-2 text-[11px] flex items-center gap-1 border hl2 rounded text-ink-600 hover:bg-ink-50"><I.Download size={12}/>Export</button>
        </>}/>

      <div className="grid grid-cols-12 gap-3 p-3">
        {/* Big apdex */}
        <Panel className="col-span-4" title="Weighted Apdex" sub="last 7 days">
          <div className="flex items-end gap-4">
            <div className="display text-[64px] leading-none font-semibold tracking-tighter tnum">0.87</div>
            <div className="pb-2">
              <Badge tone="warn">below target</Badge>
              <div className="text-[11px] text-ink-500 mt-1 mono">target 0.90 · baseline 0.85</div>
            </div>
          </div>
          <div className="mt-3">
            <Spark data={apdexHistory} w={360} h={56} strokeW={1.6}/>
            <div className="flex justify-between mono text-[10px] text-ink-400 mt-1">
              <span>Mon 12.05</span><span>Wed</span><span>Fri</span><span>Sun 18.05</span>
            </div>
          </div>
          <div className="div-h my-3"></div>
          <div className="grid grid-cols-3 text-[11.5px]">
            <div><div className="text-ink-400 mono text-[10px] uppercase tracking-wider">SATISFIED</div><div className="mono tnum font-semibold text-[15px] text-ok">78.3%</div><div className="text-[10.5px] text-ink-400 mono">&lt; 1.0 s</div></div>
            <div><div className="text-ink-400 mono text-[10px] uppercase tracking-wider">TOLERATING</div><div className="mono tnum font-semibold text-[15px] text-warn">17.4%</div><div className="text-[10.5px] text-ink-400 mono">1–4 s</div></div>
            <div><div className="text-ink-400 mono text-[10px] uppercase tracking-wider">FRUSTRATED</div><div className="mono tnum font-semibold text-[15px] text-err">4.3%</div><div className="text-[10.5px] text-ink-400 mono">&gt; 4 s</div></div>
          </div>
        </Panel>

        {/* SLA gauge */}
        <Panel className="col-span-4" title="SLA Compliance" sub="rolling 30 days">
          <div className="flex items-center gap-4">
            <Donut pct={96.4} size={104} stroke={10} color="#D97706"/>
            <div>
              <div className="display text-[28px] font-semibold tnum">96.4%</div>
              <div className="text-[11px] text-ink-500">SLA target 99.0% · queries &lt; 2s</div>
            </div>
          </div>
          <ul className="mt-3 text-[11.5px] space-y-1.5">
            <li className="flex justify-between"><span className="text-ink-500">Uptime</span><span className="mono tnum text-ok">99.94%</span></li>
            <li className="flex justify-between"><span className="text-ink-500">Apdex ≥ 0.85</span><span className="mono tnum text-warn">82.1%</span></li>
            <li className="flex justify-between"><span className="text-ink-500">Errors &lt; 0.5%</span><span className="mono tnum text-ok">0.18%</span></li>
            <li className="flex justify-between"><span className="text-ink-500">Сon. user ratio</span><span className="mono tnum text-ok">in budget</span></li>
            <li className="flex justify-between"><span className="text-ink-500">Incidents</span><span className="mono tnum">3 of 5 budget</span></li>
          </ul>
        </Panel>

        {/* SLA history */}
        <Panel className="col-span-4" title="SLA history" sub="last 12 weeks">
          <div className="flex items-end gap-1 h-[120px]">
            {[97.2,98.1,99.1,98.4,97.8,96.9,98.8,99.0,98.6,97.4,96.4,96.4].map((v,i)=>(
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div className="text-[10px] mono text-ink-400 tnum">{v}</div>
                <div className={`w-full ${v>=99?'bg-ok':v>=97?'bg-warn':'bg-err'} rounded-sm`} style={{height: ((v-95)/5)*100 + 'px', minHeight: '4px'}}></div>
              </div>
            ))}
          </div>
          <div className="flex justify-between mono text-[10px] text-ink-400 mt-1">
            <span>W08</span><span>W12</span><span>W16</span><span>W20</span>
          </div>
        </Panel>

        {/* Operations table */}
        <Panel className="col-span-12" title="Apdex breakdown by business operation" sub={`${operations.length} of 47`} right={
          <div className="flex items-center gap-1.5">
            <button className="text-[11px] h-6 px-2 border hl2 rounded text-ink-600 hover:bg-ink-50 flex items-center gap-1"><I.Filter size={11}/>Filter</button>
            <button className="text-[11px] h-6 px-2 border hl2 rounded text-ink-600 hover:bg-ink-50">Sort: total impact</button>
          </div>
        } pad={false}>
          <div className="overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead className="bg-ink-25">
                <tr>
                  <Th w="38%">Operation</Th>
                  <Th align="right" w="80px">Apdex</Th>
                  <Th align="right" w="70px">p50</Th>
                  <Th align="right" w="70px">p95</Th>
                  <Th align="right" w="70px">p99</Th>
                  <Th align="right" w="90px">Count</Th>
                  <Th align="center" w="100px">Trend (7d)</Th>
                  <Th align="right" w="80px">Total time</Th>
                  <Th align="left"  w="70px">Status</Th>
                </tr>
              </thead>
              <tbody>
                {operations.map((o,i)=>(
                  <tr key={i} className="row border-t hl">
                    <Td className="truncate max-w-0"><span className="mono text-[12px]">{o.name}</span></Td>
                    <Td align="right" mono className={`tnum font-semibold ${o.tone==='ok'?'text-ok':o.tone==='warn'?'text-warn':'text-err'}`}>{o.apdex.toFixed(2)}</Td>
                    <Td align="right" mono className="tnum">{o.p50}</Td>
                    <Td align="right" mono className="tnum">{o.p95}</Td>
                    <Td align="right" mono className="tnum">{o.p99}</Td>
                    <Td align="right" mono className="tnum text-ink-600">{o.count}</Td>
                    <Td align="center"><Spark data={Array.from({length:24},()=>0.7 + Math.random()*0.3)} w={86} h={18} strokeW={1.2}/></Td>
                    <Td align="right" mono className="tnum text-ink-500">{Math.round(parseFloat(o.p50)*0.8 + Math.random()*40)}s</Td>
                    <Td><Badge tone={o.tone}>{o.tone==='ok'?'healthy':o.tone==='warn'?'degraded':'critical'}</Badge></Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        {/* Heatmap */}
        <Panel className="col-span-8" title="Apdex heatmap" sub="day × hour · last week" right={
          <div className="flex items-center gap-3 text-[10.5px] mono text-ink-400">
            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-[#F0FDF4] border hl"/>0.95</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-[#DCFCE7] border hl"/></span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-[#FEF3C7] border hl"/>0.80</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-[#FECACA] border hl"/></span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-[#FCA5A5] border hl"/>0.50</span>
          </div>
        }>
          <Heatmap data={heatmap} w={780} h={172}/>
        </Panel>

        <Panel className="col-span-4" title="SLA risk drivers" sub="AI-ranked">
          <ol className="space-y-2 text-[12px]">
            {[
              {n:1, t:'Закрытие месяца', d:'Apdex 0.42 · 540s p99 · даёт −0.04 к общему Apdex', tone:'err'},
              {n:2, t:'Пересчёт итогов регистров', d:'eats 23% бюджета SLA · 120s p99', tone:'err'},
              {n:3, t:'НачислениеАмортизации',     d:'Apdex 0.68, медленно с 14.05', tone:'warn'},
              {n:4, t:'Поступление товаров',        d:'p95 5.2s, тренд ↓ за неделю', tone:'warn'},
            ].map(r=>(
              <li key={r.n} className="flex gap-2 items-start p-2 -mx-2 hover:bg-ink-25 rounded">
                <span className="w-5 h-5 grid place-items-center mono text-[10px] rounded bg-ink-100 tnum">{r.n}</span>
                <div className="flex-1">
                  <div className="font-medium">{r.t}</div>
                  <div className="text-[11px] text-ink-500">{r.d}</div>
                </div>
                <Sev level={r.tone} size={8}/>
              </li>
            ))}
          </ol>
        </Panel>
      </div>
    </div>
  );
}
window.ApdexScreen = ApdexScreen;
