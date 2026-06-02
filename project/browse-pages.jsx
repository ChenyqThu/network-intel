/* ============================================================
   Network Intel — browse pages: Archive + All Items (Dossier)
   ============================================================ */

function Chip({ on, onClick, children }) {
  return <button className={"chip"+(on?' on':'')} onClick={onClick}>{children}{on && <Icon name="x" size={12}/>}</button>;
}

/* ---- Archive ---- */
function ArchivePage({ onOpen }) {
  const [q,setQ] = useState('');
  const [type,setType] = useState('all');
  const [theme,setTheme] = useState('all');
  const list = NI.archive.filter(a=>{
    if (type!=='all' && a.type!==type) return false;
    if (theme!=='all' && !a.themes.includes(theme)) return false;
    if (q && !(a.title+a.excerpt).toLowerCase().includes(q.toLowerCase())) return false;
    return true;
  });
  const fmtD=(d)=>{ const [y,m,da]=d.split('-'); return {top:`${m}/${da}`,yr:y}; };
  return (
    <div className="wrap">
      <ReportHeader kicker="Network Intel · 归档" title="历史报告检索" actions={false}
        meta={[{icon:'doc',text:`${NI.archive.length} 期报告`},{icon:'calendar',text:'2026-05-17 至今'}]}/>
      <div className="filters">
        <label className="search">
          <Icon name="search" size={16}/>
          <input placeholder="搜索报告标题、摘要…" value={q} onChange={e=>setQ(e.target.value)}/>
        </label>
        <div className="chipset">
          <Chip on={type==='daily'} onClick={()=>setType(type==='daily'?'all':'daily')}>日报</Chip>
          <Chip on={type==='weekly'} onClick={()=>setType(type==='weekly'?'all':'weekly')}>周报</Chip>
          <span style={{width:1,height:20,background:'var(--border)',margin:'0 3px'}}/>
          {[['competitor','竞品'],['sentiment','舆情'],['pricing','定价'],['industry','行业']].map(([k,l])=>(
            <Chip key={k} on={theme===k} onClick={()=>setTheme(theme===k?'all':k)}>{l}</Chip>
          ))}
        </div>
      </div>
      <div className="arch-list">
        {list.map(a=>{ const d=fmtD(a.date); return (
          <div className="arch-row" key={a.id} onClick={()=>onOpen(a.id)}>
            <div className="arch-date tnum">{d.top}<span className="yr">{d.yr}</span></div>
            <div className="arch-main">
              <h3><span className={"type-badge "+a.type}>{a.type==='weekly'?'周报':'日报'}</span><span className="axt">{a.title}</span></h3>
              <p className="ax">{a.excerpt}</p>
            </div>
            <div className="arch-stats">
              <div className="arch-stat"><div className="v tnum">{a.signals}</div><div className="l">信号</div></div>
              <div className="arch-stat"><div className="v tnum" style={{color:a.threats?'var(--threat)':'var(--fg-faint)'}}>{a.threats}</div><div className="l">威胁</div></div>
              <div className="arch-stat"><div className="v tnum" style={{color:a.opps?'var(--opp)':'var(--fg-faint)'}}>{a.opps}</div><div className="l">机会</div></div>
            </div>
          </div>);})}
        {!list.length && <div style={{padding:'50px 0',textAlign:'center',color:'var(--fg-tertiary)'}}>没有匹配的报告，试试调整筛选条件。</div>}
      </div>
    </div>
  );
}

/* ---- All Items stream ---- */
function AllItemsPage() {
  const [q,setQ]=useState('');
  const [src,setSrc]=useState('all');
  const [cat,setCat]=useState('all');
  const [impact,setImpact]=useState('all');
  let list = NI.items.filter(it=>{
    if (src==='official' && it.source_tier!=='official') return false;
    if (src==='community' && it.source_tier!=='community') return false;
    if (cat!=='all' && it.category!==cat) return false;
    if (impact!=='all' && it.omada_impact!==impact) return false;
    if (q && !(it.title+it.summary).toLowerCase().includes(q.toLowerCase())) return false;
    return true;
  });
  list = [...list].sort((a,b)=> b.date.localeCompare(a.date) || a.id.localeCompare(b.id));
  const groups={}; list.forEach(it=>{ (groups[it.date]=groups[it.date]||[]).push(it); });
  const dayLabel=(d)=>{ const [,m,da]=d.split('-'); return `${+m} 月 ${+da} 日`; };
  let n=0;
  return (
    <div className="wrap">
      <ReportHeader kicker="Network Intel · 全部条目" title="情报条目流" actions={false}
        meta={[{icon:'inbox',text:`${NI.items.length} 条条目`},{icon:'filter',text:`${list.length} 条匹配`}]}/>
      <div className="filters">
        <label className="search">
          <Icon name="search" size={16}/>
          <input placeholder="搜索标题、摘要…" value={q} onChange={e=>setQ(e.target.value)}/>
        </label>
        <div className="chipset">
          <Chip on={src==='official'} onClick={()=>setSrc(src==='official'?'all':'official')}>官方源</Chip>
          <Chip on={src==='community'} onClick={()=>setSrc(src==='community'?'all':'community')}>社区源</Chip>
          <span style={{width:1,height:20,background:'var(--border)',margin:'0 3px'}}/>
          {[['threat','威胁'],['opportunity','机会'],['neutral','中性']].map(([k,l])=>(
            <Chip key={k} on={impact===k} onClick={()=>setImpact(impact===k?'all':k)}>{l}</Chip>
          ))}
          <span style={{width:1,height:20,background:'var(--border)',margin:'0 3px'}}/>
          {Object.entries(NI.CAT).map(([k,c])=>(
            <Chip key={k} on={cat===k} onClick={()=>setCat(cat===k?'all':k)}>{c.zh}</Chip>
          ))}
        </div>
      </div>
      <div style={{marginTop:8}}>
        {Object.keys(groups).sort((a,b)=>b.localeCompare(a)).map(date=>(
          <React.Fragment key={date}>
            <div className="stream-day">{dayLabel(date)}</div>
            <div className="sheet">
              {groups[date].map((it,i)=><IntelEntry key={it.id} item={it} idx={++n} delay={i*35}/>)}
            </div>
          </React.Fragment>
        ))}
        {!list.length && <div style={{padding:'50px 0',textAlign:'center',color:'var(--fg-tertiary)'}}>没有匹配的条目。</div>}
      </div>
    </div>
  );
}

Object.assign(window, { ArchivePage, AllItemsPage, Chip });
