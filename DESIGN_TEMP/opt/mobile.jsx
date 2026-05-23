/* SCREEN 18: Mobile Web Companion */
function MobileCompanionScreen() {
  return (
    <div>
      <PageHeader breadcrumbs={['Manage','Mobile Companion']} title="Mobile Web Companion"
        sub="responsive web — для пейджера на дежурстве и быстрых проверок"
        right={<>
          <SegGroup><SegBtn active>iPhone</SegBtn><SegBtn>iPad</SegBtn><SegBtn>Both</SegBtn></SegGroup>
        </>}/>

      <div className="grid grid-cols-2 gap-6 p-6 max-w-[1200px] mx-auto">
        {/* iPad mock */}
        <div>
          <div className="text-[12px] mono uppercase tracking-wider text-ink-400 mb-2">iPad · landscape · 1180 × 820</div>
          <IpadFrame/>
        </div>

        {/* Phone mock */}
        <div>
          <div className="text-[12px] mono uppercase tracking-wider text-ink-400 mb-2">iPhone · portrait · 390 × 844</div>
          <PhoneFrame/>
        </div>
      </div>

      <div className="px-6 pb-8 max-w-[1200px] mx-auto">
        <Panel title="Notes on the mobile companion">
          <ul className="text-[12.5px] space-y-1.5 text-ink-700 leading-snug">
            <li>· Покрытие сценариев: <b>Apdex и здоровье</b> за 30 сек., <b>топ-5 alerts</b>, <b>быстрый ack / снять с дежурства</b>, <b>чат с AI</b> в дороге.</li>
            <li>· Для расследований и кода — desktop, без компромиссов. Web-companion не пытается быть полнофункциональным.</li>
            <li>· Авторизация через корпоративный SSO + биометрия на устройстве. Сессии TTL 8 ч.</li>
            <li>· Поддержка push-уведомлений (Telegram bridge или native push) — настройка в Alerts → Rules.</li>
          </ul>
        </Panel>
      </div>
    </div>
  );
}

