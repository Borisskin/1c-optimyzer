/* SCREEN 6: Cluster Health & Resources */
function ClusterScreen() {
  const rphosts = [
    { id:'#1', pid:'12381', cpu:54, mem:'2.1', memPct:52, sess:24, status:'ok', growth:'+2 MB/h', topCalls:[
      ['Документ.РеализацияТоваровУслуг.Запись', '1.2s'],
      ['Справочник.Контрагенты.ПередЗаписью',     '180ms'],
      ['Регламент.ОбменДанными_РЦ',                '8.4s'],
    ]},
    { id:'#2', pid:'12384', cpu:71, mem:'2.4', memPct:60, sess:31, status:'ok', growth:'+1 MB/h', topCalls:[
      ['Отчёт.ПродажиПоНоменклатуре',           '8.2s'],
      ['Документ.КорректировкаДолга',           '2.1s'],
      ['Документ.РеализацияТоваровУслуг.Запись','0.9s'],
    ]},
    { id:'#3', pid:'12387', cpu:88, mem:'1.2', memPct:30, sess:28, status:'err', growth:'+45 MB/h ⚠', topCalls:[
      ['Регламент.ОбменДанными_РЦ',              '12s'],
      ['Обработка.ЗакрытиеМесяца.Выполнить',     '340s'],
      ['Документ.РеализацияТоваровУслуг.Запись', '1.4s'],
    ]},
    { id:'#4', pid:'12391', cpu:62, mem:'3.8', memPct:95, sess:22, status:'warn', growth:'+12 MB/h', topCalls:[
      ['Отчёт.ОстаткиТоваровНаСкладах',          '4.1s'],
      ['Документ.ПоступлениеТоваров.Запись',     '1.8s'],
      ['Справочник.Номенклатура.ПередЗаписью',   '210ms'],
    ]},
    { id:'#5', pid:'12394', cpu:48, mem:'3.1', memPct:77, sess:19, status:'ok', growth:'+3 MB/h', topCalls:[
      ['Документ.ОприходованиеТоваров.Запись',   '0.7s'],
      ['Отчёт.ВыручкаПоОрганизациям',            '2.4s'],
      ['Документ.ВнутреннееПеремещение.Запись',  '1.1s'],
    ]},
    { id:'#6', pid:'12397', cpu:55, mem:'2.9', memPct:72, sess:23, status:'ok', growth:'+4 MB/h', topCalls:[
      ['Документ.ПоступлениеТоваров.Запись',     '1.6s'],
      ['Документ.СписаниеТоваров.Запись',        '0.5s'],
      ['Регламент.ПересчётИтогов',               '38s'],
    ]},
  ];

  return (
    <div>
      <PageHeader breadcrumbs={['Analyze','Cluster Health']} title="Cluster Health & Resources"
        sub="Кластер 1С: 1 ragent · 6 rphost · SQL: MS SQL 2022"
        kpis={<>
          <KPI label="ACTIVE SESSIONS" value="147" sub="peak 213 today"/>
          <KPI label="MEMORY USED" value="15.5 GB" sub="of 24 GB allocated"/>
          <KPI label="CPU AVG" value="63%" sub="peak 88% (rphost #3)" tone="warn"/>
          <KPI label="THROUGHPUT" value="12,847" sub="server calls/min"/>
          <KPI label="RESTARTS / 24H" value="1" sub="rphost #3 mem leak" tone="warn"/>
        </>}/>

      <div className="grid grid-cols-12 gap-3 p-3">
        <Panel className="col-span-9" title="Cluster topology" sub="hover node for details · edges show throughput">
          <ClusterTopology/>
        </Panel>

        <Panel className="col-span-3" title="Resource quotas" sub="cluster-wide">
          <ul className="space-y-2.5 text-[12px]">
            {[
              ['Memory per rphost',  '4 GB',   '15.5 / 24 GB'],
              ['CPU per server call','60 s',   'p99 24s'],
              ['Sessions per rphost','100',    'avg 24'],
              ['Connection timeout', '30 s',   '—'],
              ['Idle session TTL',   '20 min', '—'],
              ['Auth time limit',    '15 s',   'p95 480ms'],
            ].map((q,i)=>(
              <li key={i} className="flex items-center gap-2">
                <div className="flex-1">
                  <div className="text-ink-700">{q[0]}</div>
                  <div className="mono text-[10.5px] text-ink-400">{q[2]}</div>
                </div>
                <span className="mono tnum font-semibold">{q[1]}</span>
                <button className="text-[10.5px] text-teal-700 hover:underline mono">edit</button>
              </li>
            ))}
          </ul>
          <div className="div-h my-3"></div>
          <button className="w-full h-7 text-[11.5px] border hl2 rounded hover:bg-ink-50">Edit quotas →</button>
        </Panel>

        {rphosts.map(r=>(
          <div key={r.id} className={`col-span-4 bg-white border ${r.status==='err'?'border-err/30':r.status==='warn'?'border-warn/30':'hl2'} rounded-md shadow-panel`}>
            <div className={`flex items-center gap-2 px-3 h-10 border-b hl ${r.status==='err'?'bg-err-bg/40':r.status==='warn'?'bg-warn-bg/30':''}`}>
              <Sev level={r.status} size={9}/>
              <div className="leading-tight">
                <div className="text-[13px] font-semibold mono">rphost {r.id}</div>
                <div className="text-[10px] mono text-ink-400">pid {r.pid} · host srv-1c-{r.id.replace('#','0')}.corp</div>
              </div>
              <div className="ml-auto flex items-center gap-1">
                <button className="text-[10.5px] mono px-1.5 h-6 rounded border hl2 hover:bg-ink-50">Restart</button>
                <button className="text-[10.5px] mono px-1.5 h-6 rounded border hl2 hover:bg-ink-50">Detach</button>
              </div>
            </div>
            <div className="p-3">
              {/* CPU */}
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-[10.5px] mono uppercase tracking-wider text-ink-400 w-7">CPU</span>
                <div className="flex-1 h-1.5 bg-ink-100 rounded-sm overflow-hidden">
                  <div className={`h-full ${r.cpu>80?'bg-err':r.cpu>65?'bg-warn':'bg-teal-700'}`} style={{width:r.cpu+'%'}}/>
                </div>
                <span className="mono tnum text-[12px] font-semibold w-10 text-right">{r.cpu}%</span>
              </div>
              <Spark data={Array.from({length:30},(_,i)=>r.cpu - 10 + Math.sin(i*0.3)*8 + Math.random()*8)} w={300} h={28}/>

              {/* MEM */}
              <div className="flex items-center gap-2 mt-3 mb-1.5">
                <span className="text-[10.5px] mono uppercase tracking-wider text-ink-400 w-7">MEM</span>
                <div className="flex-1 h-1.5 bg-ink-100 rounded-sm overflow-hidden">
                  <div className={`h-full ${r.memPct>90?'bg-err':r.memPct>75?'bg-warn':'bg-teal-700'}`} style={{width:r.memPct+'%'}}/>
                </div>
                <span className="mono tnum text-[12px] font-semibold w-16 text-right">{r.mem} GB</span>
              </div>
              <div className="flex items-center justify-between text-[10.5px] mono text-ink-400">
                <span>{r.memPct}% of 4 GB limit</span>
                <span className={r.status==='err'?'text-err font-semibold':''}>{r.growth}</span>
              </div>

              <div className="div-h my-3"></div>

              <div className="grid grid-cols-3 text-[11.5px]">
                <div><div className="mono text-[10px] text-ink-400 uppercase tracking-wider">Sess.</div><div className="mono tnum font-semibold">{r.sess}</div></div>
                <div><div className="mono text-[10px] text-ink-400 uppercase tracking-wider">Calls</div><div className="mono tnum font-semibold">2.1k</div></div>
                <div><div className="mono text-[10px] text-ink-400 uppercase tracking-wider">Errors</div><div className="mono tnum font-semibold text-ink-700">{r.status==='err'?'12':'0'}</div></div>
              </div>

              <div className="div-h my-3"></div>

              <div className="text-[10px] mono uppercase tracking-wider text-ink-400 mb-1">Top server calls now</div>
              <ul className="space-y-1">
                {r.topCalls.map((c,i)=>(
                  <li key={i} className="flex items-center text-[11px]">
                    <span className="mono text-ink-700 truncate flex-1 max-w-[230px]">{c[0]}</span>
                    <span className="mono tnum text-ink-500 ml-2">{c[1]}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ))}

        <Panel className="col-span-12" title="SQL Server pulse" sub="MS SQL 2022 · srv-mssql-01.corp">
          <div className="grid grid-cols-6 gap-3">
            <SqlStat label="CPU"             value="82%" series={[55,60,65,70,75,80,85,80,75,80,85,82]} tone="warn"/>
            <SqlStat label="Memory"          value="86 GB" series={[80,82,83,84,85,86,86,86,86,86,86,86]}/>
            <SqlStat label="Buffer hit"      value="99.4%" series={[99.1,99.2,99.3,99.4,99.4,99.4]} tone="ok"/>
            <SqlStat label="Page life exp."  value="4,820s" series={[4500,4600,4700,4800,4820,4820]}/>
            <SqlStat label="Tempdb"          value="8.4 GB" series={[6,6.5,7,7.5,8,8.4]} tone="warn"/>
            <SqlStat label="Disk IO"         value="82 MB/s" series={[40,55,65,70,75,80,82]}/>
          </div>
        </Panel>
      </div>
    </div>
  );
}

function SqlStat({ label, value, series, tone='ink' }) {
  const color = tone==='warn'?'#D97706':tone==='err'?'#DC2626':tone==='ok'?'#16A34A':'#0F766E';
  return (
    <div className="border hl2 rounded-md p-2.5 bg-white">
      <div className="mono text-[10px] text-ink-400 uppercase tracking-wider">{label}</div>
      <div className={`mono tnum font-semibold text-[18px] ${tone==='warn'?'text-warn':tone==='err'?'text-err':tone==='ok'?'text-ok':'text-ink-900'}`}>{value}</div>
      <Spark data={series} w={170} h={26} color={color}/>
    </div>
  );
}

function ClusterTopology() {
  return (
    <svg viewBox="0 0 1100 340" className="w-full">
      <defs>
        <marker id="cl-arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="#A3A3A3"/>
        </marker>
      </defs>
      {/* edges */}
      {[
        // ragent → rphosts
        [120,170, 360,60],[120,170, 360,135],[120,170, 360,210],[120,170, 360,285],
        // rphosts → sql
        [490,60, 800,170],[490,135, 800,170],[490,210, 800,170],[490,285, 800,170],
      ].map((c,i)=>(
        <line key={i} x1={c[0]} y1={c[1]} x2={c[2]} y2={c[3]} stroke="#D4D4D4" strokeWidth={i<4?1.6:i===4?3.2:i===5?2.4:i===6?2:1.4}/>
      ))}

      <TopoNode x={120} y={170} w={140} h={70} title="ragent" sub="cluster mgr" extra="port 1540" color="#0F766E"/>
      <TopoNode x={360} y={60}  w={130} h={50} title="rphost #1" sub="24 sess · 54%" color="#16A34A" small/>
      <TopoNode x={360} y={135} w={130} h={50} title="rphost #2" sub="31 sess · 71%" color="#16A34A" small/>
      <TopoNode x={360} y={210} w={130} h={50} title="rphost #3" sub="28 sess · 88% LEAK" color="#DC2626" highlight small/>
      <TopoNode x={360} y={285} w={130} h={50} title="rphost #4" sub="22 sess · 62%" color="#D97706" small/>
      <TopoNode x={360} y={350} w={130} h={50} title="rphost #5" sub="19 sess · 48%" color="#16A34A" small hide/>
      <TopoNode x={800} y={170} w={180} h={90} title="MS SQL Server" sub="2022 · 16 cores" extra="82% CPU · 86 GB" color="#0F766E"/>

      {/* labels on edges */}
      <text x={250} y={155} fontSize="10" className="mono" fill="#525252">RMI</text>
      <text x={650} y={160} fontSize="10" className="mono" fill="#525252">TDS</text>
      <text x={970} y={165} fontSize="10" className="mono" fill="#525252">3,247 conn</text>

      {/* legend */}
      <g transform="translate(20, 310)">
        <rect width="320" height="22" rx="3" fill="#FAFAFA" stroke="#EDEDED"/>
        <text x={10} y={15} fontSize="10.5" className="mono" fill="#737373">edge width ∝ throughput · click node for drill-down</text>
      </g>
    </svg>
  );
}
function TopoNode({ x, y, w, h, title, sub, extra, color, highlight, small, hide }) {
  if (hide) return null;
  return (
    <g>
      {highlight && <rect x={x-w/2-3} y={y-h/2-3} width={w+6} height={h+6} rx={7} fill="none" stroke="#DC2626" strokeDasharray="3 3" opacity="0.75"/>}
      <rect x={x-w/2} y={y-h/2} width={w} height={h} rx={5} fill="#FFFFFF" stroke={color} strokeWidth="1.6"/>
      <rect x={x-w/2} y={y-h/2} width={4} height={h} fill={color}/>
      <text x={x-w/2+12} y={y-h/2+18} fontSize={small?11:13} fontWeight="600" className="mono" fill="#0A0A0A">{title}</text>
      <text x={x-w/2+12} y={y-h/2+34} fontSize="10.5" fill="#525252">{sub}</text>
      {extra && <text x={x-w/2+12} y={y-h/2+50} fontSize="10" className="mono" fill="#A3A3A3">{extra}</text>}
    </g>
  );
}

window.ClusterScreen = ClusterScreen;
