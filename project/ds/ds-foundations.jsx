/* ============================================================
   Network Intel DS — shared primitives + foundation sections
   Icon set, SourceGlyph, BrandMark, useI18n hook, and the
   Color / Type / Spacing / Elevation / Motion / Icon sections.
   ============================================================ */
const { useState, useContext, useEffect, useRef } = React;

/* ---- i18n hook ---- */
function useI18n(){
  const lang = useContext(window.LangCtx);
  const t = (k)=> window.dsT(lang, k);
  return { t, lang };
}

/* ---- icons ---- */
const ICONS = {
  activity:'M22 12h-4l-3 9L9 3l-3 9H2',
  swords:'M14.5 17.5 3 6V3h3l11.5 11.5M13 19l6-6M16 16l4 4M19 21l2-2M14.5 6.5 18 3h3v3l-3.5 3.5',
  chat:'M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z',
  factory:'M2 20a1 1 0 0 0 1 1h18a1 1 0 0 0 1-1V8l-7 5V8l-7 5V4a1 1 0 0 0-1-1H3a1 1 0 0 0-1 1zM7 21v-4M11 21v-4M15 21v-4',
  target:'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 18a6 6 0 1 0 0-12 6 6 0 0 0 0 12zM12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4z',
  external:'M7 17 17 7M9 7h8v8',
  link:'M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1',
  trendUp:'M22 7 13.5 15.5l-5-5L2 17M16 7h6v6',
  eye:'M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
  up:'M12 19V5M6 11l6-6 6 6',
  search:'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3',
  calendar:'M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z',
  clock:'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 6v6l4 2',
  share:'M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8M16 6l-4-4-4 4M12 2v13',
  download:'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3',
  sun:'M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4',
  moon:'M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z',
  zap:'M13 2 3 14h9l-1 8 10-12h-9z',
  barChart:'M3 3v18h18M8 17V9M13 17V5M18 17v-6',
  store:'M2 7l1.5-4h17L22 7M2 7h20M2 7v12a1 1 0 0 0 1 1h18a1 1 0 0 0 1-1V7M6 11v5M18 11v5',
  mail:'M3 5h18a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2zM3 7l9 6 9-6',
  check:'M20 6 9 17l-5-5',
  x:'M18 6 6 18M6 6l12 12',
  wrench:'M14.7 6.3a4 4 0 0 0-5.2 5L3 17.8 6.2 21l6.5-6.5a4 4 0 0 0 5-5.2l-2.6 2.6-2.1-.4-.4-2.1z',
  bulb:'M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.2 1 2V18h6v-1.3c0-.8.4-1.5 1-2A7 7 0 0 0 12 2z',
  star:'M12 2.5l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.9 6.1 20.5l1.2-6.5L2.5 9.4l6.6-.9z',
  filter:'M22 3H2l8 9.46V19l4 2v-8.54z',
  inbox:'M22 12h-6l-2 3h-4l-2-3H2M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z',
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
    default: return null;
  }
}

function BrandMark() {
  return (
    <svg className="mk" viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <rect x="0.5" y="0.5" width="31" height="31" rx="8" fill="var(--color-primary)"/>
      <circle cx="11" cy="21" r="2.6" fill="#fff"/>
      <path d="M16 18.5a8 8 0 0 0-5.5-2.2" stroke="#fff" strokeWidth="2" strokeLinecap="round" opacity=".95"/>
      <path d="M19.5 15a12.5 12.5 0 0 0-9-3.6" stroke="#fff" strokeWidth="2" strokeLinecap="round" opacity=".6"/>
      <path d="M23 11.4A17 17 0 0 0 10.6 6.4" stroke="#fff" strokeWidth="2" strokeLinecap="round" opacity=".32"/>
    </svg>
  );
}

