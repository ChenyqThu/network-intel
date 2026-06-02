/* ============================================================
   Network Intel — app shell
   Topbar (brand + nav + date + theme toggle) · real routes ·
   theme (system/light/dark) + density + primary color resolution ·
   footer (email/archive/items/PRD) · Tweaks panel.
   ============================================================ */
import { useEffect, useState } from 'react';
import {
  NavLink,
  Route,
  Routes,
  useNavigate,
  useLocation,
} from 'react-router-dom';
import { BrandMark, Icon } from './components/Icon';
import { useTweaks, TweaksPanel, type Tweaks } from './components/TweaksPanel';
import { ReportPage } from './pages/ReportPage';
import { ArchivePage } from './pages/ArchivePage';
import { AllItemsPage } from './pages/AllItemsPage';

const TWEAK_DEFAULTS: Tweaks = {
  primaryColor: '#0C6151',
  density: 'regular',
  homeLayout: 'two',
  chartStyle: 'minimal',
  theme: 'system',
};

function useSystemDark(): boolean {
  const initial =
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-color-scheme: dark)').matches;
  const [dark, setDark] = useState(initial);
  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const fn = (e: MediaQueryListEvent) => setDark(e.matches);
    mq.addEventListener?.('change', fn);
    return () => mq.removeEventListener?.('change', fn);
  }, []);
  return dark;
}

export default function App() {
  const [tweaks, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const navigate = useNavigate();
  const location = useLocation();
  const sysDark = useSystemDark();

  const resolvedTheme =
    tweaks.theme === 'system' ? (sysDark ? 'dark' : 'light') : tweaks.theme;

  useEffect(() => {
    const r = document.documentElement;
    r.setAttribute('data-theme', resolvedTheme);
    r.setAttribute('data-density', tweaks.density);
    r.style.setProperty('--tw-primary', tweaks.primaryColor);
  }, [resolvedTheme, tweaks.density, tweaks.primaryColor]);

  // Scroll to top on route change.
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior });
  }, [location.pathname]);

  const toggleTheme = () =>
    setTweak('theme', resolvedTheme === 'dark' ? 'light' : 'dark');

  const navClass = ({ isActive }: { isActive: boolean }) =>
    'nav-link' + (isActive ? ' active' : '');

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand" onClick={() => navigate('/')}>
          <BrandMark />
          <span className="brand-name">
            Network <span className="intel">Intel</span>
          </span>
          <span className="brand-tag">内部情报</span>
        </div>
        <nav className="nav">
          <NavLink to="/" end className={navClass}>
            最新报告
          </NavLink>
          <NavLink to="/daily" className={navClass}>
            日报
          </NavLink>
          <NavLink to="/weekly" className={navClass}>
            周报
          </NavLink>
          <NavLink to="/archive" className={navClass}>
            归档检索
          </NavLink>
          <NavLink to="/items" className={navClass}>
            全部条目
          </NavLink>
        </nav>
        <div className="topbar-spacer" />
        <span className="nav-date tnum">2026-06-01 · 09:30 PT</span>
        <button
          className="icon-btn"
          onClick={toggleTheme}
          title={resolvedTheme === 'dark' ? '切换亮色' : '切换暗色'}
          aria-label="切换主题"
        >
          <Icon name={resolvedTheme === 'dark' ? 'sun' : 'moon'} size={18} />
        </button>
      </header>

      <main className="page">
        <Routes>
          <Route path="/" element={<ReportPage mode="home" tweaks={tweaks} />} />
          <Route path="/daily" element={<ReportPage mode="daily" tweaks={tweaks} />} />
          <Route path="/weekly" element={<ReportPage mode="weekly" tweaks={tweaks} />} />
          <Route path="/archive" element={<ArchivePage />} />
          <Route path="/items" element={<AllItemsPage />} />
          <Route path="*" element={<ReportPage mode="home" tweaks={tweaks} />} />
        </Routes>
      </main>

      <footer className="foot">
        <div className="wrap">
          <div>
            <div className="foot-brand">Network Intel</div>
            <p className="foot-note">
              内部竞品 &amp; 舆情情报 · 仅限 TP-Link 网络产品团队。每条结论可一键溯源验证——这是策展报告与普通信息聚合的本质区别。数据融合：UNIFI_CHANNELS
              Supabase（一手官方）+ 个人情报流（Reddit / YouTube）。
            </p>
          </div>
          <div className="foot-links">
            <a
              href="/api/reports/2026-06-01-daily/email"
              target="_blank"
              rel="noopener noreferrer"
            >
              邮件版 ↗
            </a>
            <a
              role="link"
              tabIndex={0}
              onClick={() => navigate('/archive')}
              onKeyDown={(e) => {
                if (e.key === 'Enter') navigate('/archive');
              }}
            >
              归档
            </a>
            <a
              role="link"
              tabIndex={0}
              onClick={() => navigate('/items')}
              onKeyDown={(e) => {
                if (e.key === 'Enter') navigate('/items');
              }}
            >
              全部条目
            </a>
            <a
              href="https://www.feishu.cn/docx/TXrNdLo7uoc8mfx9NIec45Z7n8c"
              target="_blank"
              rel="noopener noreferrer"
            >
              PRD ↗
            </a>
          </div>
        </div>
      </footer>

      <TweaksPanel title="Tweaks" tweaks={tweaks} setTweak={setTweak} />
    </div>
  );
}
