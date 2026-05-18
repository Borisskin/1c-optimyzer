/* SCREEN 13: Multi-base View */
function MultiBaseScreen() {
  const bases = [
    { name:'УТ 11.5 — Group Holding',  env:'Production', users:480, apdex:0.92, sess:147, host:'srv-1c-01', incident:'3 days ago · resolved', tone:'ok',   v:'11.5.18.235' },
    { name:'БП 3.0 — Subsidiary А',    env:'Production', users:124, apdex:0.78, sess:34,  host:'srv-1c-02', incident:'12 hours ago · memory leak', tone:'warn', v:'3.0.144.198' },
    { name:'УТ 11.5 — Subsidiary Б',   env:'Production', users:96,  apdex:0.74, sess:42,  host:'srv-1c-02', incident:'4 hours ago · slow queries', tone:'warn', v:'11.5.18.235' },
    { name:'УТ 11.5 — Subsidiary В',   env:'Production', users:78,  apdex:0.88, sess:31,  host:'srv-1c-03', incident:'2 weeks ago',                tone:'ok',   v:'11.5.18.235' },
    { name:'ERP 2.5 — Main',           env:'Production', users:284, apdex:0.88, sess:88,  host:'srv-1c-04', incident:'1 week ago',                 tone:'ok',   v:'2.5.18.94' },
    { name:'УНФ 3.0 — Retail',         env:'Production', users:64,  apdex:0.91, sess:24,  host:'srv-1c-05', incident:'4 weeks ago',                tone:'ok',   v:'3.0.4.218' },
    { name:'УТ 11.5 — Staging',        env:'Staging',    users:8,   apdex:0.94, sess:3,   host:'srv-1c-06', incident:'never',                      tone:'ok',   v:'11.5.18.240' },
    { name:'УТ 11.5 — Dev',            env:'Dev',        users:5,   apdex:0.97, sess:2,   host:'srv-1c-06', incident:'never',                      tone:'ok',   v:'11.5.18.240' },
  ];

  return (
    <div>
      <PageHeader breadcrumbs={['Manage','Multi-base']} title="Multi-base View"
        sub={`${bases.length} connected bases · ${bases.reduce((s,b)=>s+b.users,0)} users total`}
        kpis={<>
          <KPI label="HEALTHY" value="6" sub="of 8 bases" tone="ok"/>
          <KPI label="DEGRADED" value="2" sub="БП Subsidiary А, УТ Б" tone="warn"/>
          <KPI label="OFFLINE" value="0" sub="all agents online"/>
          <KPI label="AVG APDEX" value="0.87" sub="weighted by users"/>
        </>}
        right={<>
          <button className="h-7 px-2 text-[11px] border hl2 rounded text-ink-600 hover:bg-ink-50 flex items-center gap-1"><I.Plus size={11}/>Connect base</button>
        </>}/>

      {/* Cards */}
      <div className="grid grid-cols-4 gap-3 p-3">
        {bases.map((b,i)=>(
          <div key={i} className={`bg-white border ${b.tone==='warn'?'border-warn/30':'hl2'} rounded-md shadow-panel hover:border-teal-700/30 transition cursor-pointer`}>
            <div className={`h-1 ${b.tone==='warn'?'bg-warn':b.tone==='err'?'bg-err':'bg-ok'} rounded-t-md`}></div>
            <div className="p-3">
              <div className="flex items-start gap-2">
                <Sev level={b.tone} size={10}/>
                <div className="flex-1">
                  <div className="text-[13px] font-semibold leading-tight">{b.name}</div>
                  <div className="text-[10.5px] mono text-ink-400 mt-0.5">{b.env} · {b.v}</div>
                </div>
                <Badge tone={b.env==='Production'?'mute':b.env==='Staging'?'info':'teal'}>{b.env.toUpperCase()}</Badge>
              </div>

              <div className="grid grid-cols-3 mt-3 text-[11.5px] leading-tight">
                <div>
                  <div className="text-[10px] mono uppercase tracking-wider text-ink-400">Apdex</div>
                  <div className={`mono tnum font-semibold text-[16px] ${b.apdex<0.8?'text-warn':b.apdex<0.7?'text-err':'text-ok'}`}>{b.apdex.toFixed(2)}</div>
                </div>
                <div>
                  <div className="text-[10px] mono uppercase tracking-wider text-ink-400">Users</div>
                  <div className="mono tnum font-semibold text-[16px]">{b.users}</div>
                </div>
                <div>
                  <div className="text-[10px] mono uppercase tracking-wider text-ink-400">Sess.</div>
                  <div className="mono tnum font-semibold text-[16px]">{b.sess}</div>
                </div>
              </div>

              <div className="mt-3">
                <Spark data={Array.from({length:24},(_,j)=>b.apdex + Math.sin(j*0.4)*0.04 + Math.random()*0.02)} w={250} h={28}/>
              </div>

              <div className="div-h my-2.5"></div>

              <div className="flex items-center justify-between text-[11px] text-ink-500">
                <span className="truncate">last incident: <span className={b.tone==='warn'?'text-warn':'text-ink-700'}>{b.incident}</span></span>
                <button className="text-teal-700 hover:underline flex items-center gap-0.5 mono">Open <I.ArrowRight size={10}/></button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Cross-base insights */}
      <div className="p-3 grid grid-cols-3 gap-3">
        <Panel className="col-span-2" title={<span className="flex items-center gap-1.5"><I.Sparkles size={13} className="text-teal-700"/>Cross-base AI insights</span>} sub="отчёт за 24 часа">
          <ul className="space-y-3">
            <li className="border hl2 rounded p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <Badge tone="warn">SHARED DEPENDENCY</Badge>
                <span className="text-[10.5px] mono text-ink-400">conf 89%</span>
              </div>
              <div className="text-[12.5px]">Все <b>4 базы Group Holding</b> показывают деградацию Apdex с <span className="mono">14:00</span> — общая причина: <span className="mono">srv-mssql-01.corp</span> CPU 89% (shared SQL Server).</div>
              <div className="mt-1.5 flex gap-1.5">
                <button className="text-[11px] h-6 px-2 rounded border hl2 hover:bg-ink-50">Open SQL pulse</button>
                <button className="text-[11px] h-6 px-2 rounded border hl2 hover:bg-ink-50">Schedule load-shedding</button>
              </div>
            </li>
            <li className="border hl2 rounded p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <Badge tone="info">BENCHMARK</Badge>
                <span className="text-[10.5px] mono text-ink-400">conf 96%</span>
              </div>
              <div className="text-[12.5px]">УТ в <b>Subsidiary А</b> выдаёт Apdex <b className="mono">0.78</b>, в <b>Subsidiary Б</b> — <b className="mono">0.74</b> при <b>одинаковой</b> конфигурации УТ 11.5.18.235. Разница в железе: SQL у Б на HDD vs SSD у А.</div>
            </li>
            <li className="border hl2 rounded p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <Badge tone="teal">PATTERN TRANSFER</Badge>
                <span className="text-[10.5px] mono text-ink-400">conf 93%</span>
              </div>
              <div className="text-[12.5px]">Fix <span className="mono">#1247</span> применён в <b>УТ Holding</b>. Рекомендуем применить в <b>УТ Subsidiary А, Б, В</b> — там детектирован тот же deadlock pattern. Estimated lift: 312 deadlocks/7d → ~0.</div>
              <div className="mt-1.5 flex gap-1.5">
                <button className="text-[11px] h-6 px-2 rounded bg-teal-700 text-white">Push fix to 3 bases</button>
                <button className="text-[11px] h-6 px-2 rounded border hl2 hover:bg-ink-50">Preview diff</button>
              </div>
            </li>
          </ul>
        </Panel>

        <Panel title="Apdex matrix" sub="bases × last 24h">
          <table className="w-full text-[11.5px]">
            <thead>
              <tr className="text-[10px] mono uppercase tracking-wider text-ink-400">
                <td className="py-1.5 text-left">Base</td>
                <td className="text-right">24h avg</td>
                <td className="text-right">Trend</td>
              </tr>
            </thead>
            <tbody>
              {bases.map((b,i)=>(
                <tr key={i} className="border-t hl">
                  <td className="py-1.5 pr-2">
                    <div className="mono text-[11px] truncate max-w-[140px]">{b.name.split('—')[1]?.trim() || b.name}</div>
                    <div className="text-[10px] mono text-ink-400">{b.name.split('—')[0]?.trim()}</div>
                  </td>
                  <td className="text-right">
                    <span className={`mono tnum font-semibold ${b.apdex<0.8?'text-warn':b.apdex<0.7?'text-err':'text-ink-900'}`}>{b.apdex.toFixed(2)}</span>
                  </td>
                  <td className="pl-2">
                    <Spark data={Array.from({length:18},(_,j)=>b.apdex - 0.04 + Math.random()*0.06)} w={48} h={16} strokeW={1.1}/>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      </div>
    </div>
  );
}
window.MultiBaseScreen = MultiBaseScreen;
