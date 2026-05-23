// Konvey Main Workspace — the hero screen.
// Takes a `variant` prop to drive which state is shown.

const D = window.KonveyData;

// --- Header ---
function WorkspaceHeader({ direction = 'both', banner }) {
  return (
    <div className="k-header">
      <button className="k-burger"><Icon.Menu/></button>
      <span className="k-logo">Konvey</span>
      <span style={{ color: 'var(--k-text-4)', fontSize: 11 }}>/</span>
      <span className="k-project-name">Обмен УТ 11.5 ↔ БП 3.0</span>
      <span className="k-crumb">/ <span className="k-mono">Document.РеализацияТоваровУслуг</span></span>

      <div className="k-progress-block">
        <div className="k-progress-bar"><span style={{ width: '82%' }}/></div>
        <span className="k-mono" style={{ fontVariantNumeric: 'tabular-nums' }}>220<span style={{ color: 'var(--k-text-3)' }}>/267</span></span>
        <span className="k-stat-pill"><span className="dot green"/>mapped 208</span>
        <span className="k-stat-pill"><span className="dot amber"/>review 12</span>
        <span className="k-stat-pill"><span className="dot red"/>conflicts 3</span>
      </div>

      <div className="k-direction-toggle">
        <button className={direction === 'src' ? 'active' : ''}>Source → ED</button>
        <button className={direction === 'both' ? 'active' : ''}>Оба</button>
        <button className={direction === 'tgt' ? 'active' : ''}>ED → Target</button>
      </div>
      <button className="k-btn sm"><span>Validate</span></button>
      <button className="k-btn sm"><span>Preview</span></button>
      <button className="k-btn sm primary"><span>Export</span><span className="kbd k-mono" style={{color:'rgba(255,255,255,0.7)'}}>⌘E</span></button>
      <button className="k-btn sm icon" title="Command Palette">
        <span className="k-kbd">⌘K</span>
      </button>
      <div className="k-avatar">КС</div>
    </div>
  );
}

// --- Left Sidebar ---
function LeftSidebar() {
  return (
    <div className="k-sidebar">
      <div className="k-sidebar-tools">
        <div className="k-search">
          <Icon.Search/>
          <span style={{ flex: 1 }}>Поиск по объектам, типам…</span>
          <span className="k-kbd">/</span>
        </div>
        <button className="k-btn icon sm" style={{ height: 26, width: 26 }} title="Фильтры">
          <Icon.Filter/>
        </button>
      </div>
      <div className="k-sidebar-tree">
        {D.sidebarTree.map((grp, gi) => (
          <div className="k-tree-group" key={gi}>
            <div className="head">
              <Icon.TriangleDown style={{ opacity: grp.open ? 1 : 0, transform: grp.open ? '' : 'rotate(-90deg)' }}/>
              {!grp.open && <Icon.Triangle/>}
              <span style={{ marginLeft: 2 }}>{grp.type}</span>
              <span className="count k-mono">{grp.count}</span>
            </div>
            {grp.open && grp.items && grp.items.map((it, i) => (
              <TreeRow key={i} {...it}/>
            ))}
          </div>
        ))}
      </div>
      <div className="k-sidebar-footer">
        <button className="k-btn sm" style={{ justifyContent: 'flex-start' }}>
          <Icon.Plus/>Добавить объект в обмен
        </button>
        <button className="k-btn sm ghost" style={{ justifyContent: 'flex-start' }}>
          <Icon.Sparkle/>Применить pattern…
        </button>
        <div className="stats">
          22 объекта · 267 PCR<br/>
          ~30% AI-suggested
        </div>
      </div>
    </div>
  );
}

