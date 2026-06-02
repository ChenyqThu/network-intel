/* ============================================================
   Network Intel DS — Skeleton & dynamic loading (live demo),
   Responsive, and i18n sections.
   ============================================================ */

/* ---- skeleton card (isomorphic to the real intel card) ---- */
function SkeletonCard({ anim }) {
  const a = anim ? ' anim' : '';
  return (
    <div className="skel-card" aria-hidden="true">
      <div className="skel-rail">
        <span className={"skel skel-node"+a} style={{width:9,height:9}}/>
        <span className="skel" style={{width:1, flex:1, minHeight:60, background:'var(--border)'}}/>
      </div>
      <div>
        <div style={{display:'flex', alignItems:'center', gap:10}}>
          <span className={"skel"+a} style={{width:22,height:22,borderRadius:6}}/>
          <span className={"skel skel-line"+a} style={{width:120}}/>
          <span className={"skel skel-line"+a} style={{width:54, marginLeft:'auto'}}/>
        </div>
        <div className={"skel skel-line"+a} style={{width:'72%', height:17, marginTop:14}}/>
        <div style={{display:'flex', gap:6, marginTop:13}}>
          <span className={"skel skel-line"+a} style={{width:48, height:18, borderRadius:999}}/>
          <span className={"skel skel-line"+a} style={{width:64, height:18, borderRadius:999}}/>
        </div>
        <div className={"skel skel-line"+a} style={{width:'100%', marginTop:13}}/>
        <div className={"skel skel-line"+a} style={{width:'88%', marginTop:8}}/>
        <div className={"skel"+a} style={{width:'100%', height:42, marginTop:14, borderRadius:'var(--radius-md)'}}/>
      </div>
    </div>
  );
}

function SkeletonSection() {
  const { t, lang } = useI18n();
  const [status,setStatus] = useState('ready');   // ready | loading
  const [net,setNet] = useState('fast');
  const timer = React.useRef(null);
  const reload = ()=>{
    if (timer.current) clearTimeout(timer.current);
    setStatus('loading');
    const delay = net==='slow' ? 2200 : 900;
    timer.current = setTimeout(()=>setStatus('ready'), delay);
  };
  React.useEffect(()=>()=>{ if(timer.current) clearTimeout(timer.current); },[]);

  const samples = [["self","reddit",1],["competitor","unifi",3],["sentiment","unifi",5]];

  return (
    <section className="ds-sec" id="skeleton">
      <SecHead eye="09" title={t('skeleton.title')} lead={t('skeleton.lead')}/>

      {/* live demo */}
      <Spec bar={<><span className="lbl">{t('skeleton.flowH')}</span><span className="tk">.skel.anim · @keyframes shimmer · .fade-up</span></>}>
        <div className="feed-controls">
          <button className="demo-btn" onClick={reload} disabled={status==='loading'} style={status==='loading'?{opacity:.5,cursor:'wait'}:null}>
            {status==='loading' ? t('skeleton.loading') : t('skeleton.reload')}
          </button>
          <span className="feed-status">
            <span className={"pulse"+(status==='loading'?' busy':'')}/>
            {status==='loading' ? t('skeleton.loading') : t('skeleton.ready')}
          </span>
          <span style={{flex:1}}/>
          <span className="feed-status">{t('skeleton.net')}</span>
          <span className="seg-sm">
            <button className={net==='fast'?'on':''} onClick={()=>setNet('fast')}>{t('skeleton.fast')}</button>
            <button className={net==='slow'?'on':''} onClick={()=>setNet('slow')}>{t('skeleton.slow')}</button>
          </span>
        </div>
        <div className="skel-feed">
          {status==='loading'
            ? samples.map((_,i)=><SkeletonCard key={i} anim={true}/>)
            : samples.map(([k,g,idx],i)=>(
                <div className="fade-up" key={k} style={{animationDelay:(i*45)+'ms'}}>
                  <IntelCard sampleKey={k} glyph={g} idx={idx}/>
                </div>
              ))
          }
        </div>
      </Spec>

      {/* isomorphism pattern */}
      <div className="sub-h">{t('skeleton.patternH')}</div>
      <Spec inset>
        <div className="spec-grid c2">
          <div>
            <div style={{fontFamily:'var(--font-mono)', fontSize:11, color:'var(--fg-tertiary)', marginBottom:14}}>skeleton</div>
            <SkeletonCard anim={false}/>
          </div>
          <div>
            <div style={{fontFamily:'var(--font-mono)', fontSize:11, color:'var(--fg-tertiary)', marginBottom:14}}>content</div>
            <IntelCard sampleKey="competitor" glyph="unifi" idx={3}/>
          </div>
        </div>
        <p className="note">{t('skeleton.patternNote')}</p>
      </Spec>

      {/* sequence */}
      <div className="sub-h">{t('skeleton.flowH')}</div>
      <Spec inset>
        <div style={{display:'grid', gap:12}}>
          {t('skeleton.flow').map((step,i)=>(
            <div key={i} style={{display:'flex', gap:12, alignItems:'flex-start', fontSize:14, color:'var(--fg-secondary)', lineHeight:1.55}}>
              <span style={{fontFamily:'var(--font-mono)', fontSize:12, fontWeight:700, color:'var(--color-primary)', flex:'none', width:20}}>{i+1}</span>
              <span>{step.replace(/^\d+\s·\s/,'')}</span>
            </div>
          ))}
        </div>
      </Spec>
    </section>
  );
}

