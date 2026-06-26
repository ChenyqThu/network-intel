/* {{cite:N}} → clickable superscripts that jump to the cited item card.
   Plain-text runs between cites get light inline-markdown (**bold** / *italic*
   / `code`) — citation parsing (parseCites) stays the sole, separate first
   pass and is never touched by the markdown layer. */
import { parseCites, parseInlineMd } from '../lib/intel';
import { jumpTo } from '../lib/jump';

/** Render a plain text run with inline markdown emphasis. */
function InlineMd({ text }: { text: string }) {
  return (
    <>
      {parseInlineMd(text).map((n, i) => {
        if (n.kind === 'strong') return <strong key={i}>{n.value}</strong>;
        if (n.kind === 'em') return <em key={i}>{n.value}</em>;
        if (n.kind === 'code') return <code key={i}>{n.value}</code>;
        return <span key={i}>{n.value}</span>;
      })}
    </>
  );
}

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
          <InlineMd key={i} text={tok.value} />
        ),
      )}
    </>
  );
}
