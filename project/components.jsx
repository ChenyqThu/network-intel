/* ============================================================
   Network Intel — components (Dossier system)
   IntelEntry (ledger row), SourceBadge (glyph+tier), ImpactPill,
   Research note, CitationLine, Lead+Tally, References.
   ============================================================ */
const { useState } = React;

/* ---- icons ---- */
const ICONS = {
  swords:'M14.5 17.5 3 6V3h3l11.5 11.5M13 19l6-6M16 16l4 4M19 21l2-2M14.5 6.5 18 3h3v3l-3.5 3.5',
  chat:'M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z',
  factory:'M2 20a1 1 0 0 0 1 1h18a1 1 0 0 0 1-1V8l-7 5V8l-7 5V4a1 1 0 0 0-1-1H3a1 1 0 0 0-1 1zM7 21v-4M11 21v-4M15 21v-4',
  external:'M7 17 17 7M9 7h8v8',
  link:'M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1',
  arrowUp:'M12 19V5M5 12l7-7 7 7', arrowDown:'M12 5v14M5 12l7 7 7 7',
  trendUp:'M22 7 13.5 15.5l-5-5L2 17M16 7h6v6',
  thumb:'M7 10v12M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88z',
  eye:'M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
  up:'M12 19V5M6 11l6-6 6 6',
  search:'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3',
  calendar:'M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z',
  clock:'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 6v6l4 2',
  share:'M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8M16 6l-4-4-4 4M12 2v13',
  download:'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3',
  sun:'M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4',
  moon:'M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z',
  layers:'M12 2 2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5',
  check:'M20 6 9 17l-5-5',
  x:'M18 6 6 18M6 6l12 12',
  inbox:'M22 12h-6l-2 3h-4l-2-3H2M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z',
  filter:'M22 3H2l8 9.46V19l4 2v-8.54z',
  store:'M2 7l1.5-4h17L22 7M2 7h20M2 7v12a1 1 0 0 0 1 1h18a1 1 0 0 0 1-1V7M6 11v5M18 11v5',
  barChart:'M3 3v18h18M8 17V9M13 17V5M18 17v-6',
  zap:'M13 2 3 14h9l-1 8 10-12h-9z',
  sparkle:'M12 3l1.9 5.8L20 10l-6.1 1.2L12 17l-1.9-5.8L4 10l6.1-1.2z',
  doc:'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M16 13H8M16 17H8M10 9H8',
  mail:'M3 5h18a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2zM3 7l9 6 9-6',
};
function Icon({ name, size, style, cls }) {
  const d = ICONS[name]; if(!d) return null;
  return (
    <svg viewBox="0 0 24 24" width={size||18} height={size||18} fill="none"
      stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
      className={cls} style={style} aria-hidden="true">
      {d.split('M').filter(Boolean).map((seg,i)=><path key={i} d={'M'+seg}/>)}
    </svg>
  );
}

