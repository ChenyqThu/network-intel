/* ============================================================
   ReportPage — Home (/) + /daily + /weekly.
   Home shows the daily/weekly segmented toggle (defaults daily);
   /daily and /weekly bind ReportView to a fixed cadence.
   ============================================================ */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ReportView } from '../components/ReportView';
import { useAsync } from '../lib/useAsync';
import { fetchLatestReport, fetchArchive, usingFixtures } from '../api/client';
import type { Tweaks } from '../components/TweaksPanel';

export function ReportPage({
  mode,
  tweaks,
}: {
  /** 'home' = segmented toggle; 'daily'/'weekly' = fixed cadence */
  mode: 'home' | 'daily' | 'weekly';
  tweaks: Tweaks;
}) {
  const navigate = useNavigate();
  const [homeType, setHomeType] = useState<'daily' | 'weekly'>('daily');
  const type = mode === 'home' ? homeType : mode;

  const report = useAsync(() => fetchLatestReport(type), [type]);
  const archive = useAsync(() => fetchArchive(), []);

  const openReport = (id: string) => {
    const a = archive.data?.find((x) => x.id === id);
    if (a) {
      // route to the matching cadence page so the latest of that type shows
      navigate(a.type === 'weekly' ? '/weekly' : '/daily');
    }
  };

  if (report.loading) {
    return (
      <div className="wrap">
        <div className="state-msg">
          <span className="spinner" />
          加载报告…
        </div>
      </div>
    );
  }
  if (!report.data) {
    return (
      <div className="wrap">
        <div className="state-msg">报告加载失败。</div>
      </div>
    );
  }

  return (
    <ReportView
      report={report.data}
      type={type}
      onSelectType={mode === 'home' ? setHomeType : undefined}
      showToggle={mode === 'home'}
      twoCol={tweaks.homeLayout === 'two'}
      chartStyle={tweaks.chartStyle}
      archive={archive.data || []}
      onOpen={openReport}
      offline={usingFixtures}
    />
  );
}