// --- Center Mapping Area ---
function MappingColumns({ variant }) {
  const dragDrop = variant === 'drag-drop';
  const aiWorking = variant === 'ai-mapping';

  // For drag-drop: highlight source field s-cp, mark compatible ED targets
  const draggedId = dragDrop ? 's-cp' : null;
  const compatibleEdIds = ['e-cp-guid', 'e-cp-name', 'e-cp-inn', 'e-cp-kpp'];

  const mappedFromL = new Set(D.linesLE.map(l => l.from));
  const mappedToL   = new Set(D.linesLE.map(l => l.to));
  const mappedFromR = new Set(D.linesER.map(l => l.from));
  const mappedToR   = new Set(D.linesER.map(l => l.to));

  const statusByEdRight = {};
  D.linesER.forEach(l => { statusByEdRight[l.from] = l.status; });
  const statusByEdLeft = {};
  D.linesLE.forEach(l => { statusByEdLeft[l.to] = l.status; });
  const statusBySrcRight = {};
  D.linesLE.forEach(l => { statusBySrcRight[l.from] = l.status; });
  const statusByTgtLeft = {};
  D.linesER.forEach(l => { statusByTgtLeft[l.to] = l.status; });

  const linesLE = D.linesLE.map(l => ({
    ...l,
    dim: dragDrop && l.from !== draggedId,
  }));
  const linesER = D.linesER.map(l => ({ ...l, dim: dragDrop }));

  return (
    <div className="k-cols">
      {/* Source column */}
      <div className="k-col">
        <div className="k-col-head">
          <span className="side">УТ 11.5</span>
          <span className="arrow">→</span>
          <span style={{ color: 'var(--k-text-3)' }}>EnterpriseData</span>
          <span className="spacer"/>
          <span className="pill">Source</span>
        </div>
        <div className="k-col-body">
          {D.sourceFields.map((f, i) => (
            <FieldRow
              key={i}
              field={f}
              side="left"
              dragSource={dragDrop && f.id === draggedId}
              hasMappingR={mappedFromL.has(f.id)}
              mappingStatusR={statusBySrcRight[f.id]}
            />
          ))}
        </div>
      </div>

      {/* ED column */}
      <div className="k-col ed">
        <div className="k-col-head">
          <span className="side">EnterpriseData</span>
          <span className="pill">v1.8.6</span>
          <span className="spacer"/>
          <span style={{ fontFamily: 'var(--k-font-mono)', fontSize: 10.5, color: 'var(--k-text-3)' }}>Документ.РеализацияТоваровУслуг</span>
        </div>
        <div className="k-col-body">
          {D.edFields.map((f, i) => {
            let drop = null;
            if (dragDrop && f.id) {
              drop = compatibleEdIds.includes(f.id) ? 'ok' : 'bad';
            }
            const selected = !dragDrop && f.id === 'e-cp-guid';
            return (
              <FieldRow
                key={i}
                field={f}
                side="ed"
                selected={selected}
                drop={drop}
                hasMappingL={mappedToL.has(f.id)}
                hasMappingR={mappedFromR.has(f.id)}
                mappingStatusL={statusByEdLeft[f.id]}
                mappingStatusR={statusByEdRight[f.id]}
              />
            );
          })}
        </div>
      </div>

      {/* Target column */}
      <div className="k-col">
        <div className="k-col-head">
          <span style={{ color: 'var(--k-text-3)' }}>EnterpriseData</span>
          <span className="arrow">→</span>
          <span className="side">БП 3.0</span>
          <span className="spacer"/>
          <span className="pill">Target</span>
        </div>
        <div className="k-col-body">
          {D.targetFields.map((f, i) => (
            <FieldRow
              key={i}
              field={f}
              side="right"
              hasMappingL={mappedToR.has(f.id)}
              mappingStatusL={statusByTgtLeft[f.id]}
            />
          ))}
        </div>
      </div>

      {/* Global SVG overlay over the whole .k-cols box: draws both line groups */}
      <FullLineOverlay variant={variant} linesLE={linesLE} linesER={linesER}/>

      {/* Quick-edit popup on selected line — only in hero variant */}
      {variant === 'mapping-selected' && (
        <QuickEditPopup/>
      )}

      {/* AI working overlay */}
      {aiWorking && <AIWorkingOverlay/>}
    </div>
  );
}