/* ---- source glyphs ---- */
function SourceGlyph({ kind }) {
  switch (kind) {
    case 'unifi': return (<svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2.2"/><path d="M12 7v5a3 3 0 0 0 6 0" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"/></svg>);
    case 'reddit': return (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12.5" r="8.5"/><circle cx="8.7" cy="12.5" r="1.1" fill="currentColor" stroke="none"/><circle cx="15.3" cy="12.5" r="1.1" fill="currentColor" stroke="none"/><path d="M8.7 15.5c1.8 1.2 4.8 1.2 6.6 0"/><circle cx="17.5" cy="6.5" r="1.4"/></svg>);
    case 'youtube': return (<svg viewBox="0 0 24 24" fill="none"><rect x="2.5" y="5.5" width="19" height="13" rx="3.5" stroke="currentColor" strokeWidth="1.9"/><path d="M10.3 9.3 15 12l-4.7 2.7z" fill="currentColor"/></svg>);
    case 'rss': return (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round"><circle cx="6" cy="18" r="1.4" fill="currentColor" stroke="none"/><path d="M5 11a8 8 0 0 1 8 8M5 5a14 14 0 0 1 14 14"/></svg>);
    case 'x': return (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round"><path d="M5 5l14 14M19 5 5 19"/></svg>);
    default: return null;
  }
}

/* ---- SourceBadge (glyph identity + credibility tier) ---- */
function SourceBadge({ item }) {
  const tier = item.source_tier || 'community';
  const s = NI.SRC[item.source] || {};
  const label = item.source_label || s.label;
  return (
    <span className={"src "+tier}>
      <span className="src-ico"><SourceGlyph kind={item.glyph || s.glyph}/></span>
      <span className="src-name">{label}</span>
      <span className={"tier "+tier}>{item.tier_label || (tier==='official'?'一手官方':'社区二手')}</span>
    </span>
  );
}

/* ---- ImpactPill ---- */
const IMP = { threat:{zh:"威胁",en:"Threat"}, opportunity:{zh:"机会",en:"Opportunity"}, neutral:{zh:"中性",en:"Neutral"}, unknown:{zh:"待判",en:"Unknown"} };
function ImpactPill({ impact }) {
  const m = IMP[impact] || IMP.unknown;
  const cls = impact==='threat'?'threat':impact==='opportunity'?'opportunity':'neutral';
  return <span className={"impact-pill "+cls}><span className="pd"/>{m.zh}</span>;
}

/* ---- Research note (no left bar) ---- */
function Research({ impact, note }) {
  if (!note) return null;
  const cls = impact==='threat'?'threat':impact==='opportunity'?'opportunity':'neutral';
  const k = impact==='threat'?'威胁研判':impact==='opportunity'?'机会研判':'中性研判';
  return <div className={"research "+cls}><span className="rk">{k} · </span>{note}</div>;
}

/* ---- metrics ---- */
function fmtNum(n){ return n>=1000 ? (n/1000).toFixed(n>=10000?0:1).replace(/\.0$/,'')+'k' : ''+n; }
function Metrics({ m }) {
  if (!m) return null;
  const out=[];
  if (m.likes)    out.push(<span className="metric" key="l"><Icon name="up" size={14}/>{fmtNum(m.likes)}</span>);
  if (m.comments) out.push(<span className="metric" key="c"><Icon name="chat" size={14}/>{fmtNum(m.comments)}</span>);
  if (m.views)    out.push(<span className="metric" key="v"><Icon name="eye" size={14}/>{fmtNum(m.views)}</span>);
  if (m.note)     out.push(<span className="metric" key="n" style={{opacity:.9}}>{m.note}</span>);
  if (!out.length) return null;
  return <span className="metrics">{out}</span>;
}

/* ---- citation line (PRD §7.8.1) ---- */
function CitationLine({ item, citeId }) {
  const official = (item.source_tier||'community')==='official';
  return (
    <a className={"cite "+(official?'official':'community')} href={item.url} target="_blank" rel="noopener noreferrer">
      {citeId!=null && <span className="cnum">{citeId}</span>}
      <span className="clk"><Icon name="link" size={14}/></span>
      <span className="cdom">{item.source_domain}</span>
      <span className="cflag">{item.tier_label || (official?'一手官方':'社区二手')}</span>
      <span className="csep">·</span>
      <span className="cdate">{item.date}</span>
      <span className="cgo">查看原文<Icon name="external" size={13}/></span>
    </a>
  );
}

/* ---- jump-to (offset scroll + flash, no scrollIntoView) ---- */
function jumpTo(id){
  const el = document.getElementById(id); if(!el) return;
  const navH = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--nav-h')) || 62;
  const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const y = el.getBoundingClientRect().top + window.pageYOffset - navH - 16;
  window.scrollTo({ top:y, behavior:reduce?'auto':'smooth' });
  el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash');
  setTimeout(()=>el.classList.remove('flash'), 1600);
}

/* ---- IntelEntry (dossier ledger row) ---- */
function IntelEntry({ item, idx, citeId=null, delay=0 }) {
  const node = item.omada_impact==='threat'?'n-threat':item.omada_impact==='opportunity'?'n-opportunity':'n-neutral';
  return (
    <article id={citeId!=null?('item-'+citeId):undefined} className="entry fade-up" style={{animationDelay:delay+'ms'}}>
      <div className="entry-rail">
        <span className="entry-idx tnum">{idx!=null?String(idx).padStart(2,'0'):''}</span>
        <span className={"entry-node "+node}/>
        <span className="rail-line"/>
      </div>
      <div className="entry-main">
        <div className="entry-head">
          <SourceBadge item={item}/>
          <ImpactPill impact={item.omada_impact}/>
        </div>
        <div className="entry-title-row">
          <a className="entry-title" href={item.url} target="_blank" rel="noopener noreferrer">{item.title}<span className="ext">↗</span></a>
          {item.stage && <span className="stage">{item.stage}</span>}
        </div>
        <div className="tags">
          {(item.badges||[]).map((b,i)=><span className="tag" key={i}>{b}</span>)}
          <span className="tag src-a">{item.provenance==='A'?'来源 A · 情报流':'来源 B · Supabase'}</span>
        </div>
        <p className="entry-sum">{item.summary}</p>
        <Research impact={item.omada_impact} note={item.impact_note}/>
        <div className="entry-foot">
          <Metrics m={item.metrics}/>
          {citeId!=null && <span className="cite-jump" role="link" tabIndex={0} onClick={()=>jumpTo('ref-'+citeId)} onKeyDown={e=>{if(e.key==='Enter')jumpTo('ref-'+citeId);}}>[{citeId}] 溯源</span>}
        </div>
        <CitationLine item={item} citeId={citeId}/>
      </div>
    </article>
  );
}

/* ---- Lead (导语 with {{cite:N}} superscripts) ---- */
function LeadText({ text, strong }) {
  const parts = text.split(/(\{\{cite:\d+\}\})/g);
  return (
    <p className="lead-text">
      {parts.map((p,i)=>{
        const m = p.match(/^\{\{cite:(\d+)\}\}$/);
        if (m) { const n=m[1];
          return <sup key={i} className="sup" role="link" tabIndex={0} onClick={()=>jumpTo('item-'+n)} onKeyDown={e=>{if(e.key==='Enter')jumpTo('item-'+n);}}>{n}</sup>;
        }
        return <span key={i}>{p}</span>;
      })}
      {strong && <span className="lead-strong">{strong}</span>}
    </p>
  );
}
function Lead({ report }) {
  const t = report.tally;
  return (
    <div className="lead">
      <div className="lead-eyebrow">本期导语 · <span className="opus">Opus 策展</span></div>
      <LeadText text={report.lead} strong={report.lead_strong}/>
      {t && (
        <div className="tally">
          <span className="tchip"><span className="cd"/>信号 {t.signals}</span>
          <span className="tchip t-threat"><span className="cd"/>威胁 {t.threat}</span>
          <span className="tchip t-opp"><span className="cd"/>机会 {t.opp}</span>
          <span className="tchip"><span className="cd"/>中性 {t.neutral}</span>
          <span className="tchip t-accent"><span className="cd"/>官方源 {t.official}</span>
        </div>
      )}
    </div>
  );
}

/* ---- SectionHead (mark + index + solid keyline rule) ---- */
function SectionHead({ icon, num, title, count, desc, id }) {
  return (
    <div id={id}>
      <div className="sec-head">
        <span className="sec-mark"><Icon name={icon} size={18}/></span>
        <div className="sec-titles">
          <div className="sec-title"><span className="sec-num">{num}</span>{title}{count!=null && <span className="sec-count tnum">{count} 条</span>}</div>
          {desc && <div className="sec-desc">{desc}</div>}
        </div>
      </div>
      <div className="sec-rule"/>
    </div>
  );
}

/* ---- References (PRD §7.8.4) ---- */
function References({ citeOrder }) {
  return (
    <section className="refs" id="refs">
      <div className="ref-h"><h2>参考来源</h2><span className="sub">References · 编号对应正文上标</span></div>
      <div className="reflist">
        {citeOrder.map((id,i)=>{ const it=NI.byId[id]; if(!it) return null;
          const official=(it.source_tier||'community')==='official';
          return (
            <div className="refitem" id={"ref-"+(i+1)} key={id}>
              <span className="rn" role="link" tabIndex={0} onClick={()=>jumpTo('item-'+(i+1))} onKeyDown={e=>{if(e.key==='Enter')jumpTo('item-'+(i+1));}}>[{i+1}]</span>
              <div className="rbody">
                <a className="rtitle" href={it.url} target="_blank" rel="noopener noreferrer">{it.title}</a>
                <div className="rmeta">
                  <span className={official?'official':''}>{it.source_domain}</span>
                  <span className="rsep">·</span><span>{it.date}</span>
                  <span className="rsep">·</span><span>{it.tier_label || (official?'一手官方':'社区二手')}</span>
                </div>
                <a className="rurl" href={it.url} target="_blank" rel="noopener noreferrer">{it.url}</a>
              </div>
              <a className="rgo" href={it.url} target="_blank" rel="noopener noreferrer" title="打开原文"><Icon name="external" size={15}/></a>
            </div>
          );})}
      </div>
    </section>
  );
}

/* ---- ReportHeader ---- */
function ReportHeader({ kicker, title, meta, actions=true }) {
  return (
    <header className="rhead">
      <div className="kicker">{kicker}</div>
      <h1>{title}</h1>
      <div className="rhead-meta">
        {meta.map((m,i)=>(<React.Fragment key={i}>{i>0 && <span className="sep">·</span>}<span className="m">{m.icon && <Icon name={m.icon} size={13}/>}{m.text}</span></React.Fragment>))}
        {actions && (
          <div className="rhead-actions">
            <button className="btn-ghost"><Icon name="share" size={15}/>分享</button>
            <button className="btn-ghost"><Icon name="download" size={15}/>导出</button>
          </div>
        )}
      </div>
    </header>
  );
}

function EmptyState({ text }) { return <div className="empty"><Icon name="check" size={20}/>{text}</div>; }

Object.assign(window, {
  Icon, SourceGlyph, SourceBadge, ImpactPill, Research, Metrics, CitationLine,
  IntelEntry, LeadText, Lead, SectionHead, References, ReportHeader, EmptyState,
  jumpTo, fmtNum,
});
