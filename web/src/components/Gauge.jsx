// SVG scam-pressure gauge: a 240° arc with a needle that swings as pressure
// climbs and glows red once it crosses the hand-off threshold.
const START = -210; // degrees
const SWEEP = 240;

export default function Gauge({ pressure, threshold }) {
  const frac = Math.max(0, Math.min(1, threshold ? pressure / threshold : 0));
  const armed = pressure >= threshold;
  const angle = START + frac * SWEEP;
  const cx = 130;
  const cy = 130;
  const r = 96;

  return (
    <div className={`gauge ${armed ? 'gauge--armed' : ''}`}>
      <svg viewBox="0 0 260 200" width="100%" role="img" aria-label={`scam pressure ${Math.round(frac * 100)} percent`}>
        <path d={arc(cx, cy, r, START, START + SWEEP)} className="gauge__track" fill="none" />
        <path d={arc(cx, cy, r, START, angle)} className="gauge__fill" fill="none" />
        {/* threshold tick */}
        <line
          {...tick(cx, cy, r, START + SWEEP)}
          className="gauge__threshold"
        />
        {/* needle */}
        <line
          x1={cx}
          y1={cy}
          x2={cx + (r - 14) * Math.cos((angle * Math.PI) / 180)}
          y2={cy + (r - 14) * Math.sin((angle * Math.PI) / 180)}
          className="gauge__needle"
        />
        <circle cx={cx} cy={cy} r="7" className="gauge__hub" />
      </svg>
      <div className="gauge__readout">
        <span className="gauge__pct">{Math.round(frac * 100)}<small>%</small></span>
        <span className="gauge__label">{armed ? 'THRESHOLD CROSSED' : 'scam pressure'}</span>
      </div>
    </div>
  );
}

function polar(cx, cy, r, deg) {
  const rad = (deg * Math.PI) / 180;
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)];
}

function arc(cx, cy, r, a0, a1) {
  const [x0, y0] = polar(cx, cy, r, a0);
  const [x1, y1] = polar(cx, cy, r, a1);
  const large = a1 - a0 > 180 ? 1 : 0;
  return `M ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1}`;
}

function tick(cx, cy, r, deg) {
  const [x1, y1] = polar(cx, cy, r - 12, deg);
  const [x2, y2] = polar(cx, cy, r + 6, deg);
  return { x1, y1, x2, y2 };
}
