import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../App';

/**
 * Render smoke: with the API unavailable in jsdom, the client falls back to
 * the bundled contract fixtures. We assert the lead, an omada_self impact pill
 * (待修复), the weekly strategy block, and a citation line all render.
 */
function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  // Force offline fixture fallback regardless of environment.
  globalThis.fetch = (() =>
    Promise.reject(new Error('offline'))) as typeof fetch;
});

describe('App render smoke (fixtures)', () => {
  it('home (daily) renders the lead + a citation line', async () => {
    renderAt('/');
    // Lead eyebrow
    expect(await screen.findByText('Opus 策展')).toBeInTheDocument();
    // Citation line: 查看原文 appears on every item card
    await waitFor(() =>
      expect(screen.getAllByText('查看原文').length).toBeGreaterThan(0),
    );
  });

  it('weekly renders the strategy block + an omada_self 待修复 pill', async () => {
    renderAt('/weekly');
    // Strategy block badge + title
    expect(await screen.findByText('OPUS 策展')).toBeInTheDocument();
    // appears in the strategy block title and the sidebar TOC
    expect(screen.getAllByText('市场策略洞察').length).toBeGreaterThan(0);
    // omada_self impact pill (needs_fix -> 待修复)
    await waitFor(() =>
      expect(screen.getAllByText('待修复').length).toBeGreaterThan(0),
    );
    // optimal-confirm strength pill present (omada_self strength_confirm)
    expect(screen.getAllByText('优势确认').length).toBeGreaterThan(0);
  });

  it('archive page renders its filters and rows', async () => {
    renderAt('/archive');
    expect(await screen.findByText('历史报告检索')).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText('搜索报告标题、摘要…'),
    ).toBeInTheDocument();
  });

  it('all-items page renders the stream', async () => {
    renderAt('/items');
    expect(await screen.findByText('情报条目流')).toBeInTheDocument();
  });
});