// Renders SVG bezier lines spanning across the three columns.
// Column proportions: 30% / 40% / 30%. Line endpoints sit slightly inside each
// column's edge so the curves actually have horizontal travel.
function FullLineOverlay({ variant, linesLE, linesER }) {
  const HEAD = 30; // col-head height

  // Endpoints (% of total .k-cols width). Column proportions 30/40/30 mean
  // the source/ED boundary sits at 30% and the ED/target boundary at 70%.
  // Pull lines INTO each column just enough to clear row padding, and place
  // bezier control points right on the boundary — produces a clean S-curve.
  const X_SRC_OUT = 27;
  const X_ED_IN_L = 33;
  const X_ED_OUT  = 67;
  const X_TGT_IN  = 73;
  const BOUND_L   = 30;
  const BOUND_R   = 70;

  const renderLine = (ln, fromY, toY, x1, x2, cxMid, key) => {
    const status = ln.status || 'green';
    const cls = [status, ln.selected && 'selected', ln.dim && 'dim'].filter(Boolean).join(' ');
    return (
      <path
        key={key}
        d={`M ${x1}% ${fromY} C ${cxMid}% ${fromY}, ${cxMid}% ${toY}, ${x2}% ${toY}`}
        className={cls}
      />
    );
  };

  return (
    <svg
      className="k-line-layer"
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none' }}
    >
      {linesLE.map((ln, i) => {
        const fSrc = D.sourceFields.find(x => x.id === ln.from);
        const fEd  = D.edFields.find(x => x.id === ln.to);
        if (!fSrc || !fEd) return null;
        return renderLine(ln, HEAD + fSrc.y, HEAD + fEd.y, X_SRC_OUT, X_ED_IN_L, BOUND_L, `le-${i}`);
      })}
      {linesER.map((ln, i) => {
        const fEd  = D.edFields.find(x => x.id === ln.from);
        const fTgt = D.targetFields.find(x => x.id === ln.to);
        if (!fEd || !fTgt) return null;
        return renderLine(ln, HEAD + fEd.y, HEAD + fTgt.y, X_ED_OUT, X_TGT_IN, BOUND_R, `er-${i}`);
      })}

      {/* Endpoint dots */}
      {linesLE.map((ln, i) => {
        const fSrc = D.sourceFields.find(x => x.id === ln.from);
        const fEd  = D.edFields.find(x => x.id === ln.to);
        if (!fSrc || !fEd) return null;
        const color = ln.status === 'amber' ? 'var(--k-amber)' :
                      ln.status === 'red' ? 'var(--k-red)' :
                      ln.status === 'gray' ? 'var(--k-gray)' : 'var(--k-green)';
        const opacity = ln.dim ? 0.3 : 1;
        return (
          <g key={`dot-le-${i}`} opacity={opacity}>
            <circle cx={`${X_SRC_OUT}%`} cy={HEAD + fSrc.y} r="2.5" fill={color}/>
            <circle cx={`${X_ED_IN_L}%`} cy={HEAD + fEd.y} r="2.5" fill={color}/>
          </g>
        );
      })}
      {linesER.map((ln, i) => {
        const fEd  = D.edFields.find(x => x.id === ln.from);
        const fTgt = D.targetFields.find(x => x.id === ln.to);
        if (!fEd || !fTgt) return null;
        const color = ln.status === 'amber' ? 'var(--k-amber)' :
                      ln.status === 'red' ? 'var(--k-red)' :
                      ln.status === 'gray' ? 'var(--k-gray)' : 'var(--k-green)';
        const opacity = ln.dim ? 0.3 : 1;
        return (
          <g key={`dot-er-${i}`} opacity={opacity}>
            <circle cx={`${X_ED_OUT}%`} cy={HEAD + fEd.y} r="2.5" fill={color}/>
            <circle cx={`${X_TGT_IN}%`} cy={HEAD + fTgt.y} r="2.5" fill={color}/>
          </g>
        );
      })}
    </svg>
  );
}

