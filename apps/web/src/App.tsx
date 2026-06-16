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
import { AdminPage } from './pages/AdminPage';
import { UnsubscribePage } from './pages/UnsubscribePage';

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

/* Floating "back to top" — appears after scrolling past the fold. */
function BackToTop() {
  const [show, setShow] = useState(false);
  useEffect(() => {
    const onScroll = () => setShow(window.scrollY > 400);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  if (!show) return null;
  return (
    <button
      className="back-to-top"
      onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
      title="返回顶部"
      aria-label="返回顶部"
    >
      <Icon name="arrowUp" size={20} />
    </button>
  );
}

export default function App() {
  const [tweaks, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [menuOpen, setMenuOpen] = useState(false);
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

  // Scroll to top + close the mobile menu on route change.
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior });
    setMenuOpen(false);
  }, [location.pathname]);

  const toggleTheme = () =>
    setTweak('theme', resolvedTheme === 'dark' ? 'light' : 'dark');

  const navClass = ({ isActive }: { isActive: boolean }) =>
    'nav-link' + (isActive ? ' active' : '');

  // Admin review console renders standalone (full-screen, no public shell).
  if (location.pathname.startsWith('/admin')) {
    return <AdminPage />;
  }

  // Unsubscribe landing page (linked from the email footer) — also standalone.
  if (location.pathname.startsWith('/unsubscribe')) {
    return <UnsubscribePage />;
  }

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
          onClick={() => navigate('/admin')}
          title="审核台"
          aria-label="审核台"
        >
          <Icon name="inbox" size={18} />
        </button>
        <button
          className="icon-btn"
          onClick={toggleTheme}
          title={resolvedTheme === 'dark' ? '切换亮色' : '切换暗色'}
          aria-label="切换主题"
        >
          <Icon name={resolvedTheme === 'dark' ? 'sun' : 'moon'} size={18} />
        </button>
        <button
          className="icon-btn nav-toggle"
          onClick={() => setMenuOpen((v) => !v)}
          title="菜单"
          aria-label="菜单"
          aria-expanded={menuOpen}
        >
          <Icon name={menuOpen ? 'x' : 'menu'} size={18} />
        </button>
      </header>

      {menuOpen && (
        <div
          className="nav-drawer-mask"
          onClick={() => setMenuOpen(false)}
          aria-hidden="true"
        >
          <nav className="nav-drawer" onClick={(e) => e.stopPropagation()}>
            <NavLink to="/" end className={navClass} onClick={() => setMenuOpen(false)}>
              最新报告
            </NavLink>
            <NavLink to="/daily" className={navClass} onClick={() => setMenuOpen(false)}>
              日报
            </NavLink>
            <NavLink to="/weekly" className={navClass} onClick={() => setMenuOpen(false)}>
              周报
            </NavLink>
            <NavLink to="/archive" className={navClass} onClick={() => setMenuOpen(false)}>
              归档检索
            </NavLink>
            <NavLink to="/items" className={navClass} onClick={() => setMenuOpen(false)}>
              全部条目
            </NavLink>
            <div className="nav-drawer-div" />
            <a
              role="link"
              tabIndex={0}
              className="nav-link"
              onClick={() => {
                setMenuOpen(false);
                navigate('/admin');
              }}
            >
              审核台
            </a>
          </nav>
        </div>
      )}

      <main className="page">
        <Routes>
          <Route path="/" element={<ReportPage mode="home" tweaks={tweaks} />} />
          <Route path="/daily" element={<ReportPage mode="daily" tweaks={tweaks} />} />
          <Route path="/weekly" element={<ReportPage mode="weekly" tweaks={tweaks} />} />
          <Route path="/r/:id" element={<ReportPage mode="daily" tweaks={tweaks} />} />
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
              内部洞察情报 · 仅限 TP-Link 网络产品团队。覆盖竞品动态、自身舆情与行业趋势，每条结论可一键溯源验证——这是策展报告与普通信息聚合的本质区别。
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
          </div>
        </div>
      </footer>

      <BackToTop />
      <TweaksPanel title="Tweaks" tweaks={tweaks} setTweak={setTweak} />
    </div>
  );
}
