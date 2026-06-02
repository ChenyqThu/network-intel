/* ============================================================
   Network Intel — dashboard charts (static, hi-fi SVG)
   Style variants driven by `style` prop: 'minimal' | 'filled'.
   Exports: Donut, SourceBars, TrendLine, KpiCard.
   ============================================================ */

/* ---- Donut: source contribution ---- */
function Donut({ data, total, style='minimal' }) {
  const sum = total || data.reduce((a,d)=>a+d.count,0);
  const R=58, sw = style==='filled'?28:16, C=2*Math.PI*R;
  let off=0;
  const gap = style==='filled'?0:1.5;
  return (
    <div style={{display:'flex',alignItems:'center',gap:24,flexWrap:'wrap'}}>
      <div style={{position:'relative',width:150,height:150,flex:'none'}}>
        <svg viewBox="0 0 150 150" width="150" height="150" style={{transform:'rotate(-90deg)'}}>
          <circle cx="75" cy="75" r={R} fill="none" stroke="var(--bg-subtle)" strokeWidth={sw}/>
          {data.map((d,i)=>{
            const frac=d.count/sum, len=C*frac;
            const el=(<circle key={i} cx="75" cy="75" r={R} fill="none" stroke={d.color}
              strokeWidth={sw} strokeDasharray={`${Math.max(len-gap,0)} ${C-Math.max(len-gap,0)}`}
              strokeDashoffset={-off} strokeLinecap={style==='filled'?'butt':'round'}/>);
            off+=len; return el;
          })}
        </svg>
        <div style={{position:'absolute',inset:0,display:'grid',placeItems:'center',textAlign:'center'}}>
          <div>
            <div className="tnum" style={{fontSize:30,fontWeight:800,letterSpacing:'-.03em',lineHeight:1}}>{sum}</div>
            <div style={{fontSize:11,fontWeight:600,color:'var(--fg-tertiary)',marginTop:3}}>条信号</div>
          </div>
        </div>
      </div>
      <div className="legend" style={{flex:1,minWidth:150}}>
        {data.map((d,i)=>(
          <div className="lr" key={i}>
            <span className="sw" style={{background:d.color}}/>
            <span className="ln">{d.label}</span>
            <span className="lv tnum">{d.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---- SourceBars: horizontal alternative to donut ---- */
function SourceBars({ data }) {
  const max=Math.max(...data.map(d=>d.count));
  return (
    <div style={{display:'flex',flexDirection:'column',gap:13}}>
      {data.map((d,i)=>(
        <div key={i}>
          <div style={{display:'flex',justifyContent:'space-between',fontSize:13,marginBottom:6}}>
            <span style={{fontWeight:600,color:'var(--fg-secondary)'}}>{d.label}</span>
            <span className="tnum" style={{fontWeight:700}}>{d.count}</span>
          </div>
          <div style={{height:9,background:'var(--bg-subtle)',borderRadius:99,overflow:'hidden'}}>
            <div style={{height:'100%',width:(d.count/max*100)+'%',background:d.color,borderRadius:99}}/>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ---- TrendLine: omada vs unifi over weeks ---- */
function TrendLine({ series, style='minimal' }) {
  const W=520, H=200, padX=12, padB=26, padT=14;
  const xs=series.length;
  const allVals=series.flatMap(d=>[d.omada,d.unifi]);
  const max=Math.max(...allVals)+6, min=Math.min(...allVals)-6;
  const px=i=> padX + i*((W-2*padX)/(xs-1));
  const py=v=> padT + (1-(v-min)/(max-min))*(H-padT-padB);
  const path=key=> series.map((d,i)=>`${i?'L':'M'}${px(i).toFixed(1)} ${py(d[key]).toFixed(1)}`).join(' ');
  const area=key=>`${path(key)} L ${px(xs-1)} ${H-padB} L ${px(0)} ${H-padB} Z`;
  const grid=[max,(max+min)/2,min].map(v=>Math.round(v));
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{display:'block'}} preserveAspectRatio="none">
        <defs>
          <linearGradient id="ga" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-primary)" stopOpacity="0.22"/>
            <stop offset="100%" stopColor="var(--color-primary)" stopOpacity="0"/>
          </linearGradient>
        </defs>
        {grid.map((g,i)=>{ const y=padT+i*((H-padT-padB)/2); return (
          <g key={i}>
            <line x1={padX} y1={y} x2={W-padX} y2={y} stroke="var(--border)" strokeWidth="1" strokeDasharray="2 4"/>
            <text x={W-padX} y={y-4} fontSize="9.5" fill="var(--fg-faint)" textAnchor="end" fontFamily="var(--font-mono)">{g}</text>
          </g>);})}
        {style==='filled' && <path d={area('omada')} fill="url(#ga)"/>}
        <path d={path('unifi')} fill="none" stroke="var(--fg-tertiary)" strokeWidth="2"
          strokeDasharray={style==='filled'?'5 4':'0'} strokeLinecap="round" strokeLinejoin="round"/>
        <path d={path('omada')} fill="none" stroke="var(--color-primary)" strokeWidth={style==='filled'?2.6:2.2} strokeLinecap="round" strokeLinejoin="round"/>
        {series.map((d,i)=>(<circle key={i} cx={px(i)} cy={py(d.omada)} r={i===xs-1?4:0} fill="var(--color-primary)"/>))}
        {series.map((d,i)=>(<text key={i} x={px(i)} y={H-9} fontSize="9.5" fill="var(--fg-faint)" textAnchor="middle" fontFamily="var(--font-mono)">{d.wk}</text>))}
      </svg>
      <div style={{display:'flex',gap:18,fontSize:12,marginTop:6,color:'var(--fg-tertiary)'}}>
        <span style={{display:'flex',alignItems:'center',gap:6}}><span style={{width:14,height:3,borderRadius:2,background:'var(--color-primary)'}}/>Omada 正面口碑指数</span>
        <span style={{display:'flex',alignItems:'center',gap:6}}><span style={{width:14,height:3,borderRadius:2,background:'var(--fg-tertiary)'}}/>UniFi</span>
      </div>
    </div>
  );
}

/* ---- KpiCard ---- */
function KpiCard({ label, icon, value, unit, delta, deltaText, dir }) {
  return (
    <div className="kpi">
      <div className="label">{icon && <Icon name={icon} size={14}/>}{label}</div>
      <div className="val tnum">{value}{unit && <span style={{fontSize:15,fontWeight:700,color:'var(--fg-tertiary)',marginLeft:3}}>{unit}</span>}</div>
      {deltaText && (
        <div className={"delta "+(dir||'flat')}>
          {dir==='up' && <Icon name="arrowUp" size={13}/>}
          {dir==='down' && <Icon name="arrowDown" size={13}/>}
          {deltaText}
        </div>
      )}
    </div>
  );
}

Object.assign(window, { Donut, SourceBars, TrendLine, KpiCard });