// --- Quick edit popup (positioned over selected line in center) ---
function QuickEditPopup() {
  return (
    <div className="k-popup" style={{ left: 'calc(30% + 20px)', top: 240 }}>
      <div className="title">Reassign mapping · Контрагент → ?</div>
      <div className="options">
        <label>
          <span className="k-radio checked"/>
          КлючевыеСвойстваКонтрагент <span style={{ color: 'var(--k-text-3)' }}>(current)</span>
        </label>
        <label>
          <span className="k-radio"/>
          ИдентификаторКонтрагент
        </label>
        <label>
          <span className="k-radio"/>
          Удалить mapping
        </label>
      </div>
      <input className="k-input" style={{ marginTop: 8 }} placeholder="Подсказка для AI…"/>
      <div className="footer">
        <button className="k-btn sm ghost">Cancel</button>
        <button className="k-btn sm primary">Apply</button>
      </div>
    </div>
  );
}

// --- AI working overlay ---
function AIWorkingOverlay() {
  return (
    <div className="k-ai-overlay">
      <div className="title">AI auto-mapping в процессе</div>
      <div className="obj k-mono">Document.РеализацияТоваровУслуг</div>
      <div className="bar"><span style={{ width: '67%' }}/></div>
      <div className="meta"><span>8 / 12 полей</span><span>~7 сек</span></div>
      <div className="now">→ анализ поля <span style={{ color: 'var(--k-text)' }}>«Контрагент»</span></div>
      <div style={{ marginTop: 12, display: 'flex', justifyContent: 'flex-end' }}>
        <button className="k-btn sm ghost"><Icon.X/>Отменить</button>
      </div>
    </div>
  );
}

// --- Right Inspector ---
function Inspector({ variant }) {
  if (variant === 'object-selected') return <InspectorObject/>;
  return <InspectorMapping/>;
}

function InspectorMapping() {
  return (
    <div className="k-inspector">
      <div className="k-inspector-head">
        <div className="eyebrow">Mapping</div>
        <div className="k-mapping-pair">
          <div>УТ.Реализация.Контрагент</div>
          <span className="arrow">↓</span>
          <div>ED.Контрагент <span style={{color:'var(--k-text-3)'}}>· КлючевыеСвойстваКонтрагент</span></div>
        </div>
      </div>
      <div className="k-inspector-body">
        <div className="k-inspector-section">
          <div className="k-kv">
            <span className="k">Source type</span>
            <span className="v mono">CatalogRef.Контрагенты</span>
            <span className="k">ED type</span>
            <span className="v mono">КлючевыеСвойстваКонтрагент</span>
            <span className="k">Compatibility</span>
            <span className="v"><span className="k-badge green"><Icon.Check/>Совместимы</span></span>
            <span className="k">Confidence</span>
            <span className="v">high <span style={{ color: 'var(--k-text-3)' }}>(0.94)</span></span>
            <span className="k">Method</span>
            <span className="v">auto-name match + type check</span>
          </div>
        </div>

        <div className="k-inspector-section">
          <div className="label">AI Reasoning</div>
          <div className="k-reasoning">
            Имя поля совпадает, тип source — ссылка на справочник Контрагенты, тип EnterpriseData — стандартные ключевые свойства контрагента. Уверенность высокая, рекомендую approve без изменений.
          </div>
        </div>

        <div className="k-inspector-section">
          <div className="label">Стратегия поиска на приёмнике</div>
          <div className="k-radio-list">
            <label><span className="k-radio checked"/>По GUID</label>
            <label><span className="k-radio"/>По ИНН + КПП</label>
            <label><span className="k-radio"/>По наименованию</label>
            <label><span className="k-radio"/>Композитный (GUID → ИНН → наименование)</label>
          </div>
        </div>

        <div className="k-inspector-section">
          <div className="label">Conversion expression</div>
          <input className="k-input" placeholder="// Inline BSL преобразование…"/>
          <button className="k-btn sm ghost" style={{ alignSelf: 'flex-start', marginTop: 2 }}>
            <Icon.Arrow/>Открыть в Handler Editor
          </button>
        </div>

        <div className="k-inspector-section">
          <div className="label">Заметка пользователя</div>
          <textarea className="k-textarea" placeholder="Контекст для команды…"/>
        </div>

        <div className="k-inspector-section">
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <button className="k-btn sm primary"><Icon.Check/>Approve</button>
            <button className="k-btn sm"><Icon.X/>Reject</button>
            <button className="k-btn sm">Reassign</button>
            <button className="k-btn sm"><Icon.Sparkle/>Re-run AI</button>
          </div>
        </div>

        <div className="k-inspector-section">
          <div className="label">Hint для AI</div>
          <input className="k-input" placeholder="«не использовать поиск по наименованию»"/>
        </div>
      </div>
    </div>
  );
}

