/** The DataNova "spark" — a four-point nova with a small companion star. */
export function NovaMark({
  size = 24,
  className = "",
  animate = false,
}: {
  size?: number;
  className?: string;
  animate?: boolean;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="novaGrad" x1="2" y1="2" x2="22" y2="22">
          <stop offset="0" stopColor="#F6B01E" />
          <stop offset="0.55" stopColor="#E23AA3" />
          <stop offset="1" stopColor="#A31672" />
        </linearGradient>
      </defs>
      <path
        d="M12 0.8c0.8 6 5.2 10.4 11.2 11.2-6 0.8-10.4 5.2-11.2 11.2-0.8-6-5.2-10.4-11.2-11.2 6-0.8 10.4-5.2 11.2-11.2Z"
        fill="url(#novaGrad)"
        className={animate ? "origin-center animate-spark-pulse" : ""}
      />
      <circle cx="19.5" cy="4.5" r="1.7" fill="#F6B01E" />
    </svg>
  );
}

export function Wordmark({
  className = "",
  markSize = 22,
}: {
  className?: string;
  markSize?: number;
}) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <NovaMark size={markSize} />
      <span className="font-display text-[17px] font-bold tracking-tight text-ink">
        Data<span className="text-nova-600">Nova</span>
      </span>
    </span>
  );
}
