/* Shared library — icons, charts, chrome */
const { useState, useEffect, useRef, useMemo, useCallback, createContext, useContext } = React;

/* -------------------- ICONS (Lucide-ish, 16px default) -------------------- */
const ic = (d, vb = '0 0 24 24') => (props) => (
  <svg viewBox={vb} width={props.size || 16} height={props.size || 16}
    fill="none" stroke="currentColor" strokeWidth={props.sw || 1.6}
    strokeLinecap="round" strokeLinejoin="round" className={props.className || ''} aria-hidden="true">
    {d}
  </svg>
);

const I = {
  Activity: ic(<><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></>),
  Gauge: ic(<><path d="M12 14l4-4"/><path d="M3.5 12a8.5 8.5 0 1 1 17 0"/></>),
  Search: ic(<><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></>),
  Bell: ic(<><path d="M6 8a6 6 0 0 1 12 0c0 7 3 8 3 8H3s3-1 3-8"/><path d="M10 21a2 2 0 0 0 4 0"/></>),
  Sparkles: ic(<><path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5L12 3z"/><path d="M19 14l.8 2.2L22 17l-2.2.8L19 20l-.8-2.2L16 17l2.2-.8L19 14z"/></>),
  ChevronDown: ic(<><polyline points="6 9 12 15 18 9"/></>),
  ChevronRight: ic(<><polyline points="9 18 15 12 9 6"/></>),
  ChevronLeft: ic(<><polyline points="15 18 9 12 15 6"/></>),
  Cluster: ic(<><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></>),
  Database: ic(<><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v6c0 1.7 4 3 9 3s9-1.3 9-3V5"/><path d="M3 11v6c0 1.7 4 3 9 3s9-1.3 9-3v-6"/></>),
  Lock: ic(<><rect x="4" y="11" width="16" height="10" rx="1.5"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></>),
  Code: ic(<><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></>),
  FlaskList: ic(<><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/></>),
  Scan: ic(<><path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><line x1="7" y1="12" x2="17" y2="12"/></>),
  Brain: ic(<><path d="M9 4.5A2.5 2.5 0 0 1 11.5 7v10a2.5 2.5 0 0 1-5 0 2.5 2.5 0 0 1-2-4 2.5 2.5 0 0 1 1-4.5A2.5 2.5 0 0 1 9 4.5z"/><path d="M15 4.5A2.5 2.5 0 0 0 12.5 7v10a2.5 2.5 0 0 0 5 0 2.5 2.5 0 0 0 2-4 2.5 2.5 0 0 0-1-4.5A2.5 2.5 0 0 0 15 4.5z"/></>),
  Workflow: ic(<><rect x="3" y="3" width="6" height="6" rx="1"/><rect x="15" y="3" width="6" height="6" rx="1"/><rect x="9" y="15" width="6" height="6" rx="1"/><path d="M6 9v2a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V9"/></>),
  Layers: ic(<><polygon points="12 2 22 8 12 14 2 8 12 2"/><polyline points="2 14 12 20 22 14"/></>),
  Terminal: ic(<><polyline points="4 7 9 12 4 17"/><line x1="12" y1="19" x2="20" y2="19"/></>),
  Book: ic(<><path d="M4 4a2 2 0 0 1 2-2h14v18H6a2 2 0 0 0-2 2z"/><path d="M6 16h14"/></>),
  AlertTriangle: ic(<><path d="M10.3 3.7 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.7a2 2 0 0 0-3.4 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12" y2="17"/></>),
  AlertOctagon: ic(<><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12" y2="16"/></>),
  Info: ic(<><circle cx="12" cy="12" r="9"/><line x1="12" y1="11" x2="12" y2="16"/><line x1="12" y1="8" x2="12" y2="8"/></>),
  Check: ic(<><polyline points="20 6 9 17 4 12"/></>),
  X: ic(<><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></>),
  FileText: ic(<><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="16" y2="17"/></>),
  Settings: ic(<><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3h.1a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9v.1a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></>),
  Refresh: ic(<><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.5 9A9 9 0 0 1 18.4 5.6L23 10"/><path d="M20.5 15a9 9 0 0 1-14.9 3.4L1 14"/></>),
  Play: ic(<><polygon points="5 3 19 12 5 21 5 3"/></>),
  Pause: ic(<><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></>),
  Plus: ic(<><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></>),
  Bookmark: ic(<><path d="M19 21l-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></>),
  Trend: ic(<><polyline points="3 17 9 11 13 15 21 7"/><polyline points="14 7 21 7 21 14"/></>),
  Eye: ic(<><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></>),
  Filter: ic(<><polygon points="22 3 2 3 10 12.5 10 19 14 21 14 12.5 22 3"/></>),
  Download: ic(<><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></>),
  Share: ic(<><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.6" y1="13.5" x2="15.4" y2="17.5"/><line x1="15.4" y1="6.5" x2="8.6" y2="10.5"/></>),
  Mail: ic(<><rect x="2" y="4" width="20" height="16" rx="2"/><polyline points="2 6 12 13 22 6"/></>),
  ArrowRight: ic(<><line x1="4" y1="12" x2="20" y2="12"/><polyline points="14 6 20 12 14 18"/></>),
  Circle: ic(<><circle cx="12" cy="12" r="9"/></>),
  Dot: ic(<><circle cx="12" cy="12" r="3"/></>),
  Maximize: ic(<><polyline points="3 9 3 3 9 3"/><polyline points="21 9 21 3 15 3"/><polyline points="3 15 3 21 9 21"/><polyline points="21 15 21 21 15 21"/></>),
  Cpu: ic(<><rect x="5" y="5" width="14" height="14" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="2" x2="9" y2="5"/><line x1="15" y1="2" x2="15" y2="5"/><line x1="9" y1="19" x2="9" y2="22"/><line x1="15" y1="19" x2="15" y2="22"/><line x1="2" y1="9" x2="5" y2="9"/><line x1="2" y1="15" x2="5" y2="15"/><line x1="19" y1="9" x2="22" y2="9"/><line x1="19" y1="15" x2="22" y2="15"/></>),
  HardDrive: ic(<><line x1="22" y1="12" x2="2" y2="12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/><line x1="6" y1="16" x2="6" y2="16"/><line x1="10" y1="16" x2="10" y2="16"/></>),
  Memory: ic(<><rect x="2" y="7" width="20" height="10" rx="1.5"/><line x1="7" y1="7" x2="7" y2="17"/><line x1="12" y1="7" x2="12" y2="17"/><line x1="17" y1="7" x2="17" y2="17"/></>),
  Network: ic(<><circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3a14 14 0 0 1 0 18"/><path d="M12 3a14 14 0 0 0 0 18"/></>),
  Server: ic(<><rect x="3" y="4" width="18" height="6" rx="1"/><rect x="3" y="14" width="18" height="6" rx="1"/><circle cx="7" cy="7" r="0.7"/><circle cx="7" cy="17" r="0.7"/></>),
  User: ic(<><circle cx="12" cy="8" r="4"/><path d="M4 20a8 8 0 0 1 16 0"/></>),
  Inbox: ic(<><polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></>),
  Phone: ic(<><rect x="6" y="2" width="12" height="20" rx="2"/><line x1="11" y1="18" x2="13" y2="18"/></>),
  GitCompare: ic(<><circle cx="5" cy="6" r="2"/><circle cx="19" cy="18" r="2"/><path d="M7 6h6a4 4 0 0 1 4 4v6"/><path d="M17 18H11a4 4 0 0 1-4-4V8"/></>),
  Bolt: ic(<><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></>),
  Globe: ic(<><circle cx="12" cy="12" r="9"/><line x1="3" y1="12" x2="21" y2="12"/><path d="M12 3a14 14 0 0 1 0 18"/><path d="M12 3a14 14 0 0 0 0 18"/></>),
};

/* -------------------- Status pieces -------------------- */
const Sev = ({ level, size=12 }) => {
  const map = {
    ok:   { fg:'#16A34A', bg:'#F0FDF4' },
    warn: { fg:'#D97706', bg:'#FFFBEB' },
    err:  { fg:'#DC2626', bg:'#FEF2F2' },
    info: { fg:'#2563EB', bg:'#EFF6FF' },
    mute: { fg:'#737373', bg:'#F5F5F5' },
  };
  const c = map[level] || map.mute;
  return <span className="inline-block rounded-full" style={{ width:size, height:size, background:c.fg }} />;
};

const Badge = ({ tone='mute', children, mono=false, className='' }) => {
  const tones = {
    ok:   'bg-ok-bg text-ok border-ok/20',
    warn: 'bg-warn-bg text-warn border-warn/20',
    err:  'bg-err-bg text-err border-err/20',
    info: 'bg-info-bg text-info border-info/20',
    teal: 'bg-teal-50 text-teal-700 border-teal-700/15',
    mute: 'bg-ink-50 text-ink-600 border-ink-150',
    ink:  'bg-ink-900 text-white border-ink-900',
  };
  return <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 text-2xs leading-none border rounded-[3px] ${tones[tone]} ${mono?'mono':''} ${className}`}>{children}</span>;
};

const KBD = ({ children }) => <kbd>{children}</kbd>;

/* -------------------- Sparkline / Bars / Gauge -------------------- */
function Spark({ data, w=120, h=28, color='#0F766E', area=true, strokeW=1.4 }) {
  const min = Math.min(...data), max = Math.max(...data);
  const range = (max - min) || 1;
  const pts = data.map((v,i) => {
    const x = (i/(data.length-1)) * (w-2) + 1;
    const y = h - 2 - ((v - min)/range) * (h-4);
    return [x, y];
  });
  const path = pts.map((p,i)=> (i?'L':'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
  const areaPath = path + ` L${(w-1).toFixed(1)} ${h-1} L1 ${h-1} Z`;
  return (
    <svg width={w} height={h} className="block">
      {area && <path d={areaPath} fill={color} opacity={0.08}/>}
      <path d={path} fill="none" stroke={color} strokeWidth={strokeW}/>
    </svg>
  );
}

function MiniBars({ data, w=120, h=28, color='#0F766E' }) {
  const max = Math.max(...data) || 1;
  const bw = (w - (data.length-1)*1) / data.length;
  return (
    <svg width={w} height={h} className="block">
      {data.map((v,i)=>{
        const bh = (v/max) * (h-2);
        return <rect key={i} x={i*(bw+1)} y={h-bh} width={bw} height={bh} fill={color} opacity={0.85}/>;
      })}
    </svg>
  );
}

function Donut({ pct=75, size=44, stroke=5, color='#0F766E', track='#EDEDED' }) {
  const r = (size-stroke)/2;
  const c = 2*Math.PI*r;
  return (
    <svg width={size} height={size}>
      <circle cx={size/2} cy={size/2} r={r} stroke={track} strokeWidth={stroke} fill="none"/>
      <circle cx={size/2} cy={size/2} r={r} stroke={color} strokeWidth={stroke} fill="none"
        strokeDasharray={`${(pct/100)*c} ${c}`} strokeDashoffset={c*0.25} strokeLinecap="round"
        transform={`rotate(-90 ${size/2} ${size/2})`}/>
    </svg>
  );
}

/* Line chart with axis */
function LineChart({ series, w=600, h=180, yLabel, color='#0F766E', baseline, target }) {
  // series: array of {data:[{t,v}], name, color}
  const all = series.flatMap(s => s.data.map(d=>d.v));
  const min = Math.min(...all, baseline ?? Infinity, target ?? Infinity);
  const max = Math.max(...all, baseline ?? -Infinity, target ?? -Infinity);
  const range = (max-min) || 1;
  const px = 38, py = 14, pb = 20;
  const W = w - px - 8, H = h - py - pb;
  const xAt = (i, n) => px + (i/(n-1)) * W;
  const yAt = v => py + H - ((v-min)/range) * H;
  // gridlines
  const grid = [0, .25, .5, .75, 1].map(t => min + t*range);
  return (
    <svg width={w} height={h}>
      {grid.map((g,i)=>(
        <g key={i}>
          <line x1={px} x2={px+W} y1={yAt(g)} y2={yAt(g)} stroke="#F0F0F0"/>
          <text x={px-6} y={yAt(g)+3} fontSize="10" textAnchor="end" fill="#A3A3A3" className="mono">{g.toFixed(2)}</text>
        </g>
      ))}
      {target != null && <line x1={px} x2={px+W} y1={yAt(target)} y2={yAt(target)} stroke="#16A34A" strokeDasharray="3 3" strokeWidth="1"/>}
      {baseline != null && <line x1={px} x2={px+W} y1={yAt(baseline)} y2={yAt(baseline)} stroke="#A3A3A3" strokeDasharray="2 4" strokeWidth="1"/>}
      {series.map((s, si) => {
        const path = s.data.map((d,i)=> (i?'L':'M') + xAt(i, s.data.length).toFixed(1) + ' ' + yAt(d.v).toFixed(1)).join(' ');
        return <g key={si}>
          <path d={path} fill="none" stroke={s.color || color} strokeWidth="1.5"/>
        </g>
      })}
      <text x={px} y={h-4} fontSize="10" fill="#A3A3A3" className="mono">00:00</text>
      <text x={px+W} y={h-4} fontSize="10" fill="#A3A3A3" textAnchor="end" className="mono">now</text>
      {yLabel && <text x={6} y={py+2} fontSize="10" fill="#A3A3A3" className="mono">{yLabel}</text>}
    </svg>
  );
}

/* Heatmap: weeks x hours */
function Heatmap({ data, scale=[0,0.5,1], w=720, h=160, palette=['#16A34A','#D97706','#DC2626'] }) {
  // data: 7 rows x 24 cols, value 0..1 (red=high)
  const days = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];
  const cw = (w-32)/24, ch = (h-18)/7;
  const col = v => {
    if (v < 0.33) return '#F0FDF4';
    if (v < 0.55) return '#DCFCE7';
    if (v < 0.7) return '#FEF3C7';
    if (v < 0.85) return '#FECACA';
    return '#FCA5A5';
  };
  return (
    <svg width={w} height={h}>
      {days.map((d,i)=>(<text key={d} x={4} y={18+i*ch+ch/2+4} fontSize="10" fill="#737373" className="mono">{d}</text>))}
      {Array.from({length:24}).map((_,h2)=>(
        h2 % 3 === 0 && <text key={h2} x={32+h2*cw+2} y={12} fontSize="10" fill="#A3A3A3" className="mono">{String(h2).padStart(2,'0')}</text>
      ))}
      {data.map((row, ri)=>row.map((v, ci)=>(
        <rect key={`${ri}-${ci}`} x={32+ci*cw+1} y={18+ri*ch+1} width={cw-2} height={ch-2} fill={col(v)}/>
      )))}
    </svg>
  );
}

/* -------------------- App chrome -------------------- */
const NAV = [
  { id:'dashboard',  label:'Operations',         icon:I.Gauge,        group:'live' },
  { id:'apdex',      label:'Apdex & SLA',        icon:I.Trend,        group:'live' },
  { id:'workbench',  label:'Investigation',      icon:I.Layers,       group:'live' },
  { id:'queries',    label:'Slow Queries',       icon:I.Database,     group:'analyze' },
  { id:'locks',      label:'Locks & Deadlocks',  icon:I.Lock,         group:'analyze' },
  { id:'cluster',    label:'Cluster Health',     icon:I.Cluster,      group:'analyze' },
  { id:'indexes',    label:'Indexes & Stats',    icon:I.HardDrive,    group:'analyze' },
  { id:'profiler',   label:'BSL Profiler',       icon:I.Code,         group:'analyze' },
  { id:'health',     label:'Health Scan',        icon:I.Scan,         group:'config' },
  { id:'compare',    label:'Compare',            icon:I.GitCompare,   group:'config' },
  { id:'predictive', label:'Predictive',         icon:I.Brain,        group:'config' },
  { id:'resolution', label:'Resolution',         icon:I.Workflow,     group:'manage' },
  { id:'multibase',  label:'Multi-base',         icon:I.Globe,        group:'manage' },
  { id:'oql',        label:'OptimyzerQL',        icon:I.Terminal,     group:'manage' },
  { id:'knowledge',  label:'Knowledge Base',     icon:I.Book,         group:'manage' },
  { id:'alerts',     label:'Alerts',             icon:I.Bell,         group:'manage' },
  { id:'reports',    label:'Reports',            icon:I.FileText,     group:'manage' },
  { id:'mobile',     label:'Mobile Companion',   icon:I.Phone,        group:'manage' },
];

function TopBar({ env, setEnv, openCmd, openAI, alertsCount, healthLevel='warn' }) {
  return (
    <div className="row-start-1 col-span-2 flex items-center px-3 border-b hl bg-white relative z-30">
      <div className="flex items-center gap-2 pr-3 mr-2 border-r hl2 h-full">
        <div className="w-6 h-6 rounded-[5px] bg-ink-900 text-white grid place-items-center mono text-[10px] font-bold tracking-tight">1C</div>
        <div className="leading-tight">
          <div className="text-[13px] font-semibold">1C-Optimyzer</div>
          <div className="text-[10px] text-ink-500 mono -mt-0.5">v2.7.118 · prod</div>
        </div>
      </div>

      <button className="flex items-center gap-1.5 text-[12px] px-2 h-7 rounded border hl2 hover:bg-ink-50">
        <I.Database size={13} className="text-ink-500" />
        <span className="font-medium">{env}</span>
        <I.ChevronDown size={12} className="text-ink-400" />
      </button>
      <div className="text-[11px] text-ink-400 mono px-2">8.3.25.1394 · MS SQL 2022</div>

      <button onClick={openCmd} className="ml-4 flex items-center gap-2 h-7 px-2 rounded border hl2 bg-ink-25 hover:bg-white text-[12px] w-[440px] max-w-[40vw]">
        <I.Search size={13} className="text-ink-400" />
        <span className="text-ink-400">Search anything — pages, alerts, queries, sessions, code…</span>
        <span className="ml-auto"><KBD>Ctrl</KBD> <KBD>K</KBD></span>
      </button>

      <div className="ml-auto flex items-center gap-1.5">
        <div className="flex items-center gap-2 px-2 h-7 rounded border hl2">
          <span className={`w-2 h-2 rounded-full ${healthLevel==='ok'?'bg-ok led':healthLevel==='warn'?'bg-warn led-w':'bg-err led-e'} pulse`} />
          <span className="text-[11px] mono">{alertsCount} active</span>
        </div>
        <button className="h-7 w-7 grid place-items-center rounded hover:bg-ink-50 relative">
          <I.Bell size={15}/>
          <span className="absolute -top-0.5 -right-0.5 text-[9px] mono bg-err text-white rounded-full px-1 leading-[14px]">7</span>
        </button>
        <button onClick={openAI} className="h-7 px-2 flex items-center gap-1 rounded border hl2 hover:bg-teal-50 text-teal-700">
          <I.Sparkles size={13}/>
          <span className="text-[11px] font-medium">AI</span>
        </button>
        <div className="div-v h-5 mx-1"></div>
        <button className="h-7 px-2 flex items-center gap-1.5 rounded hover:bg-ink-50">
          <div className="w-5 h-5 rounded-full bg-teal-700 text-white text-[10px] grid place-items-center font-semibold">ИС</div>
          <span className="text-[11px]">Иванов И.С.</span>
          <I.ChevronDown size={12} className="text-ink-400"/>
        </button>
      </div>
    </div>
  );
}

function Sidebar({ active, setActive, open, setOpen }) {
  const groups = [
    { name:'LIVE',    keys:['dashboard','apdex','workbench'] },
    { name:'ANALYZE', keys:['queries','locks','cluster','indexes','profiler'] },
    { name:'CONFIG',  keys:['health','compare','predictive'] },
    { name:'MANAGE',  keys:['resolution','multibase','oql','knowledge','alerts','reports','mobile'] },
  ];
  const byKey = Object.fromEntries(NAV.map(n=>[n.id, n]));
  return (
    <aside className="row-start-2 col-start-1 border-r hl bg-white flex flex-col">
      <div className="flex-1 overflow-y-auto py-1.5">
        {groups.map(g => (
          <div key={g.name} className="mb-1">
            {open && <div className="px-3 pt-2 pb-1 text-[10px] tracking-[0.1em] text-ink-400 mono font-medium">{g.name}</div>}
            {!open && <div className="mx-3 my-1 div-h"></div>}
            {g.keys.map(k => {
              const n = byKey[k]; if (!n) return null;
              const Icon = n.icon;
              const isActive = active === k;
              return (
                <button key={k}
                  onClick={()=>setActive(k)}
                  className={`group relative flex items-center gap-2.5 w-full ${open?'px-3':'justify-center px-0'} h-8 text-[12.5px] ${isActive?'bg-teal-50 text-teal-700':'text-ink-700 hover:bg-ink-50'}`}>
                  {isActive && <span className="absolute left-0 top-0 bottom-0 w-[2px] bg-teal-700"></span>}
                  <Icon size={15} className={isActive?'text-teal-700':'text-ink-500'}/>
                  {open && <span className="font-medium">{n.label}</span>}
                  {!open && <span className="pointer-events-none absolute left-full ml-2 px-1.5 py-0.5 text-[11px] bg-ink-900 text-white rounded opacity-0 group-hover:opacity-100 transition whitespace-nowrap z-50">{n.label}</span>}
                </button>
              );
            })}
          </div>
        ))}
      </div>
      <div className="border-t hl p-1">
        <button onClick={()=>setOpen(!open)} className={`flex items-center gap-2 ${open?'px-3':'justify-center'} h-7 w-full text-[11px] text-ink-500 hover:bg-ink-50 rounded`}>
          {open ? <><I.ChevronLeft size={13}/>Collapse</> : <I.ChevronRight size={13}/>}
        </button>
      </div>
    </aside>
  );
}

function StatusBar({ env }) {
  return (
    <div className="row-start-3 col-span-2 flex items-center px-3 text-[11px] text-ink-500 mono border-t hl bg-white relative z-20">
      <div className="flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-ok"></span>
        <span>connected · {env}</span>
      </div>
      <div className="mx-3 div-v h-3"></div>
      <span>agents 12/12 online</span>
      <div className="mx-3 div-v h-3"></div>
      <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-teal-600 pulse"></span>events 12,847/s</span>

      <div className="ml-auto flex items-center gap-3">
        <span>last sync 2s ago</span>
        <div className="div-v h-3"></div>
        <span>ingest 23.4 MB/s</span>
        <div className="div-v h-3"></div>
        <span>session 02:14:08</span>
        <div className="div-v h-3"></div>
        <span>v2.7.118-stable</span>
      </div>
    </div>
  );
}

/* -------------------- Command Palette -------------------- */
function CommandPalette({ open, onClose, onNav }) {
  const [q, setQ] = useState('');
  useEffect(()=>{ if (open) setQ(''); }, [open]);
  const items = useMemo(()=> ([
    ...NAV.map(n => ({ kind:'page', label:n.label, hint:'Page', id:n.id, icon:n.icon })),
    { kind:'cmd', label:'Restart rphost #3', hint:'Cluster · destructive', icon:I.Server },
    { kind:'cmd', label:'Run new Health Scan',  hint:'Configuration', icon:I.Scan },
    { kind:'q',   label:'Active sessions > 30s', hint:'Saved query',   icon:I.Terminal },
    { kind:'q',   label:'Deadlocks last 24h',    hint:'Saved query',   icon:I.Terminal },
    { kind:'alert', label:'Pattern #1247 — Реализация↔КорректировкаДолга', hint:'Alert · Critical', icon:I.AlertOctagon },
    { kind:'alert', label:'Memory leak in rphost #3',                       hint:'Alert · Critical', icon:I.AlertTriangle },
    { kind:'ai',  label:'Покажи запросы дольше 1с из РасчётыСКонтрагентамиСервер', hint:'AI command', icon:I.Sparkles },
    { kind:'ai',  label:'Объясни причину последнего падения Apdex',          hint:'AI command', icon:I.Sparkles },
  ]), []);
  const filtered = items.filter(i => i.label.toLowerCase().includes(q.toLowerCase()));
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 bg-ink-900/20 backdrop-blur-[2px] flex items-start justify-center pt-[12vh]" onMouseDown={onClose}>
      <div className="w-[620px] bg-white rounded-lg shadow-pop border hl2 overflow-hidden" onMouseDown={e=>e.stopPropagation()}>
        <div className="flex items-center px-3 h-11 border-b hl">
          <I.Search size={15} className="text-ink-400"/>
          <input autoFocus value={q} onChange={e=>setQ(e.target.value)} placeholder="Type a command, page, query, alert…" className="flex-1 ml-2 bg-transparent outline-none text-[14px] placeholder:text-ink-400"/>
          <span className="text-[10px] text-ink-400 mono">ESC to close</span>
        </div>
        <div className="max-h-[420px] overflow-y-auto py-1">
          {filtered.length === 0 && <div className="px-4 py-6 text-[12px] text-ink-400 text-center">No results</div>}
          {filtered.slice(0,30).map((it,i)=>{
            const Icon = it.icon;
            return (
              <div key={i} className="flex items-center gap-2.5 px-3 h-8 hover:bg-teal-50 cursor-pointer"
                onClick={()=>{ if (it.kind==='page' && it.id) onNav(it.id); onClose(); }}>
                <Icon size={14} className="text-ink-500"/>
                <span className="text-[13px]">{it.label}</span>
                <span className="ml-auto text-[10.5px] text-ink-400 mono">{it.hint}</span>
              </div>
            );
          })}
        </div>
        <div className="border-t hl px-3 h-8 flex items-center gap-3 text-[10.5px] text-ink-400 mono bg-ink-25">
          <span><KBD>↑</KBD><KBD>↓</KBD> navigate</span>
          <span><KBD>↵</KBD> open</span>
          <span><KBD>Tab</KBD> autocomplete</span>
        </div>
      </div>
    </div>
  );
}

/* -------------------- AI Chat Drawer -------------------- */
function AIChat({ open, onClose }) {
  if (!open) return null;
  const turns = [
    { who:'user', text:'Почему за последний час упал Apdex по операции "Закрытие месяца"?' },
    { who:'ai', text:'Apdex для "Закрытие месяца" упал с 0.71 до 0.42 в 14:12. Корреляция с релизом 11.5.18.235 (deploy 12:48). Изменена `РассчитатьСебестоимость()` — добавлено чтение `НастройкиПартионногоУчёта` в цикле по строкам ТЧ. Это даёт +1000 SQL-запросов на одно проведение. См. **Comparison → 11.5.18.230 vs 11.5.18.235**.', actions:[
      'Открыть diff релиза',
      'Сгенерировать fix как CFE',
      'Добавить в Watched',
    ]},
    { who:'user', text:'Сколько раз сработал deadlock #1247 за неделю?' },
    { who:'ai', text:'312 раз за последние 7 дней (peak: понедельник 09:00–12:00, 41 inc/h). Confidence: high. Root cause неизменен — разный порядок изменения регистров в `Реализация` и `КорректировкаДолга`.' },
  ];
  return (
    <div className="fixed inset-0 z-40" onMouseDown={onClose}>
      <div className="absolute inset-0 bg-ink-900/10"></div>
      <aside onMouseDown={e=>e.stopPropagation()} className="absolute top-0 right-0 h-full w-[420px] bg-white border-l hl2 shadow-pop flex flex-col slide-in">
        <div className="h-11 px-3 flex items-center border-b hl">
          <I.Sparkles size={15} className="text-teal-700"/>
          <span className="ml-2 text-[13px] font-semibold">Optimyzer AI</span>
          <span className="ml-2 text-[10.5px] text-ink-400 mono">claude-haiku-4.5 · grounded</span>
          <button onClick={onClose} className="ml-auto h-7 w-7 grid place-items-center hover:bg-ink-50 rounded"><I.X size={14}/></button>
        </div>
        <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
          {turns.map((t,i)=>(
            <div key={i} className={`text-[12.5px] leading-relaxed ${t.who==='user'?'':'bg-teal-50/40 border hl rounded-md p-2.5'}`}>
              {t.who==='user' ? (
                <div className="flex items-start gap-2">
                  <div className="w-5 h-5 rounded-full bg-ink-900 text-white text-[10px] grid place-items-center mt-0.5">И</div>
                  <div className="text-ink-700">{t.text}</div>
                </div>
              ) : (
                <>
                  <div className="flex items-center gap-1.5 mb-1 text-teal-800 text-[11px] font-semibold mono">
                    <I.Sparkles size={11}/> AI
                  </div>
                  <div className="text-ink-700" dangerouslySetInnerHTML={{__html: t.text.replace(/`([^`]+)`/g,'<span class="mono text-ink-900 bg-white border hl px-1 rounded">$1</span>').replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>')}}></div>
                  {t.actions && <div className="mt-2 flex flex-wrap gap-1.5">
                    {t.actions.map(a=>(<button key={a} className="text-[11px] px-2 h-6 rounded border hl2 bg-white hover:bg-teal-50 text-teal-700">{a}</button>))}
                  </div>}
                </>
              )}
            </div>
          ))}
        </div>
        <div className="border-t hl p-2">
          <div className="flex flex-wrap gap-1.5 mb-2">
            {['Top 5 longest queries today','Why is rphost #3 growing?','Generate fix for #1247'].map(s=>(
              <button key={s} className="text-[11px] px-2 h-6 rounded-full border hl2 text-ink-600 hover:bg-ink-50">{s}</button>
            ))}
          </div>
          <div className="flex items-center gap-2 border hl2 rounded-md px-2 py-1.5">
            <I.Sparkles size={13} className="text-teal-700"/>
            <input placeholder="Спросите про любую метрику, запрос, дедлок…" className="flex-1 bg-transparent outline-none text-[12.5px] placeholder:text-ink-400"/>
            <button className="text-[11px] mono text-ink-500"><KBD>↵</KBD></button>
          </div>
          <div className="mt-1.5 text-[10px] text-ink-400 mono">Grounded on live telemetry from 12 agents · последние 24h в контексте</div>
        </div>
      </aside>
    </div>
  );
}

/* -------------------- Generic panel + helpers -------------------- */
function Panel({ title, sub, right, children, className='', pad=true, dense=false }) {
  return (
    <section className={`bg-white border hl2 rounded-md shadow-panel ${className}`}>
      {(title || right) && (
        <header className={`flex items-center gap-2 ${dense?'h-8 px-2.5':'h-10 px-3'} border-b hl`}>
          {title && <h3 className="text-[12.5px] font-semibold tracking-tight">{title}</h3>}
          {sub && <span className="text-[11px] text-ink-400 mono">{sub}</span>}
          <div className="ml-auto flex items-center gap-1.5">{right}</div>
        </header>
      )}
      <div className={pad? (dense?'p-2.5':'p-3') : ''}>{children}</div>
    </section>
  );
}

function PageHeader({ title, sub, right, breadcrumbs, kpis }) {
  return (
    <div className="px-4 pt-3.5 pb-3 border-b hl bg-white">
      {breadcrumbs && <div className="flex items-center gap-1 text-[11px] text-ink-400 mono mb-1">
        {breadcrumbs.map((b,i)=>(<React.Fragment key={i}>{i>0 && <I.ChevronRight size={11}/>}<span>{b}</span></React.Fragment>))}
      </div>}
      <div className="flex items-end gap-3">
        <h1 className="text-[20px] font-semibold tracking-tight">{title}</h1>
        {sub && <p className="text-[12px] text-ink-500 mb-0.5">{sub}</p>}
        <div className="ml-auto flex items-center gap-2">{right}</div>
      </div>
      {kpis && <div className="mt-3 flex items-end gap-7">{kpis}</div>}
    </div>
  );
}

function KPI({ label, value, sub, tone='ink', mono=true }) {
  const toneCls = tone==='ok'?'text-ok':tone==='warn'?'text-warn':tone==='err'?'text-err':tone==='teal'?'text-teal-700':'text-ink-900';
  return (
    <div className="leading-tight">
      <div className="text-[10.5px] text-ink-400 mono uppercase tracking-wider">{label}</div>
      <div className={`display text-[22px] font-semibold ${toneCls} ${mono?'tnum':''}`}>{value}</div>
      {sub && <div className="text-[11px] text-ink-500 mt-0.5">{sub}</div>}
    </div>
  );
}

function Tabs({ tabs, value, onChange, dense=false }) {
  return (
    <div className={`flex items-center gap-0 border-b hl ${dense?'h-8':'h-9'}`}>
      {tabs.map(t => {
        const active = t.id === value;
        return (
          <button key={t.id} onClick={()=>onChange(t.id)}
            className={`px-3 h-full text-[12px] flex items-center gap-1.5 -mb-px border-b-2 ${active? 'border-teal-700 text-ink-900 font-semibold':'border-transparent text-ink-500 hover:text-ink-900'}`}>
            {t.icon && <t.icon size={12}/>}
            {t.label}
            {t.count != null && <span className={`ml-1 text-[10px] mono px-1 rounded ${active?'bg-teal-50 text-teal-700':'bg-ink-50 text-ink-500'}`}>{t.count}</span>}
          </button>
        );
      })}
    </div>
  );
}

function SegBtn({ children, active, onClick }) {
  return (
    <button onClick={onClick} className={`px-2 h-7 text-[11px] mono border hl2 ${active?'bg-ink-900 text-white border-ink-900':'bg-white text-ink-600 hover:bg-ink-50'}`}>{children}</button>
  );
}
function SegGroup({ children }) { return <div className="inline-flex [&>button]:first:rounded-l [&>button]:last:rounded-r [&>button:not(:first-child)]:-ml-px">{children}</div>; }

function CodeBlock({ children, lang='sql', className='' }) {
  return (
    <pre className={`mono text-[12px] leading-[1.55] codebox p-2.5 overflow-x-auto whitespace-pre ${className}`}>
      {children}
    </pre>
  );
}

/* SQL syntax highlighter — very small */
function hlSQL(s) {
  // returns array of {t,c}
  const kw = /\b(SELECT|FROM|WHERE|AND|OR|GROUP BY|ORDER BY|JOIN|INNER|LEFT|RIGHT|ON|AS|SUM|COUNT|MAX|MIN|CASE|WHEN|THEN|ELSE|END|TOP|LIMIT|HAVING|UNION|ALL|IN|EXISTS|NOT|IS|NULL|DISTINCT|WITH|INDEX|CREATE|INCLUDE|UPDATE|STATISTICS)\b/g;
  const ru = /\b(ВЫБРАТЬ|ИЗ|ГДЕ|И|ИЛИ|СГРУППИРОВАТЬ ПО|УПОРЯДОЧИТЬ ПО|СОЕДИНЕНИЕ|ВНУТРЕННЕЕ|ЛЕВОЕ|ПРАВОЕ|ПО|КАК|СУММА|КОЛИЧЕСТВО|МАКСИМУМ|МИНИМУМ|ВЫБОР|КОГДА|ТОГДА|ИНАЧЕ|КОНЕЦ|ИМЕЮЩИЕ|ОБЪЕДИНИТЬ|ВСЕ|В|НЕ|ЕСТЬ|NULL|РАЗЛИЧНЫЕ|РегистрНакопления|Документ|Справочник|Регистр|В ИЕРАРХИИ|ИЕРАРХИИ)\b/g;
  let parts = [{t:s, c:null}];
  const apply = (regex, color) => {
    const out = [];
    for (const p of parts) {
      if (p.c) { out.push(p); continue; }
      let last = 0; let m;
      regex.lastIndex = 0;
      while ((m = regex.exec(p.t))) {
        if (m.index > last) out.push({t: p.t.slice(last, m.index), c:null});
        out.push({t: m[0], c: color});
        last = m.index + m[0].length;
      }
      if (last < p.t.length) out.push({t: p.t.slice(last), c:null});
    }
    parts = out;
  };
  apply(kw, '#0F766E');
  apply(ru, '#0F766E');
  // numbers
  apply(/\b\d+(\.\d+)?\b/g, '#D97706');
  // strings (single & double)
  apply(/'[^']*'/g, '#16A34A');
  // comments
  apply(/--.*$/gm, '#737373');
  // table aliases t1.something
  apply(/\b(T\d+|t\d+)\.(_?[A-Za-z0-9_]+)/g, '#2563EB');
  // 1C-style _Fld, _Period
  apply(/_[A-Z][A-Za-z0-9_]+/g, '#7C3AED');
  return parts.map((p,i)=> p.c ? <span key={i} style={{color:p.c}}>{p.t}</span> : <span key={i}>{p.t}</span>);
}

function SQLBlock({ children, className='' }) {
  return <pre className={`mono text-[12px] leading-[1.55] codebox p-2.5 overflow-x-auto whitespace-pre ${className}`}>{hlSQL(children)}</pre>;
}

function BSLBlock({ children, className='' }) {
  // simple BSL highlighter: keywords, strings, comments
  const tokens = String(children).split(/(\n)/);
  const kws = /\b(Процедура|Функция|КонецПроцедуры|КонецФункции|Возврат|Если|Тогда|Иначе|КонецЕсли|Для|Каждого|Из|Цикл|КонецЦикла|Новый|Запрос|Перем|Знач|Истина|Ложь|Неопределено|И|ИЛИ|НЕ|Пока|Прервать|Продолжить|Экспорт)\b/g;
  const num = /\b\d+(\.\d+)?\b/g;
  const str = /"([^"\\]|\\.)*"/g;
  const cmt = /\/\/.*$/gm;
  let out = String(children);
  // pseudo: render as styled spans by replacing with markers — keep simple and just colorize keywords
  // We'll do simple span replace via regex split
  const render = (line) => {
    let parts = [{t:line, c:null}];
    const apply = (regex, color) => {
      const out=[];
      for (const p of parts) {
        if (p.c) { out.push(p); continue; }
        let last=0,m; regex.lastIndex=0;
        while((m=regex.exec(p.t))) {
          if (m.index>last) out.push({t:p.t.slice(last,m.index),c:null});
          out.push({t:m[0], c:color});
          last=m.index+m[0].length;
        }
        if (last<p.t.length) out.push({t:p.t.slice(last),c:null});
      }
      parts = out;
    };
    apply(cmt, '#737373');
    apply(str, '#16A34A');
    apply(kws, '#0F766E');
    apply(num, '#D97706');
    return parts.map((p,i)=> p.c ? <span key={i} style={{color:p.c}}>{p.t}</span> : <span key={i}>{p.t}</span>);
  };
  return <pre className={`mono text-[12px] leading-[1.6] codebox p-2.5 overflow-x-auto whitespace-pre ${className}`}>{render(out)}</pre>;
}

/* -------------------- Table primitives -------------------- */
function Th({ children, w, align='left', className='' }) {
  return <th style={{width:w}} className={`text-[10.5px] mono uppercase tracking-wider text-ink-400 font-medium text-${align} px-2.5 py-1.5 border-b hl whitespace-nowrap ${className}`}>{children}</th>;
}
function Td({ children, align='left', className='', mono=false }) {
  return <td className={`px-2.5 py-1.5 text-${align} ${mono?'mono':''} ${className}`}>{children}</td>;
}

/* -------------------- Export -------------------- */
Object.assign(window, {
  I, Sev, Badge, KBD,
  Spark, MiniBars, Donut, LineChart, Heatmap,
  TopBar, Sidebar, StatusBar, CommandPalette, AIChat,
  Panel, PageHeader, KPI, Tabs, SegBtn, SegGroup,
  CodeBlock, SQLBlock, BSLBlock,
  Th, Td, NAV,
});
