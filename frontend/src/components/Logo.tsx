/**
 * T&C Analyzer logo — a contract page being scanned, with one clause "flagged".
 * Monoline glyph drawn in currentColor so it sits on the gradient tile in the
 * header or stands alone. Reads cleanly down to favicon size.
 */

interface LogoMarkProps {
  className?: string;
}

/** The glyph only (currentColor). Wrap it in a tile for the header lockup. */
export const LogoMark = ({ className = 'h-5 w-5' }: LogoMarkProps) => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.75}
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-hidden="true"
  >
    {/* contract page with a folded corner */}
    <path d="M6 3h7l5 5v12.5a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z" />
    <path d="M13 3v5h5" />
    {/* clause lines — the middle one is the flagged clause (drawn bold) */}
    <path d="M8.5 12h4" opacity={0.55} />
    <path d="M8.5 15.5h7" strokeWidth={2.5} />
    <path d="M8.5 19h4" opacity={0.55} />
  </svg>
);

interface LogoProps {
  /** Accepted for API compatibility; the wordmark is always rendered. */
  showWordmark?: boolean;
  className?: string;
}

/** Text-only wordmark. "T&C" carries the brand accent; no icon. */
export const Logo = ({ className = '' }: LogoProps) => (
  <span
    className={`font-display font-bold text-lg lg:text-xl tracking-tight ${className}`}
  >
    <span className="text-primary">T&amp;C</span>{' '}
    <span className="text-foreground">Analyzer</span>
  </span>
);
