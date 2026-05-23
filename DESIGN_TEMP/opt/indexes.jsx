/* SCREEN 7: Indexes & Statistics Advisor */
function IndexesScreen() {
  const [tab, setTab] = React.useState('missing');

  const missing = [
    { table:'_AccumRgT5634', desc:'РасчётыСКонтрагентами', cols:'(_Period, _Fld5640RRef) INCLUDE (_Fld5642)', impact:70, hint:'High',  queries:12, time:'380 s/day', size:'145 MB', tone:'err' },
    { table:'_Reference234', desc:'Контрагенты',            cols:'(_Fld234_ИНН)',                                impact:32, hint:'Medium',queries:4,  time:'42 s/day',  size:'12 MB',  tone:'warn'},
    { table:'_Document156',  desc:'РеализацияТоваровУслуг', cols:'(_Date_Time, _Fld156Organization) INCLUDE (_Number)', impact:24, hint:'Medium', queries:8, time:'120 s/day', size:'42 MB',  tone:'warn'},
    { table:'_AccumRgT5891', desc:'Взаиморасчёты',          cols:'(_Period, _Fld5891Org, _Fld5891Cntr)',         impact:18, hint:'Low',   queries:3,  time:'24 s/day',  size:'78 MB',  tone:'mute'},
    { table:'_InfoRg5891',   desc:'НастройкиПартионногоУчёта', cols:'(_Fld5891_Org, _Fld5891_Партия)',           impact:12, hint:'Low',   queries:2,  time:'14 s/day',  size:'8 MB',   tone:'mute'},
  ];

  const unused = [
    { table:'_AccumRgT5634', name:'IX_AccumRgT5634_OldByDate', size:'68 MB', last:'never (30d)', writes:'2.4K/h', tone:'warn' },
    { table:'_Document156',  name:'IX_Document156_LegacyHash', size:'12 MB', last:'never (90d)', writes:'1.1K/h', tone:'warn' },
    { table:'_Reference234', name:'IX_Reference234_FullText',  size:'24 MB', last:'never (30d)', writes:'480/h',  tone:'mute' },
  ];

  const frag = [
    { name:'IX_AccumRgT5634_PeriodRecorder', table:'_AccumRgT5634', frag:78, size:'412 MB', tone:'err' },
    { name:'IX_Document156_Number',           table:'_Document156',  frag:54, size:'88 MB',  tone:'warn'},
    { name:'IX_Reference234_Name',            table:'_Reference234', frag:32, size:'24 MB',  tone:'mute'},
    { name:'IX_InfoRg5891_Period',            table:'_InfoRg5891',   frag:23, size:'14 MB',  tone:'mute'},
  ];

  const stats = [
    { name:'_AccumRgT5634', age:'14 days', rows:'2,341,892', skew:'high',   tone:'err'},
    { name:'_Document156',  age:'21 days', rows:'1,089,234', skew:'medium', tone:'warn'},
    { name:'_AccumRgT5891', age:'30 days', rows:'1,892,341', skew:'low',    tone:'mute'},
    { name:'_Reference234', age:'45 days', rows:'48,221',    skew:'low',    tone:'mute'},
  ];

  return (
    <div>
      <PageHeader breadcrumbs={['Analyze','Indexes & Stats']} title="Indexes & Statistics Advisor"
        sub="MS SQL 2022 · автоанализ за 7 дней"
        kpis={<>
          <KPI label="MISSING (HIGH)" value="5" sub="estimated +70% gain" tone="err"/>
          <KPI label="UNUSED" value="12" sub="reclaim 248 MB / faster writes"/>
          <KPI label="FRAGMENTED >30%" value="8" sub="of 234 indexes"/>
          <KPI label="STALE STATS" value="14" sub="last update > 14 days"/>
        </>}
        right={<button className="h-7 px-2 text-[11px] flex items-center gap-1 border hl2 rounded text-teal-700 bg-teal-50"><I.Play size={11}/>Run advisor now</button>}/>

      <Tabs value={tab} onChange={setTab} tabs={[
        { id:'missing', label:'Missing Indexes', icon:I.Plus, count:5 },
        { id:'unused',  label:'Unused', icon:I.X, count:12 },
        { id:'frag',    label:'Fragmented', icon:I.AlertTriangle, count:8 },
        { id:'stats',   label:'Stale Statistics', icon:I.Trend, count:14 },
        { id:'plans',   label:'Maintenance Plans', icon:I.Workflow, count:3 },
      ]}/>

      <div className="p-3">
        {tab==='missing' && (
          <Panel pad={false}>
            <table className="w-full text-[12px]">
              <thead className="bg-ink-25">
                <tr>
                  <Th>Table</Th>
                  <Th>Recommended index</Th>
                  <Th align="right" w="120px">Expected impact</Th>
                  <Th align="right" w="80px">Queries</Th>
                  <Th align="right" w="100px">Total time</Th>
                  <Th align="right" w="80px">Size</Th>
                  <Th align="right" w="140px">Action</Th>
                </tr>
              </thead>
              <tbody>
                {missing.map((r,i)=>(
                  <tr key={i} className="row border-t hl">
                    <Td>
                      <div className="mono text-[12px]">{r.table}</div>
                      <div className="text-[10.5px] text-ink-500">{r.desc}</div>
                    </Td>
                    <Td><span className="mono text-[11.5px]">{r.cols}</span></Td>
                    <Td align="right">
                      <div className="flex items-center gap-1.5 justify-end">
                        <div className="w-16 h-1.5 bg-ink-100 rounded-sm overflow-hidden">
                          <div className={`h-full ${r.tone==='err'?'bg-err':r.tone==='warn'?'bg-warn':'bg-teal-700'}`} style={{width:r.impact+'%'}}/>
                        </div>
                        <span className={`mono tnum font-semibold ${r.tone==='err'?'text-err':r.tone==='warn'?'text-warn':'text-ink-700'}`}>{r.hint}</span>
                      </div>
                    </Td>
                    <Td mono align="right" className="tnum">{r.queries}</Td>
                    <Td mono align="right" className="tnum text-ink-500">{r.time}</Td>
                    <Td mono align="right" className="tnum text-ink-500">{r.size}</Td>
                    <Td align="right">
                      <div className="flex justify-end gap-1">
                        <button className="text-[10.5px] mono px-1.5 h-6 rounded border hl2 hover:bg-ink-50">DDL</button>
                        <button className="text-[10.5px] mono px-1.5 h-6 rounded border hl2 hover:bg-ink-50">Why?</button>
                        <button className="text-[10.5px] mono px-1.5 h-6 rounded bg-teal-700 text-white hover:bg-teal-800">Apply</button>
                      </div>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* expanded row */}
            <div className="border-t hl bg-ink-25/40 px-4 py-3">
              <div className="text-[11px] mono uppercase tracking-wider text-ink-400 mb-1.5">Drill-in · _AccumRgT5634</div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="text-[11px] text-ink-500 mb-1">Suggested DDL</div>
                  <SQLBlock>{`CREATE NONCLUSTERED INDEX IX__AccumRgT5634_Period_Fld5640RRef
    ON _AccumRgT5634 (_Period, _Fld5640RRef)
    INCLUDE (_Fld5642)
    WITH (ONLINE = ON, DATA_COMPRESSION = PAGE)
    ON [PRIMARY]; -- est. 145 MB`}</SQLBlock>
                </div>
                <div>
                  <div className="text-[11px] text-ink-500 mb-1">Queries that will benefit</div>
                  <ul className="space-y-1 text-[11.5px] mono">
                    {[
                      ['РасчётыСКонтрагентамиСервер.СформироватьТаблицуРасчётов()', '380 s/day'],
                      ['ОтчётыСервер.СформироватьВыручкуПоКонтрагентам()',          '142 s/day'],
                      ['Регламент.ПересчётИтогов_РасчётыСКонтрагентами',            '38 s/day'],
                      ['Документ.КорректировкаДолга.ОбработкаПроведения()',         '24 s/day'],
                    ].map((q,i)=>(
                      <li key={i} className="flex border hl rounded p-1.5">
                        <span className="truncate flex-1 text-ink-700">{q[0]}</span>
                        <span className="tnum text-ink-500">{q[1]}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </Panel>
        )}

        {tab==='unused' && (
          <Panel pad={false}>
            <div className="px-3 py-2 text-[11.5px] text-ink-500 border-b hl">Эти индексы не использовались за последние 30 дней. Удаление ускорит вставки и обновления.</div>
            <table className="w-full text-[12px]">
              <thead className="bg-ink-25">
                <tr><Th>Index</Th><Th>Table</Th><Th align="right">Size</Th><Th align="right">Last seek</Th><Th align="right">Maintenance cost</Th><Th align="right">Action</Th></tr>
              </thead>
              <tbody>
                {unused.map((u,i)=>(
                  <tr key={i} className="row border-t hl">
                    <Td><span className="mono">{u.name}</span></Td>
                    <Td><span className="mono">{u.table}</span></Td>
                    <Td mono align="right" className="tnum">{u.size}</Td>
                    <Td mono align="right" className="tnum text-ink-500">{u.last}</Td>
                    <Td mono align="right" className="tnum">{u.writes}</Td>
                    <Td align="right"><button className="text-[10.5px] mono px-1.5 h-6 rounded border hl2 hover:bg-ink-50 text-err">Drop</button></Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        )}

        {tab==='frag' && (
          <Panel pad={false}>
            <table className="w-full text-[12px]">
              <thead className="bg-ink-25">
                <tr><Th>Index</Th><Th>Table</Th><Th align="right">Fragmentation</Th><Th align="right">Size</Th><Th align="right">Recommendation</Th></tr>
              </thead>
              <tbody>
                {frag.map((f,i)=>(
                  <tr key={i} className="row border-t hl">
                    <Td><span className="mono">{f.name}</span></Td>
                    <Td><span className="mono">{f.table}</span></Td>
                    <Td align="right">
                      <div className="flex justify-end items-center gap-1.5">
                        <div className="w-24 h-1.5 bg-ink-100 rounded-sm overflow-hidden">
                          <div className={`h-full ${f.tone==='err'?'bg-err':f.tone==='warn'?'bg-warn':'bg-teal-700'}`} style={{width:f.frag+'%'}}/>
                        </div>
                        <span className="mono tnum font-semibold">{f.frag}%</span>
                      </div>
                    </Td>
                    <Td mono align="right" className="tnum">{f.size}</Td>
                    <Td align="right" mono className="text-teal-700"><button className="hover:underline">REBUILD ONLINE</button></Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        )}

        {tab==='stats' && (
          <Panel pad={false}>
            <table className="w-full text-[12px]">
              <thead className="bg-ink-25">
                <tr><Th>Table</Th><Th align="right">Rows</Th><Th align="right">Last updated</Th><Th align="right">Skew</Th><Th align="right">Action</Th></tr>
              </thead>
              <tbody>
                {stats.map((s,i)=>(
                  <tr key={i} className="row border-t hl">
                    <Td><span className="mono">{s.name}</span></Td>
                    <Td mono align="right" className="tnum">{s.rows}</Td>
                    <Td mono align="right" className="tnum text-ink-500">{s.age}</Td>
                    <Td align="right"><Badge tone={s.tone}>{s.skew}</Badge></Td>
                    <Td align="right" mono className="text-teal-700"><button className="hover:underline">UPDATE STATISTICS</button></Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        )}

        {tab==='plans' && (
          <div className="grid grid-cols-3 gap-3">
            {[
              {n:'Nightly Reindex', sch:'02:00 daily', last:'success · 2h ago', next:'tonight 02:00', ops:'Online rebuild · only frag > 30%'},
              {n:'Statistics refresh', sch:'04:00 daily', last:'success · yesterday', next:'tonight 04:00', ops:'Full scan top 50 tables'},
              {n:'Tempdb cleanup',  sch:'06:00 weekly', last:'success · Sunday',    next:'next Sunday 06:00', ops:'Shrink + restart tempdb'},
            ].map((p,i)=>(
              <Panel key={i} dense title={p.n} sub={p.sch}>
                <ul className="text-[11.5px] space-y-1">
                  <li className="flex justify-between"><span className="text-ink-500">Last run</span><span className="mono text-ok">{p.last}</span></li>
                  <li className="flex justify-between"><span className="text-ink-500">Next run</span><span className="mono">{p.next}</span></li>
                  <li className="text-ink-700">{p.ops}</li>
                </ul>
                <button className="mt-2 text-[11px] text-teal-700 hover:underline">Edit plan →</button>
              </Panel>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
window.IndexesScreen = IndexesScreen;
