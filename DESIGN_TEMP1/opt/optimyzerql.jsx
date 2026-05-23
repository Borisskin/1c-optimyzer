/* SCREEN 14: OptimyzerQL Console — the killer feature */
function OptimyzerQLScreen() {
  const [showDocs, setShowDocs] = React.useState(false);
  const [rtab, setRtab] = React.useState('table');

  return (
    <div className="flex flex-col h-[calc(100vh-48px-28px)]">
      <PageHeader breadcrumbs={['Manage','OptimyzerQL Console']} title={<span className="flex items-center gap-2">OptimyzerQL Console <Badge tone="teal">free tier</Badge></span>}
        sub="declarative query language over technical journal · 1С events · SQL events · code graph"
        right={<>
          <button className="h-7 px-2 text-[11px] border hl2 rounded text-ink-600 hover:bg-ink-50 flex items-center gap-1"><I.Book size={11}/>Templates</button>
          <button onClick={()=>setShowDocs(s=>!s)} className="h-7 px-2 text-[11px] border hl2 rounded text-ink-600 hover:bg-ink-50 flex items-center gap-1"><I.FileText size={11}/>Docs {showDocs?'←':'→'}</button>
          <button className="h-7 px-2 text-[11px] border hl2 rounded text-ink-600 hover:bg-ink-50 flex items-center gap-1"><I.Share size={11}/>Share</button>
          <button className="h-7 px-2 text-[11px] rounded bg-teal-700 text-white hover:bg-teal-800 flex items-center gap-1"><I.Play size={11}/>Run <KBD>⌘↵</KBD></button>
        </>}/>

      <div className="flex-1 grid grid-cols-[1fr_1fr] overflow-hidden">
        {/* Editor */}
        <section className="flex flex-col border-r hl bg-white overflow-hidden">
          <div className="px-3 h-9 border-b hl flex items-center gap-2">
            <button className="text-[11.5px] font-medium flex items-center gap-1 h-6 px-1.5 rounded hover:bg-ink-50">
              <I.FileText size={11} className="text-ink-500"/>find-slow-by-module.oql
              <I.ChevronDown size={11} className="text-ink-400"/>
            </button>
            <Badge tone="mute" className="ml-1">unsaved</Badge>
            <div className="ml-auto flex items-center gap-1 text-[10.5px] mono text-ink-400">
              ln 8 · col 12 · 18 rows
            </div>
          </div>

          <div className="flex-1 overflow-auto mono text-[12.5px] leading-[1.65]">
            <table className="w-full">
              <tbody>
                {[
                  ['1', '// Найти TOP-10 запросов длиннее 1с из модуля', 'cmt'],
                  ['2', '// РасчётыСКонтрагентамиСервер за последние 24h', 'cmt'],
                  ['3', '', null],
                  ['4', 'events', 'src'],
                  ['5', '| where Type == "DBMSSQL" and Duration > 1000ms', null],
                  ['6', '| where source_module == "РасчётыСКонтрагентамиСервер"', null],
                  ['7', '| timerange last 24h', null],
                  ['8', '| join code_graph on procedure_name', null],
                  ['9', '| project ts, sid, procedure, duration_ms,', null],
                  ['10','          sql_normalized, call_count, reads', null],
                  ['11','| order by duration_ms desc', null],
                  ['12','| limit 100', null],
                  ['13','', null],
                  ['14','// Дополнительно: распределение по типу wait', 'cmt'],
                  ['15','events', 'src'],
                  ['16','| where Type == "WAITS" and Wait_Type startswith "LCK_"', null],
                  ['17','| summarize total = sum(Wait_Time) by Wait_Type', null],
                  ['18','| render bar', null],
                ].map(([n, t, kind], i)=>(
                  <tr key={i} className="hover:bg-ink-25">
                    <td className="w-10 pr-2 text-right text-ink-300 select-none border-r hl tnum">{n}</td>
                    <td className="px-2.5 whitespace-pre">{renderOQL(t, kind)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* AI Helper */}
          <div className="border-t hl p-2.5 bg-ink-25/60">
            <div className="flex items-center gap-1.5 mb-1.5 text-teal-800">
              <I.Sparkles size={12}/>
              <span className="text-[11px] font-semibold mono">Natural language → OptimyzerQL</span>
              <span className="ml-auto text-[10px] text-ink-400">не знаете язык? опишите словами</span>
            </div>
            <div className="flex items-center gap-2 border hl2 rounded-md bg-white px-2 py-1.5">
              <I.Sparkles size={12} className="text-teal-700"/>
              <input defaultValue="Покажи все запросы дольше 1с из общего модуля РасчётыСКонтрагентамиСервер за последние сутки"
                className="flex-1 bg-transparent outline-none text-[12px] mono"/>
              <button className="text-[11px] mono h-6 px-2 rounded bg-teal-700 text-white">Generate</button>
            </div>
          </div>
        </section>

        {/* Results */}
        <section className="flex flex-col bg-white overflow-hidden">
          <div className="px-3 h-9 border-b hl flex items-center gap-2">
            <Tabs value={rtab} onChange={setRtab} dense tabs={[
              { id:'table',    label:'Table',    icon:I.FlaskList, count:47 },
              { id:'chart',    label:'Chart',    icon:I.Trend },
              { id:'timeline', label:'Timeline', icon:I.Activity },
              { id:'raw',      label:'Raw JSON', icon:I.Code },
            ]}/>
            <div className="ml-auto flex items-center gap-3 text-[10.5px] mono text-ink-400">
              <span>47 rows</span>
              <span>executed in 124 ms</span>
              <span>scanned 4.2 M events</span>
              <button className="h-6 px-2 rounded border hl2 text-ink-600 hover:bg-ink-50 flex items-center gap-1"><I.Download size={11}/>Export CSV</button>
            </div>
          </div>

          {rtab==='table' && <ResultsTable/>}
          {rtab==='chart' && <ResultsChart/>}
          {rtab==='timeline' && <ResultsTimeline/>}
          {rtab==='raw' && <ResultsRaw/>}
        </section>

        {/* Docs panel */}
        {showDocs && (
          <aside className="absolute top-[112px] right-0 bottom-7 w-[420px] bg-white border-l hl shadow-pop overflow-y-auto z-20 slide-in">
            <DocsPanel onClose={()=>setShowDocs(false)}/>
          </aside>
        )}
      </div>

      {/* Bottom: templates & saved */}
      <div className="border-t hl bg-ink-25/40 px-3 py-2 flex items-center gap-4 text-[11px] text-ink-500">
        <span className="mono text-[10.5px] uppercase tracking-wider text-ink-400">templates</span>
        {[
          'Find slow queries by module',
          'Detect deadlock patterns',
          'Memory analysis by rphost',
          'Sessions over X seconds',
          'Apdex regression vs yesterday',
          'Top BSL hot paths',
        ].map(t=>(
          <button key={t} className="hover:text-ink-900 mono">{t}</button>
        ))}
        <span className="ml-auto mono text-[10.5px] text-ink-400">SAVED · 8 queries</span>
      </div>
    </div>
  );
}

function renderOQL(text, kind) {
  if (!text) return '';
  if (kind==='cmt') return <span style={{color:'#737373'}}>{text}</span>;
  if (kind==='src') return <span><span style={{color:'#0F766E', fontWeight:600}}>{text}</span></span>;
  // tokenize
  let parts = [{t:text, c:null}];
  const apply = (re, c, w) => {
    const out=[]; for (const p of parts) {
      if (p.c) { out.push(p); continue; }
      let last=0,m; re.lastIndex=0;
      while((m=re.exec(p.t))) {
        if (m.index>last) out.push({t:p.t.slice(last,m.index),c:null});
        out.push({t:m[0], c, w});
        last = m.index+m[0].length;
      }
      if (last<p.t.length) out.push({t:p.t.slice(last),c:null});
    }
    parts = out;
  };
  apply(/\|/g, '#A3A3A3');
  apply(/\b(where|order by|project|limit|join|on|summarize|by|timerange|count|sum|avg|render|startswith|endswith|contains|in|and|or|not|last|asc|desc|bar|line|histogram)\b/g, '#0F766E', 600);
  apply(/"[^"]*"/g, '#16A34A');
  apply(/\b\d+(ms|s|h|m|d|K|M|G)?\b/g, '#D97706');
  apply(/[a-zA-Zа-яА-Я_]+(?=\()/g, '#2563EB');
  return parts.map((p,i)=> p.c ? <span key={i} style={{color:p.c, fontWeight:p.w||400}}>{p.t}</span> : <span key={i}>{p.t}</span>);
}

function ResultsTable() {
  const rows = [
    { ts:'14:32:11.402', sid:47,  procedure:'СформироватьТаблицуРасчётов', dur:8124, sql:'SELECT … FROM _AccumRgT5634 …', calls:1, reads:'234K' },
    { ts:'14:18:54.882', sid:89,  procedure:'СформироватьТаблицуРасчётов', dur:6234, sql:'SELECT … FROM _AccumRgT5634 …', calls:1, reads:'198K' },
    { ts:'14:02:08.114', sid:124, procedure:'ПроверитьВзаиморасчёты',      dur:5240, sql:'SELECT … FROM _AccumRgT5891 …', calls:1, reads:'88K'  },
    { ts:'13:47:00.211', sid:47,  procedure:'СформироватьТаблицуРасчётов', dur:4118, sql:'SELECT … FROM _AccumRgT5634 …', calls:1, reads:'164K' },
    { ts:'13:14:24.881', sid:112, procedure:'ВыполнитьПартионнуюКоррекцию',dur:3211, sql:'SELECT … FROM _AccumRg7821 …',  calls:1, reads:'42K'  },
    { ts:'12:55:12.014', sid:47,  procedure:'СформироватьТаблицуРасчётов', dur:3098, sql:'SELECT … FROM _AccumRgT5634 …', calls:1, reads:'124K' },
    { ts:'12:44:00.118', sid:89,  procedure:'ПроверитьВзаиморасчёты',      dur:2898, sql:'SELECT … FROM _AccumRgT5891 …', calls:1, reads:'62K'  },
    { ts:'12:21:33.481', sid:131, procedure:'ВыполнитьПартионнуюКоррекцию',dur:2741, sql:'SELECT … FROM _AccumRg7821 …',  calls:1, reads:'38K'  },
    { ts:'11:54:55.012', sid:64,  procedure:'СформироватьТаблицуРасчётов', dur:2401, sql:'SELECT … FROM _AccumRgT5634 …', calls:1, reads:'92K'  },
    { ts:'11:31:09.114', sid:47,  procedure:'СформироватьТаблицуРасчётов', dur:2156, sql:'SELECT … FROM _AccumRgT5634 …', calls:1, reads:'104K' },
    { ts:'11:02:55.124', sid:88,  procedure:'ПроверитьВзаиморасчёты',      dur:1944, sql:'SELECT … FROM _AccumRgT5891 …', calls:1, reads:'58K'  },
    { ts:'10:47:14.012', sid:124, procedure:'СформироватьТаблицуРасчётов', dur:1781, sql:'SELECT … FROM _AccumRgT5634 …', calls:1, reads:'88K'  },
    { ts:'10:22:00.114', sid:47,  procedure:'СформироватьТаблицуРасчётов', dur:1542, sql:'SELECT … FROM _AccumRgT5634 …', calls:1, reads:'72K'  },
    { ts:'09:55:12.488', sid:131, procedure:'ВыполнитьПартионнуюКоррекцию',dur:1402, sql:'SELECT … FROM _AccumRg7821 …',  calls:1, reads:'34K'  },
    { ts:'09:24:11.014', sid:64,  procedure:'СформироватьТаблицуРасчётов', dur:1289, sql:'SELECT … FROM _AccumRgT5634 …', calls:1, reads:'58K'  },
    { ts:'09:01:55.114', sid:89,  procedure:'ПроверитьВзаиморасчёты',      dur:1142, sql:'SELECT … FROM _AccumRgT5891 …', calls:1, reads:'48K'  },
    { ts:'08:44:33.014', sid:124, procedure:'СформироватьТаблицуРасчётов', dur:1024, sql:'SELECT … FROM _AccumRgT5634 …', calls:1, reads:'42K'  },
  ];
  return (
    <div className="overflow-auto">
      <table className="w-full text-[11.5px] mono">
        <thead className="bg-ink-25 sticky top-0">
          <tr>
            <Th w="140px">ts</Th>
            <Th align="right" w="50px">sid</Th>
            <Th>procedure</Th>
            <Th align="right" w="90px">duration_ms</Th>
            <Th w="280px">sql_normalized</Th>
            <Th align="right" w="60px">calls</Th>
            <Th align="right" w="64px">reads</Th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r,i)=>(
            <tr key={i} className="row border-t hl">
              <Td className="text-ink-500">{r.ts}</Td>
              <Td align="right" className="tnum">{r.sid}</Td>
              <Td>{r.procedure}</Td>
              <Td align="right" className={`tnum ${r.dur>=4000?'text-err font-semibold':r.dur>=2000?'text-warn font-semibold':''}`}>{r.dur.toLocaleString('en-US')}</Td>
              <Td className="text-ink-700 truncate max-w-[280px]">{r.sql}</Td>
              <Td align="right" className="tnum text-ink-500">{r.calls}</Td>
              <Td align="right" className="tnum text-ink-500">{r.reads}</Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ResultsChart() {
  // distribution chart
  return (
    <div className="p-4">
      <div className="text-[11.5px] mono text-ink-500 mb-2">AI suggested: histogram of duration_ms · 47 events</div>
      <Histogram/>
      <div className="mt-4 text-[11.5px] mono text-ink-500 mb-2">Top procedures by total time</div>
      <div className="space-y-1.5 text-[12px]">
        {[
          ['СформироватьТаблицуРасчётов', 24320, 78],
          ['ПроверитьВзаиморасчёты',       6298,  20],
          ['ВыполнитьПартионнуюКоррекцию', 5320,  17],
        ].map(([n,v,w],i)=>(
          <div key={i} className="flex items-center gap-2">
            <span className="mono w-64 truncate">{n}</span>
            <div className="flex-1 h-3 bg-ink-100 rounded-sm overflow-hidden">
              <div className="h-full bg-teal-700" style={{width: w + '%'}}/>
            </div>
            <span className="mono tnum w-24 text-right text-ink-700">{v.toLocaleString('en-US')} ms</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ResultsTimeline() {
  return (
    <div className="p-4">
      <div className="text-[11.5px] mono text-ink-500 mb-2">Events scattered along last 24h · 47 dots</div>
      <div className="relative h-[180px] border hl rounded-md bg-ink-25/40">
        {Array.from({length:47}).map((_,i)=>{
          const x = Math.random()*97;
          const y = Math.random()*85;
          const s = Math.random();
          return <span key={i} className={`absolute w-2 h-2 rounded-full ${s>0.85?'bg-err':s>0.6?'bg-warn':'bg-teal-700'} opacity-80`} style={{left:x+'%', top:y+'%'}}/>;
        })}
      </div>
    </div>
  );
}

function ResultsRaw() {
  return (
    <pre className="mono text-[11.5px] p-4 text-ink-700 leading-[1.6] whitespace-pre overflow-auto">
{`[
  {
    "ts": "2026-05-18T14:32:11.402Z",
    "sid": 47,
    "procedure": "РасчётыСКонтрагентамиСервер.СформироватьТаблицуРасчётов",
    "duration_ms": 8124,
    "sql_normalized": "SELECT T1._Fld5640RRef, SUM(T1._Fld5642) FROM _AccumRgT5634 T1 …",
    "call_count": 1,
    "logical_reads": 234891,
    "wait_type": "LCK_M_S",
    "wait_ms": 3420,
    "user": "Иванов И.С.",
    "client": "tcp:srv-1c-01.corp:1540"
  },
  {
    "ts": "2026-05-18T14:18:54.882Z",
    "sid": 89,
    ...
  }
]`}
    </pre>
  );
}

function DocsPanel({ onClose }) {
  return (
    <div>
      <div className="px-3 h-10 flex items-center border-b hl">
        <span className="text-[12.5px] font-semibold">OptimyzerQL · Reference</span>
        <button onClick={onClose} className="ml-auto h-7 w-7 grid place-items-center hover:bg-ink-50 rounded"><I.X size={14}/></button>
      </div>
      <div className="p-3 text-[12px] leading-relaxed space-y-3">
        <p className="text-ink-600">Декларативный язык над данными технологического журнала, событиями SQL Profiler, метриками агентов и графом конфигурации.</p>

        <div>
          <div className="text-[10.5px] mono uppercase tracking-wider text-ink-400 mb-1">Источники (sources)</div>
          <ul className="text-[11.5px] mono space-y-0.5 text-ink-700">
            <li><span className="text-teal-700">events</span>          · ТЖ + SQL profiler · all timestamps in UTC</li>
            <li><span className="text-teal-700">metrics</span>         · server agents, 1Hz</li>
            <li><span className="text-teal-700">deadlocks</span>       · парсенные xml_deadlock_report</li>
            <li><span className="text-teal-700">code_graph</span>      · модули/процедуры/имена, AST</li>
            <li><span className="text-teal-700">configurations</span>  · все версии конфигурации, ds</li>
          </ul>
        </div>

        <div>
          <div className="text-[10.5px] mono uppercase tracking-wider text-ink-400 mb-1">Операторы (pipe)</div>
          <ul className="text-[11.5px] mono space-y-0.5 text-ink-700">
            <li><span className="text-teal-700">| where</span> &lt;predicate&gt;</li>
            <li><span className="text-teal-700">| project</span> col1, col2, …</li>
            <li><span className="text-teal-700">| order by</span> col [asc|desc]</li>
            <li><span className="text-teal-700">| summarize</span> agg = sum(x) by col</li>
            <li><span className="text-teal-700">| join</span> &lt;source&gt; on col</li>
            <li><span className="text-teal-700">| timerange</span> last 24h | between …</li>
            <li><span className="text-teal-700">| limit</span> N</li>
            <li><span className="text-teal-700">| render</span> bar | line | histogram | timeline</li>
          </ul>
        </div>

        <div>
          <div className="text-[10.5px] mono uppercase tracking-wider text-ink-400 mb-1">Пример: топ ожиданий</div>
          <CodeBlock>{`events
| where Type == "WAITS"
| timerange last 1h
| summarize total = sum(Wait_Time)
            by Wait_Type
| order by total desc
| render bar`}</CodeBlock>
        </div>

        <div className="text-[11px] text-ink-500"><b>Free tier:</b> 30 дней ретеншена · query rate 60/min · все источники доступны. Pro даёт долгое хранилище и multi-base scope.</div>
      </div>
    </div>
  );
}

window.OptimyzerQLScreen = OptimyzerQLScreen;
