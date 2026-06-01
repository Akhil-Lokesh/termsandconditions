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
  /** When true, render the wordmark + tagline next to the mark. */
  showWordmark?: boolean;
  className?: string;
}

/** Full header lockup: gradient tile + glyph (+ optional wordmark). */
export const Logo = ({ showWordmark = true, className = '' }: LogoProps) => (
  <span className={`flex items-center gap-2.5 group ${className}`}>
    <span className="relative">
      <span className="absolute inset-0 bg-primary/25 blur-lg rounded-lg group-hover:bg-primary/40 transition-colors" />
      <span className="relative grid place-items-center bg-gradient-to-br from-primary to-accent text-primary-foreground rounded-lg h-8 w-8 lg:h-9 lg:w-9 ring-1 ring-primary/30">
        <LogoMark className="h-[18px] w-[18px] lg:h-5 lg:w-5" />
      </span>
    </span>
    {showWordmark && (
      <span className="flex flex-col leading-none">
        <span className="font-display font-bold text-base lg:text-lg tracking-tight text-foreground">
          T&amp;C Analyzer
        </span>
        <span className="text-[9px] lg:text-[10px] font-mono uppercase tracking-[0.18em] text-muted-foreground mt-0.5">
          Contract Risk Intelligence
        </span>
      </span>
    )}
  </span>
);
