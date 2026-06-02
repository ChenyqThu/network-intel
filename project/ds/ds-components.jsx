/* ============================================================
   Network Intel DS — component specimens + states
   Live, i18n-aware renderings of every core construct, each
   with token annotations in the spec bar.
   ============================================================ */

/* impact badge labels by lang */
const IMP_LABELS = {
  zh:{ threat:"威胁", opportunity:"机会", neutral:"中性", fix:"待修复", feat:"功能需求", strength:"优势确认" },
  en:{ threat:"Threat", opportunity:"Opportunity", neutral:"Neutral", fix:"Needs Fix", feat:"Feature Input", strength:"Strength" },
};
const IMP_ICON = { fix:"wrench", feat:"bulb", strength:"star" };
const RES_LABELS = {
  zh:{ threat:"威胁研判", opportunity:"机会研判", neutral:"中性研判", fix:"修复建议", feat:"需求信号", strength:"优势确认" },
  en:{ threat:"Threat", opportunity:"Opportunity", neutral:"Neutral", fix:"Fix", feat:"Signal", strength:"Strength" },
};
const SENTI_LABELS = {
  zh:{ pos:"情感:正面", neg:"情感:负面", neu:"情感:中性", rel:"相关性", intent:"切换意图" },
  en:{ pos:"Positive", neg:"Negative", neu:"Neutral", rel:"Rel", intent:"Switch intent" },
};

function ImpactPill({ impact, lang }) {
  const lbl = (IMP_LABELS[lang]||IMP_LABELS.zh)[impact] || impact;
  const ico = IMP_ICON[impact];
  return (
    <span className={"impact-pill "+impact}>
      {ico ? <Icon name={ico} size={13}/> : <span className="pd"/>}
      {lbl}
    </span>
  );
}

function SourceBadge({ glyph, name, tier, tierLabel }) {
  const cls = tier==='community' ? 'community' : 'official';
  return (
    <span className={"src "+cls}>
      <span className="src-ico"><SourceGlyph kind={glyph}/></span>
      <span className="src-name">{name}</span>
      <span className={"tier "+cls}>{tierLabel}</span>
    </span>
  );
}

function Research({ impact, note, lang }) {
  if (!note) return null;
  const k = (RES_LABELS[lang]||RES_LABELS.zh)[impact];
  return <div className={"research "+impact}><span className="rk">{k} · </span>{note}</div>;
}

function SentimentMeta({ senti, rel, intent, lang }) {
  const L = SENTI_LABELS[lang]||SENTI_LABELS.zh;
  return (
    <>
      {senti && <span className={"senti "+senti}><span className="sd"/>{L[senti]}</span>}
      {rel!=null && <span className="senti rel">{L.rel} {rel}</span>}
      {intent && <span className="senti intent">{L.intent}</span>}
    </>
  );
}

function CitationLine({ domain, tierLabel, date, official, citeId, lang }) {
  return (
    <a className={"cite "+(official?'official':'community')} onClick={e=>e.preventDefault()} href="#">
      {citeId!=null && <span className="cnum">{citeId}</span>}
      <span className="clk"><Icon name="link" size={14}/></span>
      <span className="cdom">{domain}</span>
      <span className="cflag">{tierLabel}</span>
      <span className="csep">·</span>
      <span className="cdate tnum">{date}</span>
      <span className="cgo">{lang==='en'?'View source':'查看原文'}<Icon name="external" size={13}/></span>
    </a>
  );
}

/* {{cite:N}} → clickable superscript */
function CiteText({ text }) {
  const parts = String(text).split(/(\{\{cite:\d+\}\})/g);
  return parts.map((p,i)=>{
    const m = p.match(/^\{\{cite:(\d+)\}\}$/);
    if (m) return <sup key={i} className="sup">{m[1]}</sup>;
    return <span key={i}>{p}</span>;
  });
}

function fmtNum(n){ return n>=1000 ? (n/1000).toFixed(n>=10000?0:1).replace(/\.0$/,'')+'k' : ''+n; }

