/* ============================================================
   Network Intel — app shell
   Topbar + wordmark, view routing, theme (system default),
   Tweaks integration.
   ============================================================ */
const { useEffect } = React;

/* brand mark: broadcast arcs + node, in a rounded plate */
function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <rect x="0.5" y="0.5" width="31" height="31" rx="8" fill="var(--color-primary)"/>
      <circle cx="11" cy="21" r="2.6" fill="#fff"/>
      <path d="M16 18.5a8 8 0 0 0-5.5-2.2" stroke="#fff" strokeWidth="2" strokeLinecap="round" opacity=".95"/>
      <path d="M19.5 15a12.5 12.5 0 0 0-9-3.6" stroke="#fff" strokeWidth="2" strokeLinecap="round" opacity=".6"/>
      <path d="M23 11.4A17 17 0 0 0 10.6 6.4" stroke="#fff" strokeWidth="2" strokeLinecap="round" opacity=".32"/>
    </svg>
  );
}

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "primaryColor": "#0C6151",
  "density": "regular",
  "homeLayout": "two",
  "chartStyle": "minimal",
  "theme": "system"
}/*EDITMODE-END*/;

function App() {
  const [t,setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [view,setView] = useState('home');      // home | archive | items
  const [reportType,setReportType] = useState('daily');
  const [scrolled,setScrolled] = useState(false);

  // theme: resolve system unless overridden
  const sysDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  const [sysIsDark,setSysIsDark] = useState(sysDark);
  useEffect(()=>{
    if (!window.matchMedia) return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const fn = e=>setSysIsDark(e.matches);
    mq.addEventListener && mq.addEventListener('change',fn);
    return ()=> mq.removeEventListener && mq.removeEventListener('change',fn);
  },[]);
  const resolvedTheme = t.theme==='system' ? (sysIsDark?'dark':'light') : t.theme;

  useEffect(()=>{
    const r=document.documentElement;
    r.setAttribute('data-theme',resolvedTheme);
    r.setAttribute('data-density',t.density);
    r.style.setProperty('--tw-primary',t.primaryColor);
  },[resolvedTheme,t.density,t.primaryColor]);

  useEffect(()=>{
    const fn=()=>setScrolled(window.scrollY>8);
    window.addEventListener('scroll',fn,{passive:true}); return ()=>window.removeEventListener('scroll',fn);
  },[]);

  const go=(v)=>{ setView(v); window.scrollTo({top:0,behavior:'instant'}); };
  const openReport=(id)=>{
    const a = NI.archive.find(x=>x.id===id);
    if (a) setReportType(a.type);
    setView('home'); window.scrollTo({top:0,behavior:'instant'});
  };
  const toggleTheme=()=> setTweak('theme', resolvedTheme==='dark'?'light':'dark');

  return (
    <div className="shell">
      <header className={"topbar"+(scrolled?' scrolled':'')}>
        <div className="brand" onClick={()=>go('home')}>
          <BrandMark/>
          <span className="brand-name">Network <span className="intel">Intel</span></span>
          <span className="brand-tag">内部情报</span>
        </div>
        <nav className="nav">
          <button className={"nav-link"+(view==='home'?' active':'')} onClick={()=>go('home')}>最新报告</button>
          <button className={"nav-link"+(view==='archive'?' active':'')} onClick={()=>go('archive')}>归档检索</button>
          <button className={"nav-link"+(view==='items'?' active':'')} onClick={()=>go('items')}>全部条目</button>
        </nav>
        <div className="topbar-spacer"/>
        <span className="nav-date tnum">2026-06-01 · 09:30 PT</span>
        <button className="icon-btn" onClick={toggleTheme} title={resolvedTheme==='dark'?'切换亮色':'切换暗色'} aria-label="切换主题">
          <Icon name={resolvedTheme==='dark'?'sun':'moon'} size={18}/>
        </button>
      </header>

      <main className="page" key={view+reportType}>
        {view==='home'   && <ReportView type={reportType} setType={setReportType} t={t} onOpen={openReport}/>}
        {view==='archive'&& <ArchivePage onOpen={openReport}/>}
        {view==='items'  && <AllItemsPage/>}
      </main>

      <footer className="foot">
        <div className="wrap">
          <div>
            <div className="foot-brand">Network Intel</div>
            <p className="foot-note">内部竞品 &amp; 舆情情报 · 仅限 TP-Link 网络产品团队。每条结论可一键溯源验证——这是策展报告与普通信息聚合的本质区别。数据融合：UNIFI_CHANNELS Supabase（一手官方）+ 个人情报流（Reddit / YouTube）。</p>
          </div>
          <div className="foot-links">
            <a href="email-daily.html" target="_blank" rel="noopener">邮件版 ↗</a>
            <a onClick={()=>go('archive')}>归档</a>
            <a onClick={()=>go('items')}>全部条目</a>
            <a href="https://www.feishu.cn/docx/TXrNdLo7uoc8mfx9NIec45Z7n8c" target="_blank" rel="noopener">PRD ↗</a>
          </div>
        </div>
      </footer>

      <TweaksPanel title="Tweaks">
        <TweakSection label="外观"/>
        <TweakColor label="主色" value={t.primaryColor}
          options={['#0C6151','#0A5A5A','#15503B','#1F4E79','#2C2F36']}
          onChange={v=>setTweak('primaryColor',v)}/>
        <TweakRadio label="主题" value={t.theme} options={['system','light','dark']}
          onChange={v=>setTweak('theme',v)}/>
        <TweakRadio label="密度" value={t.density} options={['compact','regular','comfy']}
          onChange={v=>setTweak('density',v)}/>
        <TweakSection label="布局 & 图表"/>
        <TweakRadio label="首页布局" value={t.homeLayout} options={['two','single']}
          onChange={v=>setTweak('homeLayout',v)}/>
        <TweakRadio label="图表风格" value={t.chartStyle} options={['minimal','filled']}
          onChange={v=>setTweak('chartStyle',v)}/>
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
