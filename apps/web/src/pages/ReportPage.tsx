/* ============================================================
   ReportPage — Home (/) + /daily + /weekly.
   Home shows the daily/weekly segmented toggle (defaults daily);
   /daily and /weekly bind ReportView to a fixed cadence.
   ============================================================ */
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ReportView } from '../components/ReportView';
import { useAsync } from '../lib/useAsync';
import { fetchLatestReport, fetchReport, fetchArchive, usingFixtures } from '../api/client';
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
  const { id: reportId } = useParams();
  const [homeType, setHomeType] = useState<'daily' | 'weekly'>('daily');
  const cadence = mode === 'home' ? homeType : mode;

  // /r/:id deep-links a specific report (e.g. the email "在浏览器中打开" link), so a
  // link always opens that exact report, not the latest of its cadence.
  const report = useAsync(
    () => (reportId ? fetchReport(reportId) : fetchLatestReport(cadence)),
    [reportId, cadence],
  );
  const archive = useAsync(() => fetchArchive(), []);
  const type = reportId ? (report.data?.type ?? cadence) : cadence;

  const openReport = (id: string) => navigate('/r/' + encodeURIComponent(id));

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
      onSelectType={mode === 'home' && !reportId ? setHomeType : undefined}
      showToggle={mode === 'home' && !reportId}
      twoCol={tweaks.homeLayout === 'two'}
      chartStyle={tweaks.chartStyle}
      archive={archive.data || []}
      onOpen={openReport}
      offline={usingFixtures}
    />
  );
}
