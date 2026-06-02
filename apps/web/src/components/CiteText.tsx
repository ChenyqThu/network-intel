/* {{cite:N}} → clickable superscripts that jump to the cited item card. */
import { parseCites } from '../lib/intel';
import { jumpTo } from '../lib/jump';

export function CiteText({ text }: { text: string }) {
  const tokens = parseCites(text);
  return (
    <>
      {tokens.map((tok, i) =>
        tok.kind === 'cite' ? (
          <sup
            key={i}
            className="sup"
            role="link"
            tabIndex={0}
            onClick={() => jumpTo('item-' + tok.n)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') jumpTo('item-' + tok.n);
            }}
          >
            {tok.n}
          </sup>
        ) : (
          <span key={i}>{tok.value}</span>
        ),
      )}
    </>
  );
}
