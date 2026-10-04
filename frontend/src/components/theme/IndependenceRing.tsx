interface IndependenceRingProps {
  score: number;
  size?: number;
}

export function IndependenceRing({ score, size = 96 }: IndependenceRingProps) {
  const normalizedScore = Math.max(0, Math.min(100, Math.round(score)));
  const strokeWidth = 9;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  return (
    <div
      className="relative inline-grid shrink-0 place-items-center"
      role="img"
      aria-label={`Independence score ${normalizedScore} percent`}
      style={{ width: size, height: size }}
    >
      <svg aria-hidden="true" className="-rotate-90" width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--lilac)" strokeWidth={strokeWidth} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--primary)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - normalizedScore / 100)}
        />
      </svg>
      <span className="absolute font-display text-xl font-extrabold tabular-nums">{normalizedScore}%</span>
    </div>
  );
}
