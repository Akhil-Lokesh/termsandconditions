import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { api } from '@/services/api';
import type { FeedbackPayload, FeedbackResponse } from '@/types';

/**
 * Storage key prefix for tracking submitted feedback per anomaly.
 * Used so users don't see the feedback prompt again after a refresh.
 */
const FEEDBACK_STORAGE_PREFIX = 'tc:feedback-submitted:';

export const feedbackStorageKey = (anomalyId: string): string =>
  `${FEEDBACK_STORAGE_PREFIX}${anomalyId}`;

/**
 * Check whether the user has already submitted feedback for an anomaly.
 * Read once per render — does not subscribe to storage events.
 */
export const hasSubmittedFeedback = (anomalyId: string): boolean => {
  try {
    return localStorage.getItem(feedbackStorageKey(anomalyId)) !== null;
  } catch {
    // localStorage can throw in private-mode / disabled contexts — fail open.
    return false;
  }
};

/**
 * Persist that the user submitted feedback for this anomaly.
 * Stores the user_action so we can show contextual UI ("you marked this helpful").
 */
export const markFeedbackSubmitted = (
  anomalyId: string,
  action: FeedbackPayload['user_action']
): void => {
  try {
    localStorage.setItem(
      feedbackStorageKey(anomalyId),
      JSON.stringify({ action, ts: new Date().toISOString() })
    );
  } catch {
    // Storage unavailable — ignore. UI will fall back to in-memory state.
  }
};

/**
 * Retrieve the previously-submitted action for an anomaly, if any.
 */
export const getSubmittedFeedbackAction = (
  anomalyId: string
): FeedbackPayload['user_action'] | null => {
  try {
    const raw = localStorage.getItem(feedbackStorageKey(anomalyId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { action?: FeedbackPayload['user_action'] };
    return parsed?.action ?? null;
  } catch {
    return null;
  }
};

interface SubmitFeedbackArgs {
  anomalyId: string;
  payload: FeedbackPayload;
}

/**
 * useFeedback — TanStack Query mutation for submitting anomaly feedback.
 *
 * On success: marks the anomaly as "feedback submitted" in localStorage, shows
 * a toast, and invalidates anomaly queries so cached state can refresh.
 *
 * On error: shows an error toast. Does NOT mark the anomaly as submitted, so
 * the user can retry.
 */
export const useFeedback = () => {
  const queryClient = useQueryClient();

  const mutation = useMutation<FeedbackResponse, unknown, SubmitFeedbackArgs>({
    mutationFn: ({ anomalyId, payload }) => api.submitFeedback(anomalyId, payload),
    onSuccess: (_data, variables) => {
      markFeedbackSubmitted(variables.anomalyId, variables.payload.user_action);
      toast.success('Thanks — your feedback was recorded.');
      // Invalidate any cached anomaly state so re-renders pick up the new
      // submitted-feedback flag (driven by localStorage in the buttons).
      queryClient.invalidateQueries({ queryKey: ['anomalies'] });
      queryClient.invalidateQueries({ queryKey: ['anomaly-report'] });
    },
    onError: (error: unknown) => {
      const e = error as { message?: string; response?: { data?: { detail?: string } } };
      const message =
        e?.message ||
        e?.response?.data?.detail ||
        'Failed to submit feedback. Please try again.';
      toast.error(message);
    },
  });

  return {
    submitFeedback: mutation.mutate,
    submitFeedbackAsync: mutation.mutateAsync,
    isLoading: mutation.isPending,
    isSuccess: mutation.isSuccess,
    isError: mutation.isError,
  };
};
