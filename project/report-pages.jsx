/* ============================================================
   Network Intel — report pages (Dossier)
   ReportView renders daily/weekly: lead + tally + section sheets
   + references, with per-report sidebar nav. Weekly adds store
   table + analytics dashboard.
   ============================================================ */

function pick(ids){ return ids.map(id=>NI.byId[id]).filter(Boolean); }

/* one section = header + a sheet of ledger entries */
function SectionSheet({ section, num, citeMap }) {
  const items = pick(section.items);
  return (
    <section className="sec" id={"sec-"+section.key}>
      <SectionHead icon={section.icon} num={num} title={section.title} count={items.length} desc={section.desc}/>
      <div className="sheet">
        {items.map((it,i)=>(
          <IntelEntry key={it.id} item={it} idx={citeMap[it.id]} citeId={citeMap[it.id]} delay={i*45}/>
        ))}
      </div>
    </section>
  );
}

/* ---- daily ---- */
function DailyBody({ rep, citeMap }) {
  return rep.sections.map((s,i)=>(
    <SectionSheet key={s.key} section={s} num={String(i+1).padStart(2,'0')} citeMap={citeMap}/>
  ));
}

/* ---- weekly analytics panels ---- */
function SentimentPanels({ db, chartStyle }) {
  return (
    <>
      <div className="dash-grid">
        <div className="panel">
          <div className="panel-head"><h3>口碑指数趋势</h3><span className="sub">近 8 周 · 情感加权</span></div>
          <TrendLine series={db.sentimentTrend} style={chartStyle}/>
        </div>
        <div className="panel">
          <div className="panel-head"><h3>高频痛点 Top 5</h3><span className="sub">UniFi 社区 · 本周</span></div>
          <div className="pain">
            {db.pains.map((p,i)=>(
              <div className="pr" key={i}>
                <div className="pt"><span className="pn">{p.name}</span><span className="pc tnum">{p.count}</span></div>
                <div className="track"><div className="fill" style={{width:(p.count/p.of*100)+'%',background:i<2?'var(--threat)':'var(--color-primary)'}}/></div>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="panel" style={{marginTop:16}}>
        <div className="panel-head"><h3>Omada vs UniFi · 本周正面口碑</h3><span className="sub">环比 W21 → W22</span></div>
        <div className="vs">
          <div className="vr"><div className="vl"><span>Omada</span><span className="tnum" style={{color:'var(--opp)'}}>{db.vs.omada} ▲</span></div><div className="bar omada"><i style={{width:db.vs.omada+'%'}}/></div></div>
          <div className="vr"><div className="vl"><span>UniFi</span><span className="tnum" style={{color:'var(--threat)'}}>{db.vs.unifi} ▼</span></div><div className="bar unifi"><i style={{width:db.vs.unifi+'%'}}/></div></div>
        </div>
      </div>
    </>
  );
}

function WeeklyBody({ rep, citeMap, chartStyle }) {
  const db = rep.dashboard;
  const S = rep.sections;
  return (
    <>
      <SectionSheet section={S[0]} num="1" citeMap={citeMap}/>

      <SectionSheet section={S[1]} num="2" citeMap={citeMap}/>
      <div style={{marginTop:18}}><SentimentPanels db={db} chartStyle={chartStyle}/></div>

      <section className="sec" id="sec-store">
        <SectionHead icon="store" num="3" title="Store 动向" desc="价格 / 库存 / 上架变化"/>
        <div className="sheet" style={{padding:'8px 8px'}}>
          <table className="tbl">
            <thead><tr><th>产品</th><th>类别</th><th>价格</th><th>变化</th><th>库存</th></tr></thead>
            <tbody>
              {rep.store.map((r,i)=>(
                <tr key={i}>
                  <td className="prod">{r.product}</td>
                  <td style={{color:'var(--fg-tertiary)',fontSize:12.5}}>{r.cat}</td>
                  <td className="pricecell">{r.from && <span className="old">${r.from}</span>}<span style={{fontWeight:700}}>{r.to?`$${r.to}`:'—'}</span></td>
                  <td className={"chg "+(r.dir==='down'?'down':r.dir==='up'?'up':'')}>{r.change}</td>
                  <td><span className={"stockpill "+(r.stock==='in'?'in':r.stock==='low'?'low':'out')}>{r.stock==='in'?'有货':r.stock==='low'?'紧张':'缺货'}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <SectionSheet section={S[2]} num="4" citeMap={citeMap}/>

      <section className="sec" id="sec-dashboard">
        <SectionHead icon="barChart" num="5" title="数据看板" desc="信号量 / 各源贡献 / 热度 Top"/>
        <div className="kpi-grid">
          <KpiCard label="本周信号量" icon="zap" value={db.signals} deltaText={`${db.signalsDelta>0?'+':''}${db.signalsDelta} 环比`} dir={db.signalsDelta>0?'up':'down'}/>
          <KpiCard label="威胁 / 机会" icon="swords" value={`${db.threats}/${db.opps}`} deltaText={`${db.neutral} 中性`} dir="flat"/>
          <KpiCard label="新竞品动作" icon="sparkle" value={db.newCompetitor} deltaText={`${db.newCompetitorDelta>0?'+':''}${db.newCompetitorDelta} 环比`} dir={db.newCompetitorDelta>0?'up':'down'}/>
          <KpiCard label="平均热度" icon="trendUp" value={db.avgHeat} deltaText={`${db.avgHeatDelta>0?'+':''}${db.avgHeatDelta} 环比`} dir={db.avgHeatDelta>0?'up':'down'}/>
        </div>
        <div className="dash-grid">
          <div className="panel">
            <div className="panel-head"><h3>各源贡献</h3><span className="sub">本周 {db.signals} 条</span></div>
            {chartStyle==='filled' ? <SourceBars data={db.sources}/> : <Donut data={db.sources} total={db.signals} style="minimal"/>}
          </div>
          <div className="panel">
            <div className="panel-head"><h3>热度 Top 5</h3><span className="sub">赞 + 评论加权</span></div>
            <div className="rank">
              {db.topHeat.map((h,i)=>{ const it=NI.byId[h.id]; return (
                <div className={"rr"+(i<1?' top':'')} key={i}>
                  <span className="ri">{String(i+1).padStart(2,'0')}</span>
                  <div className="rl"><div className="rt">{it.title}</div><div className="rm">{(NI.SRC[it.source]||{}).label} · {NI.CAT[it.category].zh}</div></div>
                  <span className="rv tnum">{h.fmt==='views'?fmtNum(h.v)+' 播放':fmtNum(h.v)}</span>
                </div>);})}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

/* ---- sidebar nav (per report) ---- */
function ReportAside({ rep, type, current, onOpen }) {
  const nav = type==='weekly'
    ? [["lead","本期导语","导语"],["sec-competitor","竞品动作盘点","1"],["sec-sentiment","用户舆情趋势","2"],["sec-store","Store 动向","3"],["sec-industry","行业风向","4"],["sec-dashboard","数据看板","5"],["refs","参考来源",String(rep.citeOrder.length)]]
    : [["lead","本期导语","导语"], ...rep.sections.map((s)=>["sec-"+s.key,s.title,String(s.items.length)]), ["refs","参考来源",String(rep.citeOrder.length)]];
  const recent = NI.archive.filter(a=>a.id!==current).slice(0,5);
  return (
    <aside className="aside">
      <div className="aside-sticky">
        <div className="aside-h">本期 · {type==='weekly'?rep.rangeLabel:rep.date}</div>
        <nav className="toc">
          {nav.map(([id,t,n],i)=>(
            <a key={id} className={i===0?'active':''} role="link" tabIndex={0} onClick={()=>jumpTo(id)} onKeyDown={e=>{if(e.key==='Enter')jumpTo(id);}}>{t}<span className="n tnum">{n}</span></a>
          ))}
        </nav>
        <div className="aside-div"/>
        <div className="aside-note">
          数据融合 · 双路<br/>
          <b>来源 B</b> UNIFI_CHANNELS Supabase（一手官方）<br/>
          <b>来源 A</b> 个人情报流 Reddit / YouTube
          <br/><br/>
          <a href="email-daily.html" target="_blank" rel="noopener" style={{color:'var(--color-primary)',fontWeight:600,display:'inline-flex',alignItems:'center',gap:6}}><Icon name="mail" size={14}/>邮件推送版本 ↗</a>
        </div>
        <div className="aside-div"/>
        <div className="aside-h">近期报告</div>
        <div className="hist">
          {recent.map(a=>(
            <div className="hist-row" key={a.id} onClick={()=>onOpen(a.id)}>
              <span className="hl">{a.title.length>15?a.title.slice(0,15)+'…':a.title}</span>
              <span className="ht">{a.type==='weekly'?'周':'日'}</span>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}

/* ---- ReportView ---- */
function ReportView({ type, setType, t, onOpen }) {
  const rep = type==='weekly' ? NI.weeklyReport : NI.dailyReport;
  const twoCol = t.homeLayout==='two';
  const citeMap = Object.fromEntries((rep.citeOrder||[]).map((id,i)=>[id,i+1]));
  const meta = type==='weekly'
    ? [{icon:'calendar',text:rep.rangeLabel},{icon:'clock',text:rep.generated},{text:rep.source_line}]
    : [{icon:'calendar',text:'覆盖 '+rep.date},{icon:'clock',text:rep.generated},{text:rep.source_line}];
  return (
    <div className="wrap">
      <div style={{paddingTop:24,display:'flex',alignItems:'center',gap:14}}>
        <div className="seg">
          <button className={type==='daily'?'on':''} onClick={()=>setType('daily')}><span className="dot"/>日报</button>
          <button className={type==='weekly'?'on':''} onClick={()=>setType('weekly')}><span className="dot"/>周报</button>
        </div>
        <span style={{fontFamily:'var(--font-mono)',fontSize:12,color:'var(--fg-tertiary)'}}>最新一期 · {type==='weekly'?rep.rangeLabel:rep.date}</span>
      </div>

      <ReportHeader kicker="Network Intel · 内部竞品情报"
        title={type==='weekly'?(rep.rangeLabel+' · 周报'):rep.dateLabel} meta={meta}/>

      <div id="lead"><Lead report={rep}/></div>

      <div className={"home-grid"+(twoCol?' two':'')} style={{marginTop:8}}>
        {twoCol && <ReportAside rep={rep} type={type} current={rep.report_id} onOpen={onOpen}/>}
        <div>
          {type==='weekly' ? <WeeklyBody rep={rep} citeMap={citeMap} chartStyle={t.chartStyle}/>
                           : <DailyBody rep={rep} citeMap={citeMap}/>}
          <References citeOrder={rep.citeOrder}/>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { ReportView, DailyBody, WeeklyBody, SectionSheet, pick });