/* ---- section scaffold ---- */
function SecHead({ id, eye, title, lead }) {
  return (
    <div>
      <div className="sec-eye">{eye}</div>
      <h2>{title}</h2>
      {lead && <p className="lead">{lead}</p>}
    </div>
  );
}
function Spec({ children, bar, inset }) {
  return (
    <div className="spec">
      <div className={"spec-stage"+(inset?' inset':'')}>{children}</div>
      {bar && <div className="spec-bar">{bar}</div>}
    </div>
  );
}

/* ============ COLOR ============ */
function Swatch({ c, lang }) {
  return (
    <div className="sw">
      <div className="sw-chip" style={{background:`var(${c.tk})`}}/>
      <div className="sw-meta">
        <div className="sw-name">{c.name}</div>
        <div className="sw-val"><span className="sw-tk">{c.tk}</span></div>
        <div className="sw-val"><span>L {c.light}</span><span>D {c.dark}</span></div>
      </div>
    </div>
  );
}
function ColorSection() {
  const { t, lang } = useI18n();
  const C = window.NIDS.colors;
  const senti = [["pos","--opp"],["neu","--neutral"],["neg","--threat"]];
  return (
    <section className="ds-sec" id="color">
      <SecHead eye="01" title={t('color.title')} lead={t('color.lead')}/>
      <div className="sub-h">{t('color.brand')}</div>
      <div className="sw-grid">{C.brand.map(c=><Swatch key={c.tk} c={c} lang={lang}/>)}</div>
      <div className="sub-h">{t('color.impact')}</div>
      <div className="sw-grid">{C.impact.map(c=><Swatch key={c.tk} c={c} lang={lang}/>)}</div>
      <div className="sub-h">{t('color.self')}</div>
      <div className="sw-grid">{C.self.map(c=><Swatch key={c.tk+c.name} c={c} lang={lang}/>)}</div>
      <div className="sub-h">{t('color.neutralH')}</div>
      <div className="sw-grid">{C.neutral.map(c=><Swatch key={c.tk} c={c} lang={lang}/>)}</div>
      <p className="note">{t('color.note')}</p>
    </section>
  );
}

/* ============ TYPE ============ */
function TypeSection() {
  const { t } = useI18n();
  const T = window.NIDS.type, W = window.NIDS.weights;
  return (
    <section className="ds-sec" id="type">
      <SecHead eye="02" title={t('type.title')} lead={t('type.lead')}/>
      <div className="sub-h">{t('type.scale')}</div>
      <Spec>
        {T.map(r=>(
          <div className="type-row" key={r.key}>
            <div className="type-meta">
              <b>{t('type.'+r.key)}</b>
              {r.px}px · {r.wt} · {r.lh}
            </div>
            <div className="type-sample" style={{fontSize:r.px, fontWeight:r.wt, lineHeight:r.lh, letterSpacing:r.ls, fontFamily:r.mono?'var(--font-mono)':'var(--font-sans)'}}>{r.sample}</div>
          </div>
        ))}
      </Spec>
      <div className="sub-h">{t('type.weight')}</div>
      <div className="weight-grid">
        {W.map(w=>(
          <div className="wt" key={w.w}>
            <div className="big" style={{fontWeight:w.w}}>Aa 网络</div>
            <div className="lbl">{w.n} · {w.w}</div>
          </div>
        ))}
      </div>
      <div className="sub-h">{t('type.numic')}</div>
      <Spec bar={<><span className="lbl">.tnum</span><span className="tk">font-variant-numeric: tabular-nums</span></>}>
        <div className="tnum" style={{fontFamily:'var(--font-mono)', fontSize:22, letterSpacing:'.02em'}}>132.60W · 23.1W / 132.60W · 16:57:04 · 12/20 · 5GHz</div>
        <p className="note">{t('type.numNote')}</p>
      </Spec>
    </section>
  );
}

