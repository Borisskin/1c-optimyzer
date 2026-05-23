// Konvey shared primitives — icons, type pills, status dots, tree rows.

// === Icons (single-stroke 14px / 12px) ===
const Icon = {
  Doc: (p) => (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" {...p}>
      <path d="M3 2.5h5l3 3v6a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1v-8a1 1 0 0 1 1-1Z" stroke="currentColor" strokeWidth="1.1"/>
      <path d="M8 2.5v3h3" stroke="currentColor" strokeWidth="1.1"/>
    </svg>
  ),
  Cat: (p) => (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" {...p}>
      <rect x="2" y="3" width="10" height="8" rx="1" stroke="currentColor" strokeWidth="1.1"/>
      <path d="M2 5.5h10M5 3v8" stroke="currentColor" strokeWidth="1.1"/>
    </svg>
  ),
  Reg: (p) => (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" {...p}>
      <rect x="2" y="3" width="10" height="8" rx="1" stroke="currentColor" strokeWidth="1.1"/>
      <path d="M2 6h10M2 8.5h10" stroke="currentColor" strokeWidth="1.1"/>
    </svg>
  ),
  Enum: (p) => (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" {...p}>
      <path d="m7 2 4.5 5L7 12 2.5 7 7 2Z" stroke="currentColor" strokeWidth="1.1"/>
    </svg>
  ),
  Tbl: (p) => (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" {...p}>
      <rect x="2" y="3" width="10" height="8" rx="1" stroke="currentColor" strokeWidth="1.1"/>
      <path d="M2 6h10M2 9h10M5 3v8M9 3v8" stroke="currentColor" strokeWidth="1.1"/>
    </svg>
  ),
  Triangle: (p) => (
    <svg width="8" height="8" viewBox="0 0 8 8" fill="currentColor" {...p}>
      <path d="M2 1.5 6 4 2 6.5z"/>
    </svg>
  ),
  TriangleDown: (p) => (
    <svg width="8" height="8" viewBox="0 0 8 8" fill="currentColor" {...p}>
      <path d="M1.5 2.5 4 6 6.5 2.5z"/>
    </svg>
  ),
  Search: (p) => (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" {...p}>
      <circle cx="5" cy="5" r="3" stroke="currentColor" strokeWidth="1.1"/>
      <path d="m7.5 7.5 2.5 2.5" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round"/>
    </svg>
  ),
  Filter: (p) => (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" {...p}>
      <path d="M2 2.5h8L7 6.5v3.5L5 9v-2.5L2 2.5Z" stroke="currentColor" strokeWidth="1.1" strokeLinejoin="round"/>
    </svg>
  ),
  Plus: (p) => (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" {...p}>
      <path d="M6 2v8M2 6h8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
    </svg>
  ),
  Menu: (p) => (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" {...p}>
      <path d="M2.5 4h9M2.5 7h9M2.5 10h9" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
    </svg>
  ),
  Kebab: (p) => (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor" {...p}>
      <circle cx="6" cy="2.5" r="1"/><circle cx="6" cy="6" r="1"/><circle cx="6" cy="9.5" r="1"/>
    </svg>
  ),
  Pen: (p) => (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" {...p}>
      <path d="m2 10 1-2 5-5 2 2-5 5-2 1Z" stroke="currentColor" strokeWidth="1.1" strokeLinejoin="round"/>
      <path d="m7 3 2 2" stroke="currentColor" strokeWidth="1.1"/>
    </svg>
  ),
  Check: (p) => (
    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" {...p}>
      <path d="M2 5.5 4 7.5 8 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  X: (p) => (
    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" {...p}>
      <path d="M2 2l6 6M8 2l-6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  ),
  Warn: (p) => (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" {...p}>
      <path d="M6 1.5 11 10.5H1L6 1.5Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/>
      <path d="M6 5v2.5M6 9v.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
    </svg>
  ),
  Info: (p) => (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" {...p}>
      <circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.1"/>
      <path d="M6 5.5v2.5M6 3.5v.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
    </svg>
  ),
  Err: (p) => (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" {...p}>
      <circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.1"/>
      <path d="m4 4 4 4M8 4l-4 4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
    </svg>
  ),
  Sparkle: (p) => (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" {...p}>
      <path d="M6 1 7 5l4 1-4 1-1 4-1-4-4-1 4-1 1-4Z" stroke="currentColor" strokeWidth="1" strokeLinejoin="round"/>
    </svg>
  ),
  Arrow: (p) => (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" {...p}>
      <path d="M2.5 6h7M7 3.5 9.5 6 7 8.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  Grip: (p) => (
    <svg width="8" height="12" viewBox="0 0 8 12" fill="currentColor" {...p}>
      <circle cx="2.5" cy="3" r="0.9"/><circle cx="5.5" cy="3" r="0.9"/>
      <circle cx="2.5" cy="6" r="0.9"/><circle cx="5.5" cy="6" r="0.9"/>
      <circle cx="2.5" cy="9" r="0.9"/><circle cx="5.5" cy="9" r="0.9"/>
    </svg>
  ),
};

// === Type icon glyph (small mono char in field rows) ===
function TypeGlyph({ type }) {
  const ch = { str: 'T', num: '#', date: '◷', bool: '✓', ref: '→', table: '▤', register: '⊞', enum: '◇' }[type] || '·';
  return <span className="k-mono" style={{ fontSize: 11, color: 'var(--k-text-3)' }}>{ch}</span>;
}

// === Object icon by kind ===
function ObjectIcon({ kind, ...rest }) {
  switch (kind) {
    case 'doc': return <Icon.Doc {...rest}/>;
    case 'cat': return <Icon.Cat {...rest}/>;
    case 'reg': return <Icon.Reg {...rest}/>;
    case 'enum': return <Icon.Enum {...rest}/>;
    case 'tbl': return <Icon.Tbl {...rest}/>;
    default: return <Icon.Doc {...rest}/>;
  }
}

// === Status dot (small colored circle for counts) ===
function Dot({ status }) {
  return <span className={`dot ${status}`}/>;
}

// === Field row in a mapping column ===
function FieldRow({ field, side, selected, dim, drop, dragSource, hasMappingL, hasMappingR, mappingStatusL, mappingStatusR }) {
  if (field.kind === 'group') {
    return (
      <div className={`k-group-row k-indent-${field.indent || 0}`}>
        <span className="twist"><Icon.TriangleDown/></span>
        {field.ico === 'table' && <span className="ico"><Icon.Tbl/></span>}
        {field.ico === 'register' && <span className="ico"><Icon.Reg/></span>}
        {field.ico === '📄' && <span className="ico" style={{color:'var(--k-text-2)'}}><Icon.Doc/></span>}
        <span className="name k-mono" style={{ fontSize: field.indent === 0 ? 11.5 : 10.5, textTransform: field.indent === 0 ? 'none' : 'uppercase', color: field.indent === 0 ? 'var(--k-text)' : 'var(--k-text-3)', fontWeight: field.indent === 0 ? 500 : 500 }}>
          {field.label}
        </span>
      </div>
    );
  }
  const cls = [
    'k-field-row', `k-indent-${field.indent || 0}`,
    selected && 'selected',
    dim && 'dim',
    drop === 'ok' && 'drop-ok',
    drop === 'bad' && 'drop-bad',
    dragSource && 'drag-source',
    hasMappingR && 'has-mapping',
    hasMappingL && 'has-mapping-l',
    mappingStatusR === 'amber' && 'mapping-amber',
    mappingStatusL === 'amber' && 'mapping-amber-l',
    mappingStatusR === 'red' && 'mapping-red',
    mappingStatusL === 'red' && 'mapping-red-l',
  ].filter(Boolean).join(' ');
  return (
    <div className={cls} data-fid={field.id}>
      {side === 'ed' ? (
        <>
          <span className="req" style={{ color: field.req ? 'var(--k-amber)' : 'var(--k-text-4)' }}>
            {field.req ? '★' : '−'}
          </span>
          <TypeGlyph type={field.type}/>
          <span className="name">{field.name}</span>
          <span className="colon">:</span>
          <span className="type">{field.dtype}</span>
        </>
      ) : (
        <>
          <TypeGlyph type={field.type}/>
          <span className="name">{field.name}</span>
          <span className="colon">:</span>
          <span className="type">{field.dtype}</span>
          <span className="handle"><Icon.Grip/></span>
        </>
      )}
      {/* Row-edge endpoint dots intentionally omitted — line layer renders dots in SVG. */}
    </div>
  );
}

// === Tree row in left sidebar ===
function TreeRow({ ico, name, mapped, total, status, active }) {
  return (
    <div className={`k-tree-row ${active ? 'active' : ''}`}>
      <span className="ico"><ObjectIcon kind={ico}/></span>
      <span className="name">{name}</span>
      <span className="stat">
        <span style={{
          width: 6, height: 6, borderRadius: '50%',
          background: status === 'green' ? 'var(--k-green)' :
                      status === 'amber' ? 'var(--k-amber)' :
                      status === 'red' ? 'var(--k-red)' : 'var(--k-gray)'
        }}/>
        {mapped}/{total}
      </span>
    </div>
  );
}

// === Mapping line layer — draws SVG bezier curves between two columns ===
function LineLayer({ lines, leftFields, rightFields, leftSide, rightSide, width = 1, leftEdgeOffset = 0, rightEdgeOffset = 0 }) {
  // build lookup
  const lMap = Object.fromEntries(leftFields.filter(f => f.id).map(f => [f.id, f.y]));
  const rMap = Object.fromEntries(rightFields.filter(f => f.id).map(f => [f.id, f.y]));
  return (
    <svg className="k-line-layer" style={{ overflow: 'visible' }}>
      {lines.map((ln, i) => {
        const y1 = lMap[ln.from];
        const y2 = rMap[ln.to];
        if (y1 == null || y2 == null) return null;
        const x1 = leftEdgeOffset;
        const x2 = rightEdgeOffset;
        const cx1 = x1 + (x2 - x1) * 0.5;
        const cx2 = x1 + (x2 - x1) * 0.5;
        const d = `M ${x1} ${y1} C ${cx1} ${y1}, ${cx2} ${y2}, ${x2} ${y2}`;
        const status = ln.status || 'green';
        const dim = ln.dim;
        const selected = ln.selected;
        return (
          <g key={i}>
            <path d={d} className={`${status} ${selected ? 'selected' : ''} ${dim ? 'dim' : ''}`}/>
          </g>
        );
      })}
    </svg>
  );
}

Object.assign(window, { Icon, TypeGlyph, ObjectIcon, Dot, FieldRow, TreeRow, LineLayer });