/* full intel card specimen */
function IntelCard({ sampleKey, glyph, idx }) {
  const { t, lang } = useI18n();
  const s = window.NIDS.samples[sampleKey];
  const c = s[lang] || s.zh;
  const nodeCls = 'n-'+s.impact;
  return (
    <article className="entry">
      <div className="entry-rail">
        <span className="entry-idx tnum">{String(idx).padStart(2,'0')}</span>
        <span className={"entry-node "+nodeCls}/>
        <span className="rail-line"/>
      </div>
      <div className="entry-main">
        <div className="entry-head">
          <SourceBadge glyph={glyph} name={s.src} tier={s.tier.en==='community'?'community':(s.domain.includes('reddit')?'community':'official')} tierLabel={s.tier[lang]||s.tier.zh}/>
          <ImpactPill impact={s.impact} lang={lang}/>
        </div>
        <div className="entry-title-row">
          <a className="entry-title" onClick={e=>e.preventDefault()} href="#">{c.title}<span className="ext">↗</span></a>
          {s.stage && <span className="stage">{s.stage}</span>}
        </div>
        <div className="tags entry-tags">
          {c.tags.map((b,i)=><span className="tag" key={i}>{b}</span>)}
          <span className="tag src-a">{lang==='en'?'Feed A · monitor':'来源 A · 舆情监控'}</span>
          {(s.senti||s.rel!=null||s.intent) && <SentimentMeta senti={s.senti} rel={s.rel} intent={s.intent} lang={lang}/>}
        </div>
        <p className="entry-sum">{c.sum}</p>
        <Research impact={s.impact} note={c.note} lang={lang}/>
        <div className="entry-foot">
          <span className="metrics">
            {s.likes!=null && <span className="metric"><Icon name="up" size={14}/>{fmtNum(s.likes)}</span>}
            {s.comments!=null && <span className="metric"><Icon name="chat" size={14}/>{fmtNum(s.comments)}</span>}
            {s.views!=null && <span className="metric"><Icon name="eye" size={14}/>{fmtNum(s.views)}</span>}
          </span>
        </div>
        <CitationLine domain={s.domain} tierLabel={s.tier[lang]||s.tier.zh} date="2026-06-01" official={!s.domain.includes('reddit')} citeId={idx} lang={lang}/>
      </div>
    </article>
  );
}

/* lead + tally */
function LeadSpec() {
  const { t, lang } = useI18n();
  const L = window.NIDS.leadSample[lang] || window.NIDS.leadSample.zh;
  return (
    <div className="lead-spec">
      <div className="lead-eye">{lang==='en'?'LEAD · ':'本期导语 · '}<span className="opus">Opus {lang==='en'?'curation':'策展'}</span></div>
      <p className="lead-text"><CiteText text={L.text}/><span className="lead-strong">{L.strong}</span></p>
      <div className="tally">
        {L.tally.map(([txt,cls],i)=>(
          <span className={"tchip "+(cls==='t-omada-none'?'':cls)} key={i}><span className="cd"/>{txt}</span>
        ))}
      </div>
    </div>
  );
}

/* strategy insight block (v3) */
function StrategyBlock() {
  const { t, lang } = useI18n();
  const S = window.NIDS.strategySample[lang] || window.NIDS.strategySample.zh;
  return (
    <div className="strategy">
      <div className="strategy-head">
        <span className="strategy-mark"><Icon name="target" size={20}/></span>
        <div className="strategy-titles">
          <div className="strategy-title">{t('comp.strategy').replace(/\s*\(v3\)/,'')}</div>
          <div className="strategy-period">{S.period}</div>
        </div>
        <span className="opus-badge">OPUS {lang==='en'?'CURATION':'策展'}</span>
      </div>
      <div className="strategy-body">
        {S.paras.map((p,i)=>(
          <div className="strat-para" key={i}>
            <div className="strat-label">{p[0]}</div>
            <div className="strat-text"><CiteText text={p[1]}/></div>
          </div>
        ))}
        <div className="strat-refs">
          <span className="rl">{lang==='en'?'Basis':'依据'}</span>
          {S.refs.map(n=><span className="strat-ref" key={n}>[{n}]</span>)}
        </div>
      </div>
    </div>
  );
}

/* section head + tone */
function SectionHeadSpec({ tone, icon, num, title, count, desc }) {
  return (
    <div className={"tone-"+tone}>
      <div className="sec-head">
        <span className="sec-mark"><Icon name={icon} size={18}/></span>
        <div className="sec-titles">
          <div className="sec-title"><span className="sec-num">{num}</span>{title}{count!=null && <span className="sec-count tnum">{count}</span>}</div>
          <div className="sec-desc">{desc}</div>
        </div>
      </div>
      <div className="sec-rule"/>
    </div>
  );
}

