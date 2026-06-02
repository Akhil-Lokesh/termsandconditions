import {
  createElement,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ElementType,
  type ReactNode,
} from 'react';

/**
 * Scroll-triggered reveal. Elements start hidden (offset + blurred) and animate
 * in once they enter the viewport — replacing the old on-load `animate-slide-up`
 * which fired everything before you ever scrolled to it.
 *
 * Implementation notes:
 * - One shared IntersectionObserver for the whole page (cheaper than one each).
 * - Reveals once, then unobserves.
 * - Uses CSS `animation` with `fill-mode: backwards` (see globals.css) so the
 *   resting state stays `transform: none` — that keeps `.card-interactive:hover`
 *   lift working after the entrance finishes.
 * - Honors `prefers-reduced-motion`: the CSS guards the hidden state behind a
 *   media query, so reduced-motion users just see static content.
 */

export type RevealVariant = 'up' | 'scale' | 'left' | 'right' | 'rail';

interface RevealProps {
  as?: ElementType;
  variant?: RevealVariant;
  /** stagger delay in ms */
  delay?: number;
  className?: string;
  style?: CSSProperties;
  children?: ReactNode;
  [key: string]: unknown;
}

const subscribers = new Map<Element, () => void>();
let sharedObserver: IntersectionObserver | null = null;

function getObserver(): IntersectionObserver | null {
  if (typeof IntersectionObserver === 'undefined') return null;
  if (!sharedObserver) {
    sharedObserver = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            subscribers.get(entry.target)?.();
            sharedObserver?.unobserve(entry.target);
            subscribers.delete(entry.target);
          }
        }
      },
      { threshold: 0.12, rootMargin: '0px 0px -8% 0px' },
    );
  }
  return sharedObserver;
}

export function Reveal({
  as = 'div',
  variant = 'up',
  delay = 0,
  className,
  style,
  children,
  ...rest
}: RevealProps) {
  const ref = useRef<HTMLElement | null>(null);
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = getObserver();
    if (!observer) {
      setRevealed(true);
      return;
    }
    const reveal = () => setRevealed(true);
    subscribers.set(el, reveal);
    observer.observe(el);
    return () => {
      observer.unobserve(el);
      subscribers.delete(el);
    };
  }, []);

  return createElement(
    as,
    {
      ref,
      'data-reveal': variant,
      'data-revealed': revealed ? 'true' : 'false',
      className,
      style: { ...style, '--reveal-delay': `${delay}ms` } as CSSProperties,
      ...rest,
    },
    children,
  );
}
