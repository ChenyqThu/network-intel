/* ============================================================
   Network Intel DS — app shell
   Top bar (brand + lang + theme), sticky TOC with scroll-spy,
   hero overview, section assembly, footer. Persists theme +
   lang to localStorage.
   ============================================================ */

function useToc(ids) {
  const [active,setActive] = useState(ids[0]);
  useEffect(()=>{
    const obs = new IntersectionObserver((entries)=>{
      const vis = entries.filter(e=>e.isIntersecting).sort((a,b)=>a.boundingClientRect.top-b.boundingClientRect.top);
      if (vis[0]) setActive(vis[0].target.id);
    }, { rootMargin:'-72px 0px -65% 0px', threshold:0 });
    ids.forEach(id=>{ const el=document.getElementById(id); if(el) obs.observe(el); });
    return ()=>obs.disconnect();
  },[ids.join(',')]);
  return active;
}

function jumpTo(id){
  const el = document.getElementById(id); if(!el) return;
  const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const y = el.getBoundingClientRect().top + window.pageYOffset - 78;
  window.scrollTo({ top:y, behavior:reduce?'auto':'smooth' });
}

const SECTIONS = [
  ["overview","overview"],["color","color"],["type","type"],["space","space"],
  ["elevation","elevation"],["motion","motion"],["icon","icon"],["comp","comp"],
  ["states","states"],["skeleton","skeleton"],["responsive","responsive"],["i18n","i18n"],
];

function App() {
  const [lang,setLang] = useState(()=>{ try{ return localStorage.getItem('nids-lang')||'zh'; }catch(e){ return 'zh'; } });
  const [theme,setTheme] = useState(()=>{
    try{ const s=localStorage.getItem('nids-theme'); if(s) return s; }catch(e){}
    return (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
  });
  useEffect(()=>{ document.documentElement.setAttribute('data-theme',theme); try{ localStorage.setItem('nids-theme',theme); }catch(e){} },[theme]);
  useEffect(()=>{ try{ localStorage.setItem('nids-lang',lang); }catch(e){} document.documentElement.setAttribute('lang', lang==='en'?'en':'zh-CN'); },[lang]);

  const t = (k)=> window.dsT(lang,k);
  const ids = SECTIONS.map(s=>s[1]);
  const active = useToc(ids);

  return (
    <window.LangCtx.Provider value={lang}>
      <header className="ds-top">
        <div className="ds-brand" onClick={()=>window.scrollTo({top:0,behavior:'smooth'})}>
          <BrandMark/>
          <div>
            <div className="nm">Network <span className="g">Intel</span></div>
            <div className="sub">{t('brand.sub')}</div>
          </div>
        </div>
        <span className="ds-ver">{t('brand.ver')}</span>
        <span className="ds-top-spacer"/>
        <div className="seg-ctrl" role="group" aria-label={t('ui.lang')}>
          <button className={lang==='zh'?'on':''} onClick={()=>setLang('zh')}>中</button>
          <button className={lang==='en'?'on':''} onClick={()=>setLang('en')}>EN</button>
        </div>
        <button className="icon-btn" onClick={()=>setTheme(theme==='dark'?'light':'dark')} title={t('ui.theme')} aria-label={t('ui.theme')}>
          <Icon name={theme==='dark'?'sun':'moon'} size={18}/>
        </button>
      </header>

      <div className="ds-body">
        <nav className="ds-toc">
          <div className="toc-h">{t('ui.contents')}</div>
          {SECTIONS.map(([key,id],i)=>(
            <button key={id} className={"toc-link"+(active===id?' active':'')} onClick={()=>jumpTo(id)}>
              <span className="ti">{String(i).padStart(2,'0')}</span>{t('toc.'+key)}
            </button>
          ))}
          <div className="toc-div"/>
          <a className="toc-link" href="../index.html"><span className="ti"><Icon name="external" size={12}/></span>{t('foot.live')}</a>
        </nav>

        <main className="ds-main">
          <section className="ds-hero" id="overview">
            <div className="eye">{t('hero.eye')}</div>
            <h1>{t('hero.title_a')}<span className="g">{t('hero.title_b')}</span></h1>
            <p>{t('hero.desc')}</p>
            <div className="meta">
              {t('hero.chips').map((c,i)=>(<span className="hero-chip" key={i}><span className="d"/>{c}</span>))}
            </div>
          </section>

          <ColorSection/>
          <TypeSection/>
          <SpaceSection/>
          <ElevationSection/>
          <MotionSection/>
          <IconSection/>
          <ComponentsSection/>
          <StatesSection/>
          <SkeletonSection/>
          <ResponsiveSection/>
          <I18nSection/>

          <footer className="ds-foot">
            <div>
              <div className="fb">{t('foot.name')}</div>
              <p className="fn">{t('foot.note')}</p>
            </div>
            <a className="hero-chip" href="../index.html"><Icon name="external" size={13}/>{t('foot.live')}</a>
          </footer>
        </main>
      </div>
    </window.LangCtx.Provider>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