function InspectorObject() {
  return (
    <div className="k-inspector">
      <div className="k-inspector-head">
        <div className="eyebrow">Object</div>
        <div className="k-mapping-pair">Document.РеализацияТоваровУслуг</div>
      </div>
      <div className="k-inspector-body">
        <div className="k-inspector-section">
          <div className="label">Статистика</div>
          <div className="k-kv">
            <span className="k"><span className="k-badge green"><Icon.Check/></span> Mapped</span>
            <span className="v mono">12</span>
            <span className="k"><span className="k-badge amber"><Icon.Sparkle/></span> AI-suggested</span>
            <span className="v mono">4</span>
            <span className="k"><span className="k-badge red"><Icon.Warn/></span> Unresolved</span>
            <span className="v mono">2</span>
            <span className="k">Total handlers</span>
            <span className="v mono">8</span>
          </div>
        </div>

        <div className="k-inspector-section">
          <div className="label">Настройки ПКО</div>
          <div style={{ fontSize: 11, color: 'var(--k-text-3)' }}>Создавать новый при загрузке</div>
          <div className="k-radio-list">
            <label><span className="k-radio"/>Да</label>
            <label><span className="k-radio"/>Нет</label>
            <label><span className="k-radio checked"/>Только если не найден</label>
          </div>
          <div style={{ fontSize: 11, color: 'var(--k-text-3)', marginTop: 6 }}>Стратегия поиска</div>
          <div className="k-input" style={{ display:'flex', alignItems:'center', justifyContent:'space-between', cursor:'pointer' }}>
            <span className="k-mono">По уникальному идентификатору</span>
            <Icon.TriangleDown/>
          </div>
          <div style={{ fontSize: 11, color: 'var(--k-text-3)', marginTop: 6 }}>Направление обмена</div>
          <div className="k-radio-list">
            <label><span className="k-radio"/>Только выгрузка</label>
            <label><span className="k-radio"/>Только загрузка</label>
            <label><span className="k-radio checked"/>Оба направления</label>
          </div>
        </div>

        <div className="k-inspector-section">
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <button className="k-btn sm primary"><Icon.Sparkle/>Re-run AI mapping</button>
            <button className="k-btn sm">Apply pattern…</button>
            <button className="k-btn sm">Copy to similar…</button>
          </div>
        </div>

        <div className="k-inspector-section">
          <div className="label">Обработчики (4 события)</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div className="k-handler-row empty">
              <span className="dot"/>
              <span className="name">ПередКонвертациейОбъекта</span>
              <span className="meta">empty</span>
              <span className="pen"><Icon.Pen/></span>
            </div>
            <div className="k-handler-row filled">
              <span className="dot"/>
              <span className="name">ПриКонвертацииДанныхXDTO</span>
              <span className="meta">12 lines · 2h</span>
              <span className="pen"><Icon.Pen/></span>
            </div>
            <div className="k-handler-row filled">
              <span className="dot"/>
              <span className="name">ПриКонвертацииДанныхИзXDTO</span>
              <span className="meta">8 lines · 1d</span>
              <span className="pen"><Icon.Pen/></span>
            </div>
            <div className="k-handler-row empty">
              <span className="dot"/>
              <span className="name">ПослеКонвертацииОбъекта</span>
              <span className="meta">empty</span>
              <span className="pen"><Icon.Pen/></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Center wrapper with sub-header ---
function CenterArea({ variant }) {
  return (
    <div className="k-center">
      <div className="k-center-head">
        <Icon.Doc style={{ color: 'var(--k-text-2)' }}/>
        <span className="obj-name"><span className="kind">Document.</span>РеализацияТоваровУслуг</span>
        <button className="switch-obj">
          другой объект <Icon.TriangleDown/>
        </button>
        <span style={{ flex: 1 }}/>
        <button className="k-btn sm ghost">
          <Icon.Plus/>применить ко всем Document
        </button>
        <button className="k-btn sm icon" title="Меню объекта"><Icon.Kebab/></button>
      </div>
      <MappingColumns variant={variant}/>
    </div>
  );
}

// --- Bottom Dock variants ---
function BottomDock({ variant }) {
  const tab =
    variant === 'problems' ? 'problems' :
    variant === 'ai-chat' ? 'chat' :
    variant === 'preview' ? 'xml' :
    null;
  if (!tab) return null;

  return (
    <div className="k-dock" style={{ height: 280 }}>
      <div className="k-dock-tabs">
        <div className={`k-dock-tab ${tab === 'problems' ? 'active' : ''}`}>
          <Icon.Warn/>Problems
          <span className="badge">15</span>
        </div>
        <div className={`k-dock-tab ${tab === 'xml' ? 'active' : ''}`}>
          Generated XML
        </div>
        <div className={`k-dock-tab ${tab === 'chat' ? 'active' : ''}`}>
          <Icon.Sparkle/>AI Chat
        </div>
        <div className="k-dock-tab">
          History
        </div>
        <div className="k-dock-spacer"/>
        <button className="k-btn sm ghost icon"><Icon.X/></button>
      </div>
      <div className="k-dock-body">
        {tab === 'problems' && <ProblemsTab/>}
        {tab === 'xml' && <XmlTab/>}
        {tab === 'chat' && <ChatTab/>}
      </div>
    </div>
  );
}

function ProblemsTab() {
  const rows = [
    { sev: 'err', where: 'Реализация.Сумма', msg: 'Тип источника Число(15,2) несовместим с xs:string в EnterpriseData.Сумма', fix: true },
    { sev: 'err', where: 'Реализация.Комментарий', msg: 'Целевое поле Примечание имеет другую длину: source 500 → target 1024 (info), но обработчик усечения отсутствует', fix: true },
    { sev: 'err', where: 'ВозвратТоваровОтПокупателя.Контрагент', msg: 'Конфликт: два AI suggestion указывают на разные ED-поля (КлючевыеСвойстваКонтрагент vs ИдентификаторКонтрагент)', fix: false },
    { sev: 'warn', where: 'Catalog.Контрагенты', msg: 'Не задана стратегия поиска дубликатов на стороне приёмника', fix: true },
    { sev: 'warn', where: 'Реализация.Курс', msg: 'ПКС создан, но обработчик ПриКонвертации пуст — преобразование валюты не реализовано', fix: false },
    { sev: 'warn', where: 'Договоры.ДатаНачала', msg: 'AI suggestion с low confidence (0.42) — рекомендуется ручная проверка', fix: false },
    { sev: 'info', where: 'Реализация', msg: 'AI рекомендует добавить обработчик ПередКонвертациейОбъекта для проверки заполненности обязательных полей', fix: false },
  ];
  return (
    <div>
      <div className="k-problems-toolbar">
        <span className="k-sev-filter active"><Icon.Err style={{ color: 'var(--k-red)' }}/>Errors 3</span>
        <span className="k-sev-filter active"><Icon.Warn style={{ color: 'var(--k-amber)' }}/>Warnings 11</span>
        <span className="k-sev-filter active"><Icon.Info style={{ color: 'var(--k-accent)' }}/>Info 1</span>
        <span style={{ color: 'var(--k-text-4)', fontSize: 11 }}>·</span>
        <span style={{ color: 'var(--k-text-3)', fontSize: 11 }}>last run 2 min ago</span>
        <span style={{ flex: 1 }}/>
        <button className="k-btn sm">Run validation</button>
        <button className="k-btn sm primary"><Icon.Sparkle/>Auto-fix all (8)</button>
      </div>
      {rows.map((r, i) => {
        const ico = r.sev === 'err' ? <Icon.Err style={{ color: 'var(--k-red)' }}/> :
                    r.sev === 'warn' ? <Icon.Warn style={{ color: 'var(--k-amber)' }}/> :
                    <Icon.Info style={{ color: 'var(--k-accent)' }}/>;
        return (
          <div key={i} className="k-problem-row">
            <div className="sev">{ico}</div>
            <div className="where">{r.where}</div>
            <div className="msg">{r.msg}</div>
            <div className="actions">
              <button className="k-btn sm ghost">Перейти</button>
              {r.fix && <button className="k-btn sm">Auto-fix</button>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function XmlTab() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="k-problems-toolbar">
        <span className="k-sev-filter active">Правила выгрузки</span>
        <span className="k-sev-filter">Правила загрузки</span>
        <span className="k-sev-filter">EnterpriseData sample</span>
        <span style={{ flex: 1 }}/>
        <button className="k-btn sm ghost">Copy</button>
        <button className="k-btn sm">Save to file</button>
      </div>
      <pre className="k-mono" style={{
        flex: 1, margin: 0, padding: '12px 14px',
        fontSize: 11.5, lineHeight: 1.55,
        background: '#fafafa',
        color: 'var(--k-text-2)',
        overflow: 'auto',
      }}>
{`<ПравилаОбмена ВерсияФормата="3.1" ВерсияEnterpriseData="1.8.6">
  <Источник>УТ_11_5</Источник>
  <Приёмник>ED_1_8_6</Приёмник>

  <ПравилоКонвертацииОбъектов Имя="ПКО_Реализация">
    <Источник>Document.РеализацияТоваровУслуг</Источник>
    <Приёмник>Документ.РеализацияТоваровУслуг</Приёмник>
    <СоздаватьНовыйПриЗагрузке>ТолькоЕслиНеНайден</СоздаватьНовыйПриЗагрузке>
    <ПоискПо>УникальныйИдентификатор</ПоискПо>

    <Свойства>
      <ПКС Источник="Дата"        Приёмник="Дата"/>
      <ПКС Источник="Сумма"       Приёмник="Сумма"/>
      <ПКС Источник="Контрагент"  Приёмник="Контрагент" ВидСвязи="КлючевыеСвойства"/>
      <ПКС Источник="Организация" Приёмник="Организация" ВидСвязи="КлючевыеСвойства"/>
      <ПКС Источник="Склад"       Приёмник="Склад"/>
      <ПКС Источник="Договор"     Приёмник="Договор"/>
      <ПКС Источник="Комментарий" Приёмник="Комментарий">
        <ОбработчикКонвертации>
          // длина source(500) → target(1024) — обрезание не требуется
          Приёмник = Источник;
        </ОбработчикКонвертации>
      </ПКС>
    </Свойства>

    <ТабличныеЧасти>
      <ТЧ Имя="Товары">
        <ПКС Источник="Номенклатура" Приёмник="Номенклатура"/>
        <ПКС Источник="Количество"   Приёмник="Количество"/>
        <ПКС Источник="Цена"         Приёмник="Цена"/>
      </ТЧ>
    </ТабличныеЧасти>
  </ПравилоКонвертацииОбъектов>
</ПравилаОбмена>`}
      </pre>
    </div>
  );
}

function ChatTab() {
  return (
    <div className="k-chat">
      <div className="k-chat-history">
        <div className="k-chat-entry">
          <div className="ts k-mono">14:32 · <span className="ctx">Document.РеализацияТоваровУслуг</span></div>
          <div className="you">Если в источнике Контрагент пустой, не выгружай этот документ</div>
          <div className="ai">
            Добавил обработчик в событие <span className="k-mono">ПередКонвертациейОбъекта</span>:
            <code className="code">{`Если ИсходныйОбъект.Контрагент.Пустая() Тогда
    Отказ = Истина;
    Возврат;
КонецЕсли;`}</code>
            Обработчик сохранён. Объект без контрагента будет пропущен при выгрузке.
            <div className="meta">
              <span className="diff-chip">+1 handler · +4 lines</span>
              <span className="rollback">↶ rollback</span>
              <span className="rollback">view full code</span>
            </div>
          </div>
        </div>

        <div className="k-chat-entry">
          <div className="ts k-mono">13:15 · <span className="ctx">Catalog.Контрагенты</span></div>
          <div className="you">Запусти auto-mapping для этого объекта, по полям из ED Контрагент</div>
          <div className="ai">
            Auto-mapping завершён за 6.2s. 7 mapped, 1 unresolved (поле <span className="k-mono">«ОсобыйСтатус»</span> не имеет аналога в EnterpriseData — рекомендую игнорировать или хранить в свободном поле).
            <div className="meta">
              <span className="diff-chip">+7 mappings</span>
              <span className="rollback">↶ rollback</span>
            </div>
          </div>
        </div>

        <div className="k-chat-entry">
          <div className="ts k-mono">12:48 · <span className="ctx">Document.Реализация</span></div>
          <div className="you">Почему ты предложил мапить Комментарий в Примечание? Они разной длины</div>
          <div className="ai">
            EnterpriseData промежуточный — там длина 0 (unbounded). Mapping safe в обе стороны: source(500) → ED → target(1024). Сжатие данных не происходит. Если хочешь иметь обработчик с явным усечением — могу добавить.
          </div>
        </div>
      </div>

      <div className="k-chat-input">
        <div className="ctxbar">
          <span>контекст: <span style={{ color: 'var(--k-text-2)' }}>Document.РеализацияТоваровУслуг</span></span>
          <span style={{ color: 'var(--k-text-4)' }}>·</span>
          <span>12 mapped · 4 unresolved · 2 errors</span>
        </div>
        <textarea placeholder="Опишите, что должен сделать AI с этим объектом…"/>
        <div className="footer">
          <button className="k-quick"><Icon.Sparkle/>Re-run mapping</button>
          <button className="k-quick">Suggest handlers</button>
          <button className="k-quick">Explain this mapping</button>
          <span className="spacer"/>
          <span style={{ color: 'var(--k-text-3)', fontSize: 11 }}>Enter = send · Shift+Enter = newline</span>
          <button className="k-btn sm primary">Send</button>
        </div>
      </div>
    </div>
  );
}

// --- Status bar (bottom of window) ---
function StatusBar() {
  return (
    <div className="k-statusbar">
      <span className="seg"><span className="label">Source</span> УТ 11.5.18.123</span>
      <span style={{ color: 'var(--k-text-4)' }}>·</span>
      <span className="seg"><span className="label">Target</span> БП 3.0.142.39</span>
      <span style={{ color: 'var(--k-text-4)' }}>·</span>
      <span className="seg"><span className="label">ED</span> v1.8.6</span>
      <span className="spacer"/>
      <span className="seg">Auto-save · 2 мин назад</span>
      <span style={{ color: 'var(--k-text-4)' }}>·</span>
      <span className="seg" style={{ color: 'var(--k-green)' }}>● online</span>
      <span style={{ color: 'var(--k-text-4)' }}>·</span>
      <span className="seg">v0.14.2</span>
    </div>
  );
}

// --- Workspace root component ---
function Workspace({ variant = 'mapping-selected', showBanner = false, showToast = false }) {
  return (
    <div className="k-app" style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', position: 'relative' }}>
      <WorkspaceHeader/>
      {showBanner && (
        <div className="k-banner">
          <Icon.Err style={{ color: 'var(--k-red)' }}/>
          <span>Ошибка подключения к Anthropic API. AI функции временно недоступны.</span>
          <div className="actions">
            <button className="k-btn sm">Retry</button>
            <button className="k-btn sm ghost">Settings</button>
          </div>
        </div>
      )}
      <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        <LeftSidebar/>
        <CenterArea variant={variant}/>
        <Inspector variant={variant}/>
      </div>
      <BottomDock variant={variant}/>
      <StatusBar/>
      {showToast && (
        <div className="k-toast">
          <Icon.Check/>
          <span>Файлы сохранены в <span className="k-mono">~/Konvey/out/</span></span>
          <span className="btn">Open folder</span>
        </div>
      )}
    </div>
  );
}

Object.assign(window, { Workspace });