function IpadFrame() {
  return (
    <div className="rounded-[24px] bg-ink-900 p-3 shadow-pop" style={{width: 720}}>
      <div className="rounded-[18px] bg-white overflow-hidden" style={{width: '100%', height: 480}}>
        {/* simulated mobile chrome */}
        <div className="h-9 bg-white border-b hl flex items-center px-3 gap-2">
          <div className="w-5 h-5 rounded-[5px] bg-ink-900 text-white grid place-items-center mono text-[8.5px] font-bold">1C</div>
          <span className="text-[11.5px] font-semibold">УТ 11.5 — Production</span>
          <I.ChevronDown size={11} className="text-ink-400"/>
          <div className="ml-auto flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-warn"></span>
            <span className="text-[11px] mono">3 active</span>
            <I.Bell size={13} className="text-ink-600 ml-2"/>
            <div className="w-5 h-5 rounded-full bg-teal-700 text-white text-[8.5px] grid place-items-center font-semibold ml-1">ИС</div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 p-3 bg-ink-25 h-[calc(100%-36px)]">
          {/* Health */}
          <div className="bg-white border hl2 rounded p-3 col-span-2">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-warn-bg grid place-items-center"><I.AlertTriangle size={20} className="text-warn"/></div>
              <div>
                <div className="text-[13px] font-semibold text-warn">3 Active Warnings</div>
                <div className="text-[11px] text-ink-500">1 critical · 1 anomaly · 1 slow query</div>
              </div>
              <div className="ml-auto flex items-end gap-5">
                <div>
                  <div className="mono text-[9.5px] text-ink-400 uppercase tracking-wider">Apdex</div>
                  <div className="mono tnum font-semibold text-[20px] text-warn">0.87</div>
                </div>
                <div>
                  <div className="mono text-[9.5px] text-ink-400 uppercase tracking-wider">Sessions</div>
                  <div className="mono tnum font-semibold text-[20px]">147</div>
                </div>
                <div>
                  <div className="mono text-[9.5px] text-ink-400 uppercase tracking-wider">Errors</div>
                  <div className="mono tnum font-semibold text-[20px] text-warn">3</div>
                </div>
              </div>
            </div>
          </div>

          {/* Alerts */}
          <div className="bg-white border hl2 rounded p-3">
            <div className="text-[11.5px] font-semibold mb-1.5">Active alerts</div>
            <ul className="space-y-1 text-[11px]">
              {[
                ['#1247','Deadlock #1247','err'],
                ['#1246','Memory leak rphost #3','err'],
                ['#1241','Pattern #892','warn'],
                ['#1239','Tempdb 8 GB','warn'],
              ].map(a=>(
                <li key={a[0]} className="flex items-center gap-1.5 border-b hl pb-1">
                  <Sev level={a[2]} size={6}/>
                  <span className="truncate">{a[1]}</span>
                  <span className="ml-auto mono text-[10px] text-ink-400">{a[0]}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Timeline mini */}
          <div className="bg-white border hl2 rounded p-3">
            <div className="text-[11.5px] font-semibold mb-1.5">Apdex · last 24h</div>
            <Spark data={[0.91,0.89,0.87,0.85,0.83,0.86,0.88,0.87,0.85,0.84]} w={280} h={60} strokeW={1.5}/>
            <div className="text-[10px] mono text-ink-400 mt-1">target 0.90 · 4 deadlocks</div>
          </div>

          {/* AI ask */}
          <div className="col-span-2 bg-teal-50/40 border hl rounded p-3">
            <div className="flex items-center gap-1.5 text-[10.5px] text-teal-800 mono font-semibold mb-1"><I.Sparkles size={11}/>Ask AI</div>
            <div className="border hl rounded bg-white px-2 py-1.5 text-[11.5px] text-ink-400">Что сейчас тормозит больше всего?</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function PhoneFrame() {
  return (
    <div className="rounded-[40px] bg-ink-900 p-3 shadow-pop mx-auto" style={{width: 320}}>
      <div className="relative rounded-[30px] bg-white overflow-hidden" style={{height: 640}}>
        {/* status bar */}
        <div className="absolute top-0 left-0 right-0 h-6 px-5 flex items-center justify-between mono text-[10px] z-10">
          <span>9:41</span>
          <span className="w-24 h-5 -mt-1 rounded-full bg-ink-900"></span>
          <span>5G ▮▮</span>
        </div>

        <div className="pt-7 px-3 pb-3 h-full overflow-hidden flex flex-col bg-ink-25">
          {/* header */}
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-[7px] bg-ink-900 text-white grid place-items-center mono text-[10px] font-bold">1C</div>
            <div className="flex-1 leading-tight">
              <div className="text-[12.5px] font-semibold">УТ 11.5 — Prod</div>
              <div className="mono text-[9.5px] text-ink-400">8.3.25.1394</div>
            </div>
            <button className="w-7 h-7 grid place-items-center rounded hover:bg-white"><I.Bell size={14}/></button>
          </div>

          {/* big health */}
          <div className="mt-3 bg-white border hl2 rounded-md p-3">
            <div className="flex items-center gap-2">
              <div className="w-12 h-12 rounded-full bg-warn-bg grid place-items-center"><I.AlertTriangle size={22} className="text-warn"/></div>
              <div>
                <div className="text-[13px] font-semibold text-warn">3 Warnings</div>
                <div className="text-[10.5px] text-ink-500">1 critical pattern</div>
              </div>
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2 text-center">
              <div>
                <div className="mono text-[8.5px] text-ink-400 uppercase tracking-wider">Apdex</div>
                <div className="mono tnum font-semibold text-[16px] text-warn">0.87</div>
              </div>
              <div>
                <div className="mono text-[8.5px] text-ink-400 uppercase tracking-wider">Sess</div>
                <div className="mono tnum font-semibold text-[16px]">147</div>
              </div>
              <div>
                <div className="mono text-[8.5px] text-ink-400 uppercase tracking-wider">Err/m</div>
                <div className="mono tnum font-semibold text-[16px] text-warn">3</div>
              </div>
            </div>
          </div>

          {/* alerts list */}
          <div className="mt-3 bg-white border hl2 rounded-md overflow-hidden">
            <div className="px-3 py-2 border-b hl text-[12px] font-semibold">Active alerts</div>
            <ul className="divide-y divide-ink-100 text-[11.5px]">
              {[
                ['Deadlock pattern #1247', '14:32','err'],
                ['Memory leak rphost #3',  '14:18','err'],
                ['Slow query family',      '13:47','warn'],
              ].map((a,i)=>(
                <li key={i} className="px-3 py-2 flex items-center gap-1.5">
                  <Sev level={a[2]} size={7}/>
                  <span className="flex-1 truncate">{a[0]}</span>
                  <span className="mono text-[10px] text-ink-400">{a[1]}</span>
                  <I.ChevronRight size={11} className="text-ink-300"/>
                </li>
              ))}
            </ul>
          </div>

          {/* AI ask */}
          <div className="mt-3 bg-teal-50/40 border hl rounded-md p-2.5">
            <div className="flex items-center gap-1 text-[10px] text-teal-800 mono font-semibold mb-1"><I.Sparkles size={10}/>Ask AI</div>
            <div className="bg-white border hl rounded px-2 py-1.5 text-[11px] text-ink-400">Что сейчас тормозит?</div>
          </div>

          {/* nav */}
          <div className="mt-auto flex items-center justify-around pt-3 border-t hl mono text-[9.5px] text-ink-500">
            <span className="flex flex-col items-center gap-0.5 text-teal-700"><I.Gauge size={16}/>Home</span>
            <span className="flex flex-col items-center gap-0.5"><I.Bell size={16}/>Alerts</span>
            <span className="flex flex-col items-center gap-0.5"><I.Sparkles size={16}/>AI</span>
            <span className="flex flex-col items-center gap-0.5"><I.User size={16}/>Me</span>
          </div>
        </div>
      </div>
    </div>
  );
}

window.MobileCompanionScreen = MobileCompanionScreen;
