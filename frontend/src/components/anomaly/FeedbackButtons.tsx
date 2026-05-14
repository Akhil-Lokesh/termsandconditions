import { useMemo, useState } from 'react';
import { CheckCircle2, ThumbsUp, ThumbsDown, AlertTriangle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  useFeedback,
  hasSubmittedFeedback,
  getSubmittedFeedbackAction,
} from '@/hooks/useFeedback';
import type { FeedbackPayload, FeedbackUserAction } from '@/types';

type SuggestedSeverity = 'critical' | 'high' | 'medium' | 'low';

interface FeedbackButtonsProps {
  anomalyId: string;
  /** Current severity of the anomaly — used so the "wrong severity" form can
   *  pre-select something other than the current value. */
  currentSeverity?: 'critical' | 'high' | 'medium' | 'low';
  /** Confidence at detection time. The backend FeedbackRequest requires this
   *  in [0, 1]. We don't have access to the raw calibrated value in the
   *  current Anomaly type, so we pass a sensible default. */
  confidenceAtDetection?: number;
}

const SEVERITY_OPTIONS: ReadonlyArray<{ value: SuggestedSeverity; label: string }> = [
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
];

export const FeedbackButtons = ({
  anomalyId,
  currentSeverity,
  confidenceAtDetection = 0.5,
}: FeedbackButtonsProps) => {
  const { submitFeedback, isLoading } = useFeedback();

  // localStorage-driven submitted state (persists across refresh).
  // We capture it once on mount, then track an in-memory override so the
  // post-submit UI reflects the just-submitted action immediately.
  const initialSubmittedAction = useMemo(
    () => (hasSubmittedFeedback(anomalyId) ? getSubmittedFeedbackAction(anomalyId) : null),
    [anomalyId]
  );
  const [localSubmittedAction, setLocalSubmittedAction] = useState<FeedbackUserAction | null>(
    initialSubmittedAction
  );

  // Wrong-severity dialog state.
  const [dialogOpen, setDialogOpen] = useState(false);
  const [suggestedSeverity, setSuggestedSeverity] = useState<SuggestedSeverity>(() => {
    // Default to a severity different from the current one when possible.
    if (currentSeverity === 'critical') return 'high';
    if (currentSeverity === 'high') return 'medium';
    if (currentSeverity === 'medium') return 'low';
    return 'medium';
  });
  const [commentText, setCommentText] = useState('');

  const submit = (action: FeedbackUserAction, extra?: Partial<FeedbackPayload>) => {
    const payload: FeedbackPayload = {
      user_action: action,
      confidence_at_detection: confidenceAtDetection,
      ...extra,
    };
    submitFeedback(
      { anomalyId, payload },
      {
        onSuccess: () => {
          setLocalSubmittedAction(action);
          setDialogOpen(false);
          setCommentText('');
        },
      }
    );
  };

  const handleHelpful = () => submit('helpful');
  const handleDismiss = () => submit('dismiss');

  const handleSubmitWrongSeverity = () => {
    // The backend FeedbackRequest only accepts a fixed set of user_action
    // strings, and there's no first-class "wrong severity" action. We encode
    // the suggested severity into feedback_text so it's persisted with the
    // FeedbackEvent for later calibrator inspection, and use 'dismiss' as the
    // closest semantic match (user is signaling the call was wrong).
    const composedText = [
      `[suggested_severity=${suggestedSeverity}]`,
      commentText.trim() ? commentText.trim() : null,
    ]
      .filter(Boolean)
      .join(' ');

    submit('dismiss', {
      feedback_text: composedText,
      suggested_severity: suggestedSeverity,
    });
  };

  // ── Submitted state ──────────────────────────────────────────────────
  if (localSubmittedAction) {
    return (
      <div className="flex items-center gap-2 pt-3 lg:pt-4 border-t border-border/30 text-xs lg:text-sm text-muted-foreground">
        <CheckCircle2 className="h-3.5 w-3.5 lg:h-4 lg:w-4 text-emerald-500" />
        <span className="font-mono uppercase tracking-wider text-[10px] lg:text-xs">
          Feedback recorded
        </span>
        <span className="ml-1 text-foreground/70">
          {localSubmittedAction === 'helpful' && '· marked helpful'}
          {localSubmittedAction === 'dismiss' && '· dismissed'}
          {localSubmittedAction === 'not_applicable' && '· not applicable'}
          {localSubmittedAction === 'acted_on' && '· acted on'}
        </span>
      </div>
    );
  }

  // ── Active feedback UI ───────────────────────────────────────────────
  return (
    <div className="pt-3 lg:pt-4 border-t border-border/30">
      <div className="flex items-center justify-between gap-2 mb-2 lg:mb-3">
        <span className="text-[10px] lg:text-xs font-mono uppercase tracking-wider text-muted-foreground">
          Was this useful?
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={isLoading}
          onClick={handleHelpful}
          className="h-8 lg:h-9 text-xs lg:text-sm gap-1.5 hover:bg-emerald-500/10 hover:text-emerald-500 hover:border-emerald-500/40"
          aria-label="Mark this anomaly as helpful"
        >
          {isLoading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <ThumbsUp className="h-3.5 w-3.5" />
          )}
          Helpful
        </Button>

        <Button
          variant="outline"
          size="sm"
          disabled={isLoading}
          onClick={handleDismiss}
          className="h-8 lg:h-9 text-xs lg:text-sm gap-1.5 hover:bg-muted hover:text-muted-foreground"
          aria-label="Dismiss this anomaly as not helpful"
        >
          {isLoading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <ThumbsDown className="h-3.5 w-3.5" />
          )}
          Not helpful
        </Button>

        <Button
          variant="outline"
          size="sm"
          disabled={isLoading}
          onClick={() => setDialogOpen(true)}
          className="h-8 lg:h-9 text-xs lg:text-sm gap-1.5 hover:bg-amber-500/10 hover:text-amber-500 hover:border-amber-500/40"
          aria-label="Report wrong severity"
        >
          <AlertTriangle className="h-3.5 w-3.5" />
          Wrong severity
        </Button>
      </div>

      {/* Wrong-severity dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Report wrong severity</DialogTitle>
            <DialogDescription>
              Tell us what severity you think this clause should be. This
              helps calibrate our detection over time.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
                Suggested severity
              </Label>
              <div className="flex flex-wrap gap-2">
                {SEVERITY_OPTIONS.map((opt) => {
                  const selected = suggestedSeverity === opt.value;
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setSuggestedSeverity(opt.value)}
                      className={
                        'h-9 px-3 text-xs rounded-md border transition-colors ' +
                        (selected
                          ? 'bg-primary/10 border-primary text-primary'
                          : 'border-border/60 text-foreground/70 hover:bg-muted/50')
                      }
                      aria-pressed={selected}
                    >
                      {opt.label}
                    </button>
                  );
                })}
              </div>
              {currentSeverity && (
                <p className="text-[10px] lg:text-xs text-muted-foreground">
                  Currently shown as{' '}
                  <span className="font-mono uppercase">{currentSeverity}</span>.
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label
                htmlFor="feedback-comment"
                className="text-xs font-mono uppercase tracking-wider text-muted-foreground"
              >
                Comment (optional)
              </Label>
              <Textarea
                id="feedback-comment"
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                placeholder="Why do you think the severity is wrong?"
                maxLength={500}
                rows={3}
                className="text-sm"
              />
              <p className="text-[10px] text-muted-foreground text-right">
                {commentText.length}/500
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setDialogOpen(false)}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button onClick={handleSubmitWrongSeverity} disabled={isLoading}>
              {isLoading ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Submitting...
                </>
              ) : (
                'Submit feedback'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
