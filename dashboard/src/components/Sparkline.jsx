const WIDTH = 120;
const HEIGHT = 32;

export default function Sparkline({ values, bandLower, bandUpper }) {
  if (!values || values.length < 2) {
    return <div className="sparkline-empty" aria-hidden="true" />;
  }

  const all = [...values, bandLower, bandUpper].filter((v) => typeof v === "number");
  const min = Math.min(...all);
  const max = Math.max(...all);
  const span = max - min || 1;
  const pad = span * 0.1;
  const lo = min - pad;
  const hi = max + pad;
  const range = hi - lo || 1;

  const step = WIDTH / (values.length - 1);
  const toY = (v) => HEIGHT - ((v - lo) / range) * HEIGHT;
  const points = values.map((v, i) => `${(i * step).toFixed(1)},${toY(v).toFixed(1)}`).join(" ");

  const hasBand = typeof bandLower === "number" && typeof bandUpper === "number";
  const bandTop = hasBand ? toY(bandUpper) : null;
  const bandHeight = hasBand ? Math.max(0, toY(bandLower) - toY(bandUpper)) : null;

  return (
    <svg
      className="sparkline"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      width={WIDTH}
      height={HEIGHT}
      preserveAspectRatio="none"
      role="img"
      aria-label="Recent trend"
    >
      {hasBand && (
        <rect x={0} y={bandTop} width={WIDTH} height={bandHeight} className="sparkline-band" />
      )}
      <polyline points={points} className="sparkline-line" fill="none" />
    </svg>
  );
}
