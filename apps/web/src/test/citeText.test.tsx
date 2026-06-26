import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { CiteText } from '../components/CiteText';

/* Guards the user-critical contract: inline markdown and {{cite:N}} compose
   in the SAME run without interfering — citations stay clickable, **bold**
   renders, and a literal `**` only shows when there's no real emphasis. */
describe('CiteText: markdown + citation compose', () => {
  it('renders **bold** and a clickable cite from one string', () => {
    const { container } = render(
      <CiteText text="风险在于**确认在野利用**{{cite:3}}，需警惕" />,
    );
    const strong = container.querySelector('strong');
    expect(strong?.textContent).toBe('确认在野利用');

    const sup = container.querySelector('sup.sup');
    expect(sup?.textContent).toBe('3');
    expect(sup?.getAttribute('role')).toBe('link');

    // bold markers are consumed, not shown raw
    expect(container.textContent).not.toContain('**');
    expect(container.textContent).toBe('风险在于确认在野利用3，需警惕');
  });

  it('leaves plain prose (no markdown) untouched', () => {
    const { container } = render(<CiteText text="普通文本{{cite:1}}" />);
    expect(container.querySelector('strong')).toBeNull();
    expect(container.querySelector('sup.sup')?.textContent).toBe('1');
  });
});