/* ---- responsive ---- */
function ResponsiveSection() {
  const { t, lang } = useI18n();
  const bp = window.NIDS.DICT[lang].responsive.bp;
  return (
    <section className="ds-sec" id="responsive">
      <SecHead eye="10" title={t('responsive.title')} lead={t('responsive.lead')}/>
      <div className="sub-h">{t('responsive.bpH')}</div>
      <Spec>
        <div className="bp-list">
          {bp.map((r,i)=>(
            <div className="bp-row" key={i}>
              <div className="bp-name">{r[0]}<span className="w">{r[1]}</span></div>
              <div className="bp-desc">{r[2]}</div>
            </div>
          ))}
        </div>
      </Spec>
      <div className="sub-h">{t('responsive.gridH')}</div>
      <Spec inset>
        <div className="frame-row">
          <div className="mini-frame" style={{width:240}}>
            <div className="bar" style={{width:'40%'}}/>
            <div className="mini-cols"><div style={{width:54}}/><div style={{flex:1}}/></div>
            <div className="lbl">≥1280 · side + content</div>
          </div>
          <div className="mini-frame" style={{width:150}}>
            <div className="bar" style={{width:'55%'}}/>
            <div className="mini-cols"><div style={{flex:1}}/></div>
            <div className="lbl">640–1080 · single</div>
          </div>
          <div className="mini-frame" style={{width:92}}>
            <div className="bar" style={{width:'70%'}}/>
            <div className="mini-cols"><div style={{flex:1}}/></div>
            <div className="lbl">≤640 · mobile</div>
          </div>
        </div>
        <p className="note">{t('responsive.lead')}</p>
      </Spec>
    </section>
  );
}

/* ---- i18n ---- */
function I18nSection() {
  const { t, lang } = useI18n();
  const rows = window.NIDS.keySample;
  return (
    <section className="ds-sec" id="i18n">
      <SecHead eye="11" title={t('i18nSec.title')} lead={t('i18nSec.lead')}/>
      <div className="sub-h">{t('i18nSec.tryH')}</div>
      <Spec inset>
        <p className="note" style={{marginTop:0, fontSize:14, color:'var(--fg-secondary)'}}>{t('i18nSec.tryNote')}</p>
      </Spec>
      <div className="sub-h">{t('i18nSec.keyH')}</div>
      <Spec>
        <table className="key-tbl">
          <thead><tr>
            <th>{t('i18nSec.colKey')}</th>
            <th style={lang==='zh'?{color:'var(--color-primary)'}:null}>{t('i18nSec.colZh')}</th>
            <th style={lang==='en'?{color:'var(--color-primary)'}:null}>{t('i18nSec.colEn')}</th>
          </tr></thead>
          <tbody>
            {rows.map((r,i)=>(
              <tr key={i}>
                <td className="k">{r[0]}</td>
                <td className="v" style={lang==='zh'?{color:'var(--fg-primary)',fontWeight:600}:null}>{r[1]}</td>
                <td className="v" style={lang==='en'?{color:'var(--fg-primary)',fontWeight:600}:null}>{r[2]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Spec>
      <p className="note">{t('i18nSec.rules')}</p>
    </section>
  );
}

Object.assign(window, { SkeletonCard, SkeletonSection, ResponsiveSection, I18nSection });
