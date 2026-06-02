import '@testing-library/jest-dom/vitest';

// jsdom lacks matchMedia; provide a no-op so theme + jump code paths run.
if (!window.matchMedia) {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
}

// jsdom lacks scrollTo.
if (!window.scrollTo) {
  window.scrollTo = (() => {}) as typeof window.scrollTo;
}