/* ============ SPACING & RADIUS ============ */
function SpaceSection() {
  const { t } = useI18n();
  const S = window.NIDS.spacing, R = window.NIDS.radii;
  return (
    <section className="ds-sec" id="space">
      <SecHead eye="03" title={t('space.title')} lead={t('space.lead')}/>
      <div className="sub-h">{t('space.spacing')}</div>
      <Spec>
        <div className="scale-list">
          {S.map(s=>(
            <div className="scale-row" key={s.n}>
              <span className="nm"><b>{s.n}</b> · {s.v}px</span>
              <span className="scale-bar" style={{width:s.v}}/>
            </div>
          ))}
        </div>
      </Spec>
      <div className="sub-h">{t('space.radius')}</div>
      <div className="radius-grid">
        {R.map(r=>(
          <div className="rad" key={r.n}>
            <div className="box" style={{borderRadius:r.v>100?'40px':r.v}}/>
            <div className="lbl"><b>{r.n}</b>{r.v>100?'pill':r.v+'px'}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ============ ELEVATION & BORDER ============ */
function ElevationSection() {
  const { t } = useI18n();
  return (
    <section className="ds-sec" id="elevation">
      <SecHead eye="04" title={t('elevation.title')} lead={t('elevation.lead')}/>
      <div className="elev-grid" style={{marginTop:24}}>
        <div className="elev">none · --border</div>
        <div className="elev card">card · --shadow-card</div>
        <div className="elev pop">pop · --shadow-pop</div>
      </div>
      <p className="note" style={{marginTop:18}}><b>{t('elevation.border')} ·</b> {t('elevation.borderNote')}</p>
    </section>
  );
}

/* ============ MOTION ============ */
function MotionCard({ m, t }) {
  const [run,setRun] = useState(false);
  const ref = useRef(null);
  const fire = ()=>{ setRun(false); requestAnimationFrame(()=>requestAnimationFrame(()=>setRun(true))); };
  return (
    <div className={"mo"+(run?' run':'')} ref={ref} style={{['--mo-dur']:m.dur+'ms'}} onClick={fire}
      onAnimationEnd={()=>setRun(false)}>
      <div className="nm">{t('motion.'+m.key)}</div>
      <div className="track"><span className="dot"/></div>
      <div className="vl">{m.label} · {m.dur}ms · {t('motion.click')}</div>
    </div>
  );
}
function MotionSection() {
  const { t } = useI18n();
  const M = window.NIDS.motion;
  return (
    <section className="ds-sec" id="motion">
      <SecHead eye="05" title={t('motion.title')} lead={t('motion.lead')}/>
      <div className="motion-grid" style={{marginTop:24}}>
        {M.map(m=><MotionCard key={m.key} m={m} t={t}/>)}
      </div>
      <p className="note" style={{marginTop:18}}>{t('motion.easeNote')}</p>
    </section>
  );
}

/* ============ ICONS ============ */
function IconSection() {
  const { t } = useI18n();
  const list = window.NIDS.icons;
  return (
    <section className="ds-sec" id="icon">
      <SecHead eye="06" title={t('icon.title')} lead={t('icon.lead')}/>
      <Spec inset>
        <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(92px,1fr))', gap:14}}>
          {list.map(n=>(
            <div key={n} style={{display:'flex', flexDirection:'column', alignItems:'center', gap:8, padding:'14px 6px', border:'1px solid var(--border)', borderRadius:'var(--radius-md)', background:'var(--bg-surface)'}}>
              <Icon name={n} size={22} style={{color:'var(--fg-primary)'}}/>
              <span style={{fontFamily:'var(--font-mono)', fontSize:10, color:'var(--fg-tertiary)'}}>{n}</span>
            </div>
          ))}
        </div>
      </Spec>
    </section>
  );
}

Object.assign(window, {
  useI18n, Icon, ICONS, SourceGlyph, BrandMark, SecHead, Spec,
  ColorSection, TypeSection, SpaceSection, ElevationSection, MotionSection, IconSection,
});
