/* SCREEN 17: Reports & Analytics */
function ReportsScreen() {
  const [tpl, setTpl] = React.useState('weekly');

  const templates = [
    { id:'daily',    name:'Daily Operations',    sub:'для дежурного 1С:Эксперта · 1 страница', schedule:'daily 09:00' },
    { id:'weekly',   name:'Weekly Performance',  sub:'для тимлида · 4 страницы',               schedule:'Mon 09:00' },
    { id:'monthly',  name:'Monthly Executive',   sub:'для CIO · 8 страниц · PDF + Slack',     schedule:'1st of month' },
    { id:'incident', name:'Post-incident',       sub:'после каждого Critical incident',         schedule:'on-demand' },
    { id:'custom',   name:'Custom builder',      sub:'собрать свой шаблон',                     schedule:'—' },
  ];

  return (
    <div>
      <PageHeader breadcrumbs={['Manage','Reports']} title="Reports & Analytics"
        sub="регулярные отчёты для разных аудиторий · экспорт PDF, рассылка"
        right={<>
          <button className="h-7 px-2 text-[11px] border hl2 rounded text-ink-600 hover:bg-ink-50 flex items-center gap-1"><I.Download size={11}/>Download PDF</button>
          <button className="h-7 px-2 text-[11px] border hl2 rounded text-ink-600 hover:bg-ink-50 flex items-center gap-1"><I.Mail size={11}/>Email to stakeholders</button>
          <button className="h-7 px-2 text-[11px] rounded bg-teal-700 text-white flex items-center gap-1"><I.Refresh size={11}/>Schedule recurring</button>
        </>}/>

      <div className="grid grid-cols-[260px_1fr] gap-3 p-3">
        {/* Template list */}
        <aside className="bg-white border hl2 rounded-md shadow-panel">
          <div className="px-3 h-9 border-b hl flex items-center text-[12px] font-semibold">Templates</div>
          <ul>
            {templates.map(t=>(
              <li key={t.id}>
                <button onClick={()=>setTpl(t.id)} className={`w-full text-left px-3 py-2 border-b hl hover:bg-ink-25 ${t.id===tpl?'bg-teal-50/60 border-l-2 border-l-teal-700':''}`}>
                  <div className="text-[12.5px] font-medium">{t.name}</div>
                  <div className="text-[11px] text-ink-500">{t.sub}</div>
                  <div className="mt-1 mono text-[10px] text-ink-400">{t.schedule}</div>
                </button>
              </li>
            ))}
          </ul>
          <div className="px-3 py-2 border-t hl">
            <button className="text-[11px] text-teal-700 hover:underline flex items-center gap-1"><I.Plus size={11}/>New template</button>
          </div>
        </aside>

        {/* Preview */}
        <div className="bg-white border hl2 rounded-md shadow-panel overflow-hidden">
          <div className="px-3 h-9 border-b hl flex items-center gap-2 bg-ink-25/40">
            <span className="text-[12px] font-semibold">Preview · Weekly Performance Report</span>
            <span className="mono text-[10.5px] text-ink-400">page 1 of 4</span>
            <div className="ml-auto flex items-center gap-1.5">
              <SegGroup><SegBtn>← prev</SegBtn><SegBtn>next →</SegBtn></SegGroup>
              <button className="h-7 px-2 text-[11px] border hl2 rounded text-ink-600 hover:bg-ink-50">Customize</button>
            </div>
          </div>

          {/* PDF-like page */}
          <div className="p-6 max-w-[820px] mx-auto">
            <div className="border hl2 rounded-md shadow-panel bg-white p-8" style={{aspectRatio: '0.75', minHeight: 720}}>
              <header className="flex items-end justify-between border-b-2 border-ink-900 pb-3">
                <div>
                  <div className="text-[10px] mono uppercase tracking-wider text-ink-400">Performance Report</div>
                  <h1 className="text-[22px] font-semibold mt-0.5">Weekly Performance · УТ 11.5 Production</h1>
                  <div className="text-[11px] text-ink-500 mono">Week 20 · 12.05 – 18.05 · prepared 18.05 09:00</div>
                </div>
                <div className="text-right leading-tight">
                  <div className="mono text-[11px] text-ink-400">1C-Optimyzer</div>
                  <div className="mono text-[10px] text-ink-400">v2.7.118</div>
                </div>
              </header>

              <section className="mt-5">
                <div className="text-[10px] mono uppercase tracking-wider text-ink-400 mb-1">Executive summary</div>
                <p className="text-[13px] leading-relaxed">
                  Apdex weekly average <b>0.87</b> (target 0.90, baseline 0.85). SLA compliance: <b className="text-warn">96.4%</b>. <b>3 incidents</b> — два разрешены в течение MTTR. Recurring deadlock pattern <span className="mono">#1247</span> остаётся ведущей причиной деградации; fix готов и ожидает деплоя в release window 19.05.
                </p>
              </section>

              <section className="mt-5 grid grid-cols-3 gap-3">
                {[
                  ['Apdex (week)', '0.87', 'warn', '−0.02 vs prev'],
                  ['SLA compliance', '96.4%', 'warn', 'target 99.0%'],
                  ['Critical incidents', '3', 'err', '2 resolved'],
                  ['Deadlocks / day', '67', 'warn', '+18% wow'],
                  ['Top query time', '380 s', 'err', '23% SQL CPU'],
                  ['Cluster CPU avg', '63%', 'ok', 'within budget'],
                ].map(([l,v,t,s],i)=>(
                  <div key={i} className="border hl2 rounded p-2.5">
                    <div className="text-[9.5px] mono uppercase tracking-wider text-ink-400">{l}</div>
                    <div className={`mono tnum font-semibold text-[20px] mt-0.5 ${t==='warn'?'text-warn':t==='err'?'text-err':'text-ink-900'}`}>{v}</div>
                    <div className="text-[10.5px] text-ink-500 mono">{s}</div>
                  </div>
                ))}
              </section>

              <section className="mt-5">
                <div className="text-[10px] mono uppercase tracking-wider text-ink-400 mb-1">Apdex trend</div>
                <Spark data={[0.91,0.92,0.89,0.85,0.83,0.86,0.87]} w={720} h={70} strokeW={1.8}/>
                <div className="flex justify-between text-[10px] mono text-ink-400 mt-1">
                  <span>Mon 12.05</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun 18.05</span>
                </div>
              </section>

              <section className="mt-5">
                <div className="text-[10px] mono uppercase tracking-wider text-ink-400 mb-1">Top issues this week</div>
                <table className="w-full text-[11.5px]">
                  <thead className="text-[10px] mono uppercase tracking-wider text-ink-400">
                    <tr className="border-b hl"><td className="py-1">Issue</td><td className="text-right">Occurrences</td><td className="text-right">Impact</td><td className="text-right">Status</td></tr>
                  </thead>
                  <tbody>
                    {[
                      ['Deadlock pattern #1247', '312', 'Critical', 'Fix designed', 'err'],
                      ['Slow query СформироватьТаблицуРасчётов', '2,184', 'High',     'Index applied', 'ok'],
                      ['Memory leak rphost #3',  'continuous', 'High',     'Investigating', 'warn'],
                      ['Tempdb pressure (reports)', '34 spikes', 'Medium', 'Open', 'warn'],
                      ['Lock escalation _AccumRgT5891','18','Medium','Open','warn'],
                    ].map((r,i)=>(
                      <tr key={i} className="border-b hl">
                        <td className="py-1.5">{r[0]}</td>
                        <td className="py-1.5 text-right mono tnum">{r[1]}</td>
                        <td className="py-1.5 text-right">{r[2]}</td>
                        <td className="py-1.5 text-right"><Badge tone={r[4]}>{r[3]}</Badge></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>

              <section className="mt-5">
                <div className="text-[10px] mono uppercase tracking-wider text-ink-400 mb-1">AI recommendations (ranked)</div>
                <ol className="text-[12px] space-y-1.5">
                  <li className="flex gap-2"><span className="mono w-6 text-ink-400">01.</span><span>Деплой fix паттерна #1247 в окно 19.05 — ожидаемый эффект −300 deadlocks/week.</span></li>
                  <li className="flex gap-2"><span className="mono w-6 text-ink-400">02.</span><span>Партиционирование <span className="mono">_AccumRgT5634</span> по году — снимет capacity-риск (forecast: 78 дней).</span></li>
                  <li className="flex gap-2"><span className="mono w-6 text-ink-400">03.</span><span>Рефакторинг <span className="mono">РассчитатьСебестоимость()</span> в <span className="mono">СебестоимостьРасчётСервер</span> — устранит регресс Закрытия месяца.</span></li>
                </ol>
              </section>

              <footer className="mt-6 pt-3 border-t hl flex items-center text-[10px] mono text-ink-400">
                <span>1C-Optimyzer · УТ 11.5.18.235 prod · prepared automatically</span>
                <span className="ml-auto">page 1 / 4</span>
              </footer>
            </div>
          </div>
        </div>
      </div>

      {/* Custom report builder */}
      <div className="p-3">
        <Panel title="Custom report builder" sub="drag-and-drop виджеты для своего шаблона">
          <div className="grid grid-cols-[200px_1fr] gap-3">
            <div>
              <div className="text-[10px] mono uppercase tracking-wider text-ink-400 mb-1.5">Available widgets</div>
              <ul className="space-y-1 text-[11.5px]">
                {['Apdex card','Top issues table','Apdex sparkline','Heatmap day×hour','SLA gauge','Deadlock patterns','Top slow queries','Cluster CPU sparkline','Memory growth chart','AI recommendations'].map(w=>(
                  <li key={w} className="border hl2 rounded px-2 py-1 hover:border-teal-700/30 cursor-grab flex items-center gap-1.5"><I.Activity size={11} className="text-ink-400"/>{w}</li>
                ))}
              </ul>
            </div>
            <div className="border-2 border-dashed border-ink-150 rounded-md min-h-[200px] p-3 grid grid-cols-3 gap-2 bg-ink-25/40">
              <div className="border hl2 rounded p-2 bg-white">
                <div className="text-[10px] mono uppercase tracking-wider text-ink-400">Apdex</div>
                <div className="mono tnum text-[18px] font-semibold">0.87</div>
              </div>
              <div className="col-span-2 border hl2 rounded p-2 bg-white">
                <div className="text-[10px] mono uppercase tracking-wider text-ink-400">Apdex sparkline</div>
                <Spark data={[0.91,0.89,0.87,0.85,0.86,0.88]} w={300} h={40}/>
              </div>
              <div className="col-span-3 border-2 border-dashed border-ink-200 rounded p-3 text-center text-[11px] mono text-ink-400">drop widget here</div>
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}
window.ReportsScreen = ReportsScreen;