/* store table */
function StoreTable() {
  const { lang } = useI18n();
  const rows = window.NIDS.storeSample[lang] || window.NIDS.storeSample.zh;
  const cols = window.NIDS.storeSample.cols[lang] || window.NIDS.storeSample.cols.zh;
  return (
    <table className="tbl">
      <thead><tr>{cols.map((c,i)=><th key={i}>{c}</th>)}</tr></thead>
      <tbody>
        {rows.map((r,i)=>(
          <tr key={i}>
            <td className="prod">{r[0]}</td>
            <td style={{color:'var(--fg-tertiary)', fontSize:12.5}}>{r[1]}</td>
            <td className="tnum">{r[2] && <span className="old">{r[2]}</span>}<span style={{fontWeight:700}}>{r[3]}</span></td>
            <td className={"chg "+(r[5]==='down'?'down':r[5]==='up'?'up':'')}>{r[4]}</td>
            <td><span className={"stockpill "+r[6]}>{r[7]}</span></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/* ============ COMPONENTS SECTION ============ */
function ComponentsSection() {
  const { t, lang } = useI18n();
  const tones = [
    ["omada_self","activity", lang==='en'?'Omada own sentiment':'Omada 自身舆情'],
    ["competitor","swords", lang==='en'?'Competitor moves':'竞品动态'],
    ["sentiment","chat", lang==='en'?'Competitor sentiment':'竞品舆情与对比'],
    ["industry","factory", lang==='en'?'Industry':'行业要闻'],
  ];
  return (
    <section className="ds-sec" id="comp">
      <SecHead eye="07" title={t('comp.title')} lead={t('comp.lead')}/>

      <div className="sub-h">{t('comp.src')}</div>
      <Spec inset bar={<><span className="lbl">.src</span><span className="tk">.tier.official / .tier.community</span></>}>
        <p className="note" style={{marginTop:0, marginBottom:14}}>{t('comp.srcDesc')}</p>
        <div style={{display:'flex', gap:24, flexWrap:'wrap'}}>
          <SourceBadge glyph="unifi" name="UniFi · Release" tier="official" tierLabel={lang==='en'?'first-party':'一手官方'}/>
          <SourceBadge glyph="reddit" name="Reddit · r/TPLink_Omada" tier="community" tierLabel={lang==='en'?'community':'社区一手'}/>
          <SourceBadge glyph="youtube" name="YouTube · Crosstalk" tier="community" tierLabel={lang==='en'?'community':'社区二手'}/>
        </div>
      </Spec>

      <div className="sub-h">{t('comp.impact')}</div>
      <Spec inset bar={<><span className="lbl">.impact-pill</span><span className="tk">.threat / .opportunity / .neutral · .fix / .feat / .strength</span></>}>
        <p className="note" style={{marginTop:0, marginBottom:14}}>{t('comp.impactDesc')}</p>
        <div style={{display:'flex', gap:10, flexWrap:'wrap'}}>
          {["threat","opportunity","neutral","fix","feat","strength"].map(k=><ImpactPill key={k} impact={k} lang={lang}/>)}
        </div>
      </Spec>

      <div className="sub-h">{t('comp.research')}</div>
      <Spec inset>
        <p className="note" style={{marginTop:0, marginBottom:14}}>{t('comp.researchDesc')}</p>
        <div style={{display:'grid', gap:12}}>
          <Research impact="threat" note={lang==='en'?'Express 7 directly targets the Omada entry line; track its feature cadence.':'Express 7 直接对标 Omada 入门线，需关注其功能补齐速度。'} lang={lang}/>
          <Research impact="fix" note={lang==='en'?'The rollback is reproducible — route to the firmware team to audit the flow.':'升级回滚为可复现问题，建议固件团队核查升级流程。'} lang={lang}/>
          <Research impact="strength" note={lang==='en'?'Local-first, no-subscription is a self-formed reputation strength to amplify.':'本地优先 + 无订阅是自发口碑优势，可强化稳定性叙事。'} lang={lang}/>
        </div>
      </Spec>

      <div className="sub-h">{t('comp.senti')}</div>
      <Spec inset bar={<><span className="lbl">.senti</span><span className="tk">.pos / .neg / .neu · .rel · .intent</span></>}>
        <p className="note" style={{marginTop:0, marginBottom:14}}>{t('comp.sentiDesc')}</p>
        <div className="tags">
          <SentimentMeta senti="neg" rel={0.88} intent={true} lang={lang}/>
          <SentimentMeta senti="pos" rel={0.9} lang={lang}/>
          <SentimentMeta senti="neu" lang={lang}/>
        </div>
      </Spec>

      <div className="sub-h">{t('comp.cite')}</div>
      <Spec inset>
        <p className="note" style={{marginTop:0, marginBottom:14}}>{t('comp.citeDesc')}</p>
        <div style={{display:'grid', gap:12}}>
          <CitationLine domain="community.ui.com" tierLabel={lang==='en'?'first-party':'一手官方'} date="2026-06-01" official={true} citeId={3} lang={lang}/>
          <CitationLine domain="reddit.com/r/TPLink_Omada" tierLabel={lang==='en'?'community':'社区一手'} date="2026-05-31" official={false} citeId={1} lang={lang}/>
        </div>
      </Spec>

      <div className="sub-h">{t('comp.entry')}</div>
      <Spec>
        <div style={{display:'grid', gap:30}}>
          <IntelCard sampleKey="self" glyph="reddit" idx={1}/>
          <IntelCard sampleKey="competitor" glyph="unifi" idx={3}/>
          <IntelCard sampleKey="sentiment" glyph="unifi" idx={5}/>
        </div>
      </Spec>

      <div className="sub-h">{t('comp.lead')}</div>
      <Spec><LeadSpec/></Spec>

      <div className="sub-h">{t('comp.strategy')}</div>
      <Spec inset>
        <p className="note" style={{marginTop:0, marginBottom:16}}>{t('comp.strategyDesc')}</p>
        <StrategyBlock/>
      </Spec>

      <div className="sub-h">{t('comp.sechead')}</div>
      <Spec inset bar={<><span className="lbl">.tone-*</span><span className="tk">omada_self · competitor · sentiment · industry</span></>}>
        <p className="note" style={{marginTop:0, marginBottom:16}}>{t('comp.secheadDesc')}</p>
        <div style={{display:'grid', gap:26}}>
          {tones.map(([tone,icon,title],i)=>(
            <SectionHeadSpec key={tone} tone={tone} icon={icon} num={String(i+1).padStart(2,'0')} title={title} count={lang==='en'?(i+2)+' items':(i+2)+' 条'} desc={tone}/>
          ))}
        </div>
      </Spec>

      <div className="sub-h">{t('comp.table')}</div>
      <Spec>
        <p className="note" style={{marginTop:0, marginBottom:14}}>{t('comp.tableDesc')}</p>
        <StoreTable/>
      </Spec>
    </section>
  );
}

/* ============ STATES SECTION ============ */
function StatesSection() {
  const { t, lang } = useI18n();
  return (
    <section className="ds-sec" id="states">
      <SecHead eye="08" title={t('states.title')} lead={t('states.lead')}/>
      <div className="sub-h">{t('states.primary')} · {t('states.ghost')}</div>
      <div className="state-grid">
        <div className="state-cell"><span className="nm">{t('states.rest')}</span><button className="demo-btn">{t('states.primary')}</button></div>
        <div className="state-cell"><span className="nm">{t('states.hover')}</span><button className="demo-btn is-hover">{t('states.primary')}</button></div>
        <div className="state-cell"><span className="nm">{t('states.focus')}</span><button className="demo-btn is-focus">{t('states.primary')}</button></div>
        <div className="state-cell"><span className="nm">{t('states.disabled')}</span><button className="demo-btn is-disabled" disabled>{t('states.primary')}</button></div>
        <div className="state-cell"><span className="nm">{t('states.rest')}</span><button className="demo-btn ghost">{t('states.ghost')}</button></div>
        <div className="state-cell"><span className="nm">{t('states.hover')}</span><button className="demo-btn ghost is-hover">{t('states.ghost')}</button></div>
      </div>
      <div className="sub-h">{t('states.loading')} · {t('states.empty')} · {t('states.error')}</div>
      <div className="state-grid">
        <div className="state-cell"><span className="nm">{t('states.loading')}</span><span style={{display:'inline-flex',alignItems:'center',gap:10,color:'var(--fg-tertiary)',fontSize:13}}><span className="spinner"/>{t('skeleton.loading')}</span></div>
        <div className="state-cell"><span className="nm">{t('states.empty')}</span><div className="empty-demo"><Icon name="check" size={22}/>{t('states.emptyText')}</div></div>
        <div className="state-cell"><span className="nm">{t('states.error')}</span><div className="error-demo"><Icon name="x" size={18}/>{t('states.errorText')}</div></div>
      </div>
    </section>
  );
}

Object.assign(window, {
  ImpactPill, SourceBadge, Research, SentimentMeta, CitationLine, CiteText, IntelCard,
  LeadSpec, StrategyBlock, SectionHeadSpec, StoreTable, ComponentsSection, StatesSection, fmtNum,
});
