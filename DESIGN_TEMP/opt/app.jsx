/* App shell — top bar, sidebar, routes */
const { useState: useState_app, useEffect: useEffect_app, useMemo: useMemo_app } = React;

const SCREENS = {
  dashboard:  () => <DashboardScreen />,
  apdex:      () => <ApdexScreen />,
  workbench:  () => <WorkbenchScreen />,
  queries:    () => <SlowQueriesScreen />,
  locks:      () => <LocksScreen />,
  cluster:    () => <ClusterScreen />,
  indexes:    () => <IndexesScreen />,
  profiler:   () => <ProfilerScreen />,
  health:     () => <HealthScanScreen />,
  compare:    () => <ComparisonScreen />,
  predictive: () => <PredictiveScreen />,
  resolution: () => <ResolutionScreen />,
  multibase:  () => <MultiBaseScreen />,
  oql:        () => <OptimyzerQLScreen />,
  knowledge:  () => <KnowledgeScreen />,
  alerts:     () => <AlertsScreen />,
  reports:    () => <ReportsScreen />,
  mobile:     () => <MobileCompanionScreen />,
};

function App() {
  const [active, setActive] = useState_app('dashboard');
  const [sbOpen, setSbOpen] = useState_app(false);
  const [cmdOpen, setCmdOpen] = useState_app(false);
  const [aiOpen, setAIOpen] = useState_app(false);
  const [env, setEnv] = useState_app('УТ 11.5 — Production');

  useEffect_app(() => {
    const h = (e) => {
      if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'p')) {
        e.preventDefault(); setCmdOpen(v=>!v);
      } else if (e.key === 'Escape') {
        setCmdOpen(false); setAIOpen(false);
      }
    };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, []);

  return (
    <div className="app" data-sidebar={sbOpen?'open':'closed'}>
      <TopBar env={env} setEnv={setEnv} openCmd={()=>setCmdOpen(true)} openAI={()=>setAIOpen(true)} alertsCount={3} healthLevel="warn"/>
      <Sidebar active={active} setActive={setActive} open={sbOpen} setOpen={setSbOpen}/>
      <main className="row-start-2 col-start-2 overflow-auto bg-ink-25">
        <div key={active} className="min-h-full">
          {SCREENS[active]?.() || <div className="p-8 text-ink-500">Not found</div>}
        </div>
      </main>
      <StatusBar env={env}/>
      <CommandPalette open={cmdOpen} onClose={()=>setCmdOpen(false)} onNav={setActive}/>
      <AIChat open={aiOpen} onClose={()=>setAIOpen(false)}/>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
