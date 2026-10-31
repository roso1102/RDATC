// Range-only radar view. The radar reports distance, not bearing, so targets sit on the centre
// line at their measured range, with a faint arc marking "somewhere at this distance".

export type RadarReading = {
  target_state: string; moving: boolean; stationary: boolean; presence: boolean;
  moving_distance_cm: number; stationary_distance_cm: number; sequence: number;
};

const CX = 160, CY = 190, R = 170, MAX_M = 6, HALF_FOV = Math.PI / 3;
const point = (radius: number, angle: number) =>
  [CX + radius * Math.sin(angle), CY - radius * Math.cos(angle)] as const;
const arc = (radius: number) => {
  const [x1, y1] = point(radius, -HALF_FOV), [x2, y2] = point(radius, HALF_FOV);
  return `M ${x1} ${y1} A ${radius} ${radius} 0 0 1 ${x2} ${y2}`;
};
const FAN = `M ${CX} ${CY} L ${point(R, -HALF_FOV).join(' ')} A ${R} ${R} 0 0 1 ${point(R, HALF_FOV).join(' ')} Z`;
const toRadius = (cm: number) => Math.min(cm / 100, MAX_M) / MAX_M * R;

export function RadarView({ reading, live }: { reading: RadarReading | null; live: boolean }) {
  const targets = reading ? [
    reading.moving && { kind: 'moving', cm: reading.moving_distance_cm },
    reading.stationary && { kind: 'still', cm: reading.stationary_distance_cm },
  ].filter(Boolean) as { kind: string; cm: number }[] : [];

  return <svg className={`radar ${live ? 'live' : 'idle'}`} viewBox="0 0 320 200" role="img"
    aria-label={targets.length ? `Radar targets at ${targets.map(t => `${(t.cm / 100).toFixed(1)} m`).join(' and ')}` : 'No radar target'}>
    <defs>
      <clipPath id="radar-fan"><path d={FAN} /></clipPath>
      <radialGradient id="radar-fill" cx={CX} cy={CY} r={R} gradientUnits="userSpaceOnUse">
        <stop offset="0" stopColor="var(--radar)" stopOpacity="0.10" />
        <stop offset="1" stopColor="var(--radar)" stopOpacity="0.02" />
      </radialGradient>
    </defs>
    <path d={FAN} className="radar-fan" />
    {[1, 2, 3, 4, 5, 6].map(m => <path key={m} d={arc(m / MAX_M * R)} className="radar-ring" />)}
    {[2, 4, 6].map(m => <text key={m} x={CX + 5} y={CY - m / MAX_M * R + 11} className="radar-label">{m} m</text>)}
    <line x1={CX} y1={CY} x2={CX} y2={CY - R} className="radar-axis" />
    <g clipPath="url(#radar-fan)">
      {live && [0, 1, 2].map(i => <circle key={i} cx={CX} cy={CY} r={R} className="radar-pulse"
        style={{ animationDelay: `${i * 0.9}s` }} />)}
    </g>
    {targets.map(target => <path key={`band-${target.kind}`} d={arc(toRadius(target.cm))}
      className={`radar-band ${target.kind}`} />)}
    {targets.map(target => <g key={target.kind} className={`radar-target ${target.kind}`}
      style={{ transform: `translate(${CX}px, ${CY - toRadius(target.cm)}px)` }}>
      {target.kind === 'moving' && <circle r="6" className="radar-ping" />}
      <circle r="5" className="radar-dot" />
    </g>)}
    <circle cx={CX} cy={CY} r="4" className="radar-origin" />
  </svg>;
}

export function radarSummary(reading: RadarReading | null) {
  if (!reading || !reading.presence) return 'No one in range';
  const metres = (cm: number) => `${(cm / 100).toFixed(1)} m`;
  if (reading.moving && reading.stationary)
    return `Movement at ${metres(reading.moving_distance_cm)} · still target at ${metres(reading.stationary_distance_cm)}`;
  if (reading.moving) return `Movement at ${metres(reading.moving_distance_cm)}`;
  return `Someone still at ${metres(reading.stationary_distance_cm)}`;
}
