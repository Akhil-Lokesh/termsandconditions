# Bug Sweep Report — T&C Analyzer

_Multi-agent audit: 15 finders → 104 raw findings → **88 verified real** (16 refuted by adversarial verifiers) → 88 after dedupe._

**Severity:** 1 critical · 23 high · 27 medium · 37 low

---

## CRITICAL (1)

### C1. risk_level "Unknown" / "Critical" from backend white-screens the analysis page (RISK_META lookup returns undefined, then destructured)
- **File:** `frontend/src/components/analysis/RiskSummaryHeader.tsx:99-100` · **Category:** crash · **Finder:** x-contract · **Verifier confidence:** high
- **Impact:** AnalysisResults computes riskLevel as document.risk_level.toLowerCase() and passes it to RiskSummaryHeader, which does `const meta = RISK_META[riskLevel]; const { Icon } = meta;`. RISK_META only has keys analyzing|critical|high|medium|low. The upload background-task FAILURE path sets document.risk_level = "Unknown" (backend/app/api/v1/upload.py:309). With processing_status="anomaly_detection_failed", isAnalyzing is false, so AnalysisResults.tsx:34 returns "unknown" — NOT a RISK_META key — making `meta` undefined and `const { Icon } = meta` throw `TypeError: Cannot destructure property 'Icon' of 'undefined'`. The entire DocumentPage render tree throws and white-screens. This fires precisely when anomaly detection failed — exactly when the user opens the doc to see what happened. (Reanalyze sets risk_level="Critical" which lowercases to a valid key, so that path is safe; "Unknown" is the trigger.)
- **Evidence:** AnalysisResults.tsx:33-35: `if (document.risk_level) { return document.risk_level.toLowerCase() as 'critical' | 'high' | 'medium' | 'low'; }` ; RiskSummaryHeader.tsx:99-100: `const meta = RISK_META[riskLevel]; const { Icon } = meta;` ; upload.py:309 (failure path): `document.risk_level = "Unknown"`
- **Fix:** In AnalysisResults.getDocumentRiskLevel(), normalize/whitelist the lowercased value: `const lvl = document.risk_level.toLowerCase(); if (['critical','high','medium','low'].includes(lvl)) return lvl as ...;` and fall through to the anomaly-count heuristic otherwise. Alternatively make RiskSummaryHeader defensive: `const meta = RISK_META[riskLevel] ?? RISK_META.low;`. Best: have the backend failure path set a status the FE surfaces as an error banner rather than a fake risk_level.

## HIGH (23)

### H1. submit_feedback calls non-existent detector.collect_user_feedback() — every feedback POST returns 500
- **File:** `backend/app/api/v1/anomalies.py:908-912` · **Category:** crash · **Finder:** be-anomalies-api · **Verifier confidence:** high
- **Impact:** The feedback endpoint calls detector.collect_user_feedback(...), a method that no longer exists on AnomalyDetector after the simple-engineering refactor (the class only exposes detect_anomalies and the static calculate_document_risk_score). The call raises AttributeError, which is caught by the broad except at line 936 and converted to HTTP 500. Result: the entire feedback feature is non-functional — every valid feedback submission from the frontend (POST /anomalies/{id}/feedback) fails with 'Failed to collect feedback.' Even if it did not crash there, line 926 does FeedbackStats(**result['feedback_stats']) on a result that never gets produced.
- **Evidence:** result = detector.collect_user_feedback(
    anomaly_id=anomaly_id,
    user_action=internal_action,
    confidence_at_detection=feedback.confidence_at_detection
)
# AnomalyDetector defines only: detect_anomalies(...), calculate_document_risk_score(...). grep across app/ confirms collect_user_feedback exists nowhere.
- **Fix:** Either reimplement feedback persistence (e.g. write a FeedbackEvent row — the model still exists in app/models/feedback_event.py) and build a real FeedbackStats, or replace the detector call with a direct DB insert + a stubbed/real stats response. Do not leave a call to a deleted method.

### H2. get_performance_metrics crashes with KeyError on every call (placeholder feedback_stats dict missing required keys)
- **File:** `backend/app/api/v1/anomalies.py:130-143` · **Category:** crash · **Finder:** be-anomalies-api · **Verifier confidence:** high
- **Impact:** feedback_stats is hardcoded to {'total_feedback': 0, 'positive': 0, 'negative': 0} after ActiveLearningManager was removed, but the code immediately indexes feedback_stats['dismissal_rate'] (line 143), then ['total_feedback_collected'] (171), ['calibrator_fitted'] (176), ['retrain_count'] (177), ['last_retrain_date'] (178). The first access raises KeyError('dismissal_rate'), caught by the broad except at line 192 → HTTP 500. The /performance endpoint is therefore permanently broken for the admins it is gated to. Separately, line 147 references detector.confidence_calibrator.is_fitted, an attribute that no longer exists on AnomalyDetector (would also AttributeError), but the KeyError fires first.
- **Evidence:** feedback_stats = {"total_feedback": 0, "positive": 0, "negative": 0}
...
false_positive_rate = feedback_stats['dismissal_rate']   # KeyError
...
if detector.confidence_calibrator.is_fitted:            # attribute does not exist
...
total_feedback_collected=feedback_stats['total_feedback_collected'],  # KeyError
calibrator_fitted=feedback_stats['calibrator_fitted'],               # KeyError
- **Fix:** Build feedback_stats with all keys the PerformanceMetrics schema needs (dismissal_rate, total_feedback_collected, calibrator_fitted, retrain_count, last_retrain_date, accuracy, etc.) or compute them from FeedbackEvent rows. Remove the detector.confidence_calibrator reference and set expected_calibration_error=None and calibrator_fitted=False directly.

### H3. get_anomaly_report reanalysis path calls non-existent detector.set_user_preferences() — 500 whenever user_preferences is passed
- **File:** `backend/app/api/v1/anomalies.py:794-796` · **Category:** crash · **Finder:** be-anomalies-api · **Verifier confidence:** high
- **Impact:** In the reanalysis branch the code does detector = AnomalyDetector(); if prefs: detector.set_user_preferences(prefs). set_user_preferences does not exist on AnomalyDetector (removed in refactor; grep confirms it exists nowhere in app/). Any call to GET /anomalies/report/{id} with a non-empty, valid user_preferences JSON reaches this line and raises AttributeError, caught at line 827 → HTTP 500 'Failed to generate anomaly report.' This path is hit whenever the DB-read fast path is skipped (force_reanalysis=true, or processing_status != 'completed') AND user_preferences is supplied.
- **Evidence:** detector = AnomalyDetector()
if prefs:
    detector.set_user_preferences(prefs)   # AttributeError: 'AnomalyDetector' object has no attribute 'set_user_preferences'
- **Fix:** Remove the set_user_preferences call (the minimal pipeline ignores user preferences), or pass prefs through detect_anomalies' document_context. Drop the dead branch entirely if personalization is no longer supported.

### H4. reanalyze_document deletes all anomalies then 503s if services unavailable — destructive data loss with no rollback
- **File:** `backend/app/api/v1/anomalies.py:269-281` · **Category:** data-integrity · **Finder:** be-anomalies-api · **Verifier confidence:** high
- **Impact:** reanalyze deletes existing anomalies AND commits (db.query(Anomaly)...delete(); db.commit()) at lines 270-271, and only AFTER the commit checks whether embedding_service / pinecone_service are available, raising 503 if not (lines 277-281). Because the delete is already committed, a 503 (or any later failure in detection — the detect_anomalies call at 295 is not wrapped in try/except, so an LLM/timeout error 500s) leaves the document with ZERO anomalies persisted while document.anomaly_count / risk_level still show the OLD values (they are only updated at lines 345-348 after success). The user's previously-computed analysis is permanently destroyed and the document is left in an inconsistent state (stale counts, no anomaly rows). A retry that also fails compounds the loss.
- **Evidence:** deleted_count = db.query(Anomaly).filter(Anomaly.document_id == document_id).delete()
db.commit()                       # <-- committed BEFORE service availability check
...
if pinecone_service is None or embedding_service is None:
    raise HTTPException(status_code=503, ...)   # anomalies already gone
...
detection_result = await detector.detect_anomalies(...)   # not in try/except; failure 500s, anomalies already gone
- **Fix:** Check service availability and run detect_anomalies BEFORE deleting old anomalies, or do delete+reinsert in a single transaction (no intermediate commit) wrapped in try/except with db.rollback() on failure so the old anomalies survive a failed re-analysis.

### H5. alembic/env.py omits AnalysisLog (and all advanced) model imports → autogenerate emits DROP TABLE for live tables
- **File:** `backend/alembic/env.py:12, 22` · **Category:** data-integrity · **Finder:** be-db-integrity · **Verifier confidence:** high
- **Impact:** env.py builds target_metadata = Base.metadata after importing only `user, document, clause, anomaly, feedback_event`. It does NOT import `analysis_log`. Therefore Base.metadata has no `analysis_logs` table (and no `compound_risks`, `calibration_feedback`, `active_learning_queue` — those have no ORM model at all). These tables DO exist in the DB because migrations add_analysis_logs_002 and b8e4d92f1a3c create them. The next time anyone runs `alembic revision --autogenerate`, Alembic diffs metadata (no analysis_logs / advanced tables) against the DB (tables present) and will emit `op.drop_table('analysis_logs')`, `op.drop_table('compound_risks')`, etc. A developer who runs autogenerate + upgrade will silently DROP these tables and all their data. AnalysisLog is imported in app/models/__init__.py but env.py imports the submodules directly, so the class never gets registered on Base.metadata for migration purposes.
- **Evidence:** env.py line 12: `from app.models import user, document, clause, anomaly, feedback_event  # noqa: F401`  (no analysis_log). app/models/analysis_log.py defines `class AnalysisLog(Base)` with __tablename__='analysis_logs', and add_analysis_logs_table.py does `op.create_table('analysis_logs', ...)`. The mismatch makes autogenerate think the table is orphaned.
- **Fix:** Import analysis_log in env.py (`from app.models import user, document, clause, anomaly, feedback_event, analysis_log`), or better, import the package `import app.models` which runs __init__ and registers all classes. Also add ORM models (or `Table` stubs) for compound_risks/calibration_feedback/active_learning_queue, or mark them in include_object so autogenerate never tries to drop them.

### H6. submit_feedback calls AnomalyDetector.collect_user_feedback which does not exist → 500 on every feedback POST; feedback_events table is never written
- **File:** `backend/app/api/v1/anomalies.py:908` · **Category:** crash · **Finder:** be-db-integrity · **Verifier confidence:** high
- **Impact:** POST /anomalies/{anomaly_id}/feedback constructs `detector = AnomalyDetector()` then calls `detector.collect_user_feedback(...)`. AnomalyDetector.__init__ (anomaly_detector.py:52) defines no such method — the ActiveLearningManager was removed in the simple-engineering refactor. The call raises AttributeError, caught by the generic `except Exception` at line 936, and returns HTTP 500 for every feedback submission. Consequence for my scope: the FeedbackEvent model (app/models/feedback_event.py) and its migration (d2a4b5_feedback_event) describe a `feedback_events` table whose ONLY intended writer was collect_feedback/collect_user_feedback. Since that path is dead, the table is permanently empty — the persistence feature the model exists for is non-functional, and every user feedback action errors.
- **Evidence:** anomalies.py:888 `detector = AnomalyDetector()`; :908 `result = detector.collect_user_feedback(anomaly_id=..., user_action=..., confidence_at_detection=...)`. grep of anomaly_detector.py shows only `def __init__` — no collect_user_feedback / collect_feedback / confidence_calibrator. Model docstring (feedback_event.py:19-22) states rows are 'inserted by ActiveLearningManager.collect_feedback (write-through)', which no longer exists.
- **Fix:** Either reimplement persistence by writing a FeedbackEvent row directly in submit_feedback (db.add(FeedbackEvent(...)); db.commit()), or remove the feedback endpoint + FeedbackEvent model/migration if the feature is deprecated. Do not leave an endpoint that 500s on every call.

### H7. Missing-protection presence guard over-suppresses 'advance_notice_for_changes' via whole-document substring match with no proximity bound
- **File:** `backend/app/core/expected_protections.py:151-158, 219-239` · **Category:** logic · **Finder:** be-patterns-data · **Verifier confidence:** high
- **Impact:** The deterministic presence guard for advance_notice_for_changes treats the protection as PRESENT if ANY term-group has all its terms appearing ANYWHERE in the full document (case-insensitive substring, no proximity/co-clause requirement). The term-groups are 2-word pairs like ['days before','chang'] and ['advance notice','chang'], where 'chang' is a loose stem. On any real multi-section ToS, the word 'days before' (cancellation windows, free-trial windows) and the stem 'chang' (change/changes/changing/exchange) almost always BOTH occur somewhere in the document, independent of whether the doc actually commits to advance notice for TERMS changes. The guard then suppresses the legitimately-missing advance_notice_for_changes finding (a high_if_missing protection). This is the exact inverse of the inversion bug it was added to fix: it now produces FALSE NEGATIVES on documents that give NO advance notice. Because advance_notice_for_changes is the single most common 'missing protection' a reference tool flags, silently dropping it materially weakens recall on the marquee capability.
- **Evidence:** presence guard: `return any(all(term.lower() in text for term in group) for group in indicators)` over `text = (document_text or '').lower()` (whole doc). Indicators: `[['days before','chang'],['advance notice','chang'],['prior notice','chang'], ...]`. Reproduced: doc='You may cancel 7 days before the exchange of goods. We may modify terms at any time without notice.' -> protection_is_present == True (false-present; 'exchange' contains the 'chang' stem). Also doc='Free trials must be cancelled at least 3 days before the trial period ends. ... We reserve the right to change these Terms at any time. ... No notice will be provided.' -> True (false-present). The existing tests only use single-clause fragments where the two terms legitimately co-occur, so they miss this.
- **Fix:** Require the two terms in a group to co-occur within a bounded window (e.g. same sentence or within N characters/words), and/or anchor the change-stem to 'these terms'/'this agreement' so cancellation-window and exchange language doesn't satisfy it. At minimum replace the 'chang'/'modif' bare stems with the full phrases tied to terms changes (e.g. 'change these terms', 'modify these terms', 'changes to these terms') and require the notice phrase ('days before','advance notice','prior notice') within ~80 chars of that phrase.

### H8. Background task DB-failure recovery omits rollback → document permanently stuck in 'analyzing_anomalies'
- **File:** `backend/app/api/v1/upload.py:299-312` · **Category:** error-handling · **Finder:** be-upload-pipeline · **Verifier confidence:** high
- **Impact:** In run_anomaly_detection_background, if the failure that triggers the except block originated from a DB operation (e.g. db.commit() at line 289, or the implicit flush from db.add(anomaly) at line 280 hitting a constraint/serialization error), the SQLAlchemy session is left in a failed/aborted-transaction state. The recovery handler then immediately issues db.query(Document)... at line 304 WITHOUT calling db.rollback() first. On PostgreSQL this raises 'current transaction is aborted, commands ignored until end of transaction block' (PendingRollbackError), which is swallowed by the inner except at line 311. Result: processing_status is never moved off 'analyzing_anomalies'. The frontend (useDocument / useAnomalies refetchInterval) keeps polling that status forever (every 3s indefinitely), so the document is stuck 'analyzing' in the UI with no error ever surfaced. The whole point of the failed-status update is defeated precisely in the DB-error case it is meant to handle.
- **Evidence:** except Exception as e:
    logger.error(...)
    # Update document status to failed
    try:
        document = db.query(Document).filter(Document.id == document_id).first()  # <-- no db.rollback() first; on PG this throws if txn aborted
        if document:
            document.processing_status = "anomaly_detection_failed"
            ...
            db.commit()
    except Exception as db_error:
        logger.error(f"Failed to update document status after error: {db_error}")
- **Fix:** Call db.rollback() as the first statement inside the except handler (before re-querying), so the session is usable: `except Exception as e: db.rollback(); ...`. Optionally wrap the recovery commit in its own try with a fresh session if rollback itself fails.

### H9. Document risk_score / risk_level never returned by GET endpoints → completed analysis shows no risk in UI
- **File:** `backend/app/api/v1/upload.py:648-657, 690-699` · **Category:** contract-mismatch · **Finder:** be-upload-pipeline · **Verifier confidence:** high
- **Impact:** The background task writes document.risk_score and document.risk_level to the DB (upload.py:286-287). The DocumentResponse schema exposes risk_score and risk_level (schemas/document.py:72-77) and the frontend reads document.risk_level / document.risk_score (AnalysisResults.tsx:33-34,57,143). But get_document and list_documents construct DocumentResponse manually and OMIT risk_score= and risk_level=, so they fall back to the schema default of None. Because these are explicit constructor calls (not from_attributes auto-mapping), the persisted values are silently dropped. After analysis completes and the frontend polls GET /{id}, it always receives risk_score=null and risk_level=null, so the computed risk badge/score in the UI is wrong/empty even though the data exists in the DB.
- **Evidence:** return DocumentResponse(
    id=document.id,
    filename=document.filename,
    metadata=document.document_metadata,
    page_count=document.page_count,
    clause_count=document.clause_count,
    anomaly_count=document.anomaly_count,
    processing_status=document.processing_status,
    created_at=document.created_at,
)  # risk_score / risk_level NOT passed -> default None
- **Fix:** Pass risk_score=document.risk_score and risk_level=document.risk_level in both get_document and list_documents (and the upload responses), or build the response via DocumentResponse.model_validate(document) using from_attributes to pick up all columns automatically.

### H10. Per-severity kappa returns 1.0 for zero-support classes, causing false CI-gate regressions
- **File:** `backend/evals/metrics/kappa.py:126-131, 165-186` · **Category:** logic · **Finder:** evals · **Verifier confidence:** high
- **Impact:** `kappa_per_severity` runs one-vs-rest kappa per class in {critical,high,medium,low}. On a dataset with no gold examples of a class (UNFAIR-ToS has zero `critical` and zero `low` after the label mapping), both rater sequences are all "no", so in `cohens_kappa` pe>=1.0 and po==1.0 -> it returns 1.0. That degenerate 1.0 is written into the baseline as `per_severity_kappa.critical`/`.low`. `ci_gate._gather_kappa_axes` gates EACH per-severity axis. A later run that makes a single false-critical prediction drops that axis from 1.0 to <=0 (delta <= -1.0), tripping `delta < -max_kappa_regression` (-0.03) and FAILING CI — even though the 1.0 was an artifact of zero support, not real agreement. The gate thus fires spurious 'regressions' (and conversely the inflated 1.0 masks real moves). Verified empirically: baseline critical=1.0; one false critical -> 0.0; delta -1.0.
- **Evidence:** if pe >= 1.0:
    return 1.0 if po == 1.0 else 0.0
# kappa_per_severity: r1/r2 all 'no' for an absent class -> returns 1.0
# ci_gate gates: out[f"per_severity_kappa.{sev}"] = float(val)  for every sev
# repro: per_severity_kappa['critical']==1.0 with no critical labels; -> 0.0 after 1 FP -> delta -1.0 (regression)
- **Fix:** In kappa_per_severity, return None / omit a class with zero support in BOTH raters (or zero gold support), and have ci_gate skip axes that are None or whose baseline support is 0. Alternatively define the zero-support one-vs-rest kappa as 0.0 (undefined-but-not-perfect) and document it; either way do not let an artifactual 1.0 become a gated baseline.

### H11. Failed analysis (risk_level="Unknown") crashes the entire DocumentPage — no error boundary
- **File:** `frontend/src/components/analysis/RiskSummaryHeader.tsx:99-100` · **Category:** crash · **Finder:** fe-anomaly-analysis · **Verifier confidence:** high
- **Impact:** When background anomaly detection fails, the backend sets document.risk_level = "Unknown" and processing_status = "anomaly_detection_failed" (backend/app/api/v1/upload.py:306-309). On the frontend, AnalysisResults.getDocumentRiskLevel() computes isAnalyzing=false (the failed status is not in the analyzing set) and, because document.risk_level is the truthy string "Unknown", returns "unknown" (AnalysisResults.tsx:33-34, `document.risk_level.toLowerCase()`). That value is passed as riskLevel to RiskSummaryHeader, where `const meta = RISK_META[riskLevel]` yields undefined (RISK_META only has keys analyzing/critical/high/medium/low), and the very next line `const { Icon } = meta;` throws `TypeError: Cannot destructure property 'Icon' of undefined`. There is NO ErrorBoundary anywhere in the frontend (grep for ErrorBoundary/componentDidCatch returned nothing), and DocumentPage renders <AnalysisResults> unconditionally, so the React render error unwinds the whole route to a blank white screen. So any document whose analysis failed becomes completely unviewable.
- **Evidence:** RiskSummaryHeader.tsx: `const meta = RISK_META[riskLevel];\n  const { Icon } = meta;` — RISK_META has no 'unknown' key. AnalysisResults.tsx:33-34: `if (document.risk_level) { return document.risk_level.toLowerCase() as 'critical' | 'high' | 'medium' | 'low'; }`. upload.py:309: `document.risk_level = "Unknown"` on failure.
- **Fix:** Normalize/whitelist risk_level in getDocumentRiskLevel(): after toLowerCase(), if the value is not one of critical/high/medium/low, fall through to the count-based calculation (or return 'low'). Defensively, also make RiskSummaryHeader fall back to a default meta when RISK_META[riskLevel] is undefined (e.g. `const meta = RISK_META[riskLevel] ?? RISK_META.low;`).

### H12. Feedback submission always returns 500 (backend calls non-existent detector methods) → onSuccess never runs, localStorage never written, retry loop
- **File:** `frontend/src/hooks/useFeedback.ts:79-96` · **Category:** error-handling · **Finder:** fe-api-state · **Verifier confidence:** high
- **Impact:** The feedback mutation calls `api.submitFeedback` → `POST /anomalies/{id}/feedback`. The backend handler (anomalies.py:888-912) instantiates `AnomalyDetector()` and calls `detector.collect_user_feedback(...)`, but `AnomalyDetector` (anomaly_detector.py:52-69) defines ONLY `__init__` and `detect_anomalies` — there is no `collect_user_feedback`, `set_user_preferences`, or `confidence_calibrator` attribute. The call raises AttributeError, caught by the generic `except Exception` → HTTP 500. Effect on the frontend in scope: every feedback click resolves to the mutation's `onError`, so `markFeedbackSubmitted()`/`getSubmittedFeedbackAction()` are never persisted, the success toast/`localSubmittedAction` UI transition (FeedbackButtons.tsx:79-85) never happens, and the user can re-submit indefinitely. The whole 'active learning' feedback feature is non-functional end-to-end. (Same dead-method problem 500s the `/anomalies/performance` and report-reanalysis paths: anomalies.py:147 `detector.confidence_calibrator`, :796 `detector.set_user_preferences`.)
- **Evidence:** anomalies.py:908 `result = detector.collect_user_feedback(anomaly_id=..., user_action=internal_action, confidence_at_detection=...)`; anomaly_detector.py only exposes `def __init__` (52) and `async def detect_anomalies` (73) — `grep 'def collect_user_feedback|set_user_preferences|confidence_calibrator'` returns nothing in that file.
- **Fix:** Backend: implement `collect_user_feedback` (and `set_user_preferences`/`confidence_calibrator` or remove their use) on AnomalyDetector, or replace the handler body with a direct FeedbackEvent insert + computed FeedbackStats. Frontend: harmless but the feature is dead until the 500 is fixed.

### H13. Every error toast shows the generic interceptor message; backend `detail` is never surfaced (error-shape mismatch)
- **File:** `frontend/src/services/api.ts:140-147` · **Category:** contract-mismatch · **Finder:** fe-api-state · **Verifier confidence:** high
- **Impact:** The response interceptor rejects with a flattened object `{ message, status, originalError }` — it does NOT preserve `error.response.data.detail` at the top level. Yet most consumers read `error.response.data.detail`. Because the rejected value has no `.response` property at all (only `.originalError.response`), `(error as {response?...})?.response?.data?.detail` is always `undefined`, so the UI falls through to a hardcoded generic string. This affects LoginForm.tsx:26, SignupForm.tsx:40, and useQuery.ts:10 (which has NO `e.message` fallback, so it reads only the missing `.response.data.detail`). Concrete impact: a user who signs up with an already-registered email gets the backend message 'Email already registered...' computed in the interceptor as `message`, but SignupForm ignores `message` and shows 'Signup failed. Please try again.' Query errors (e.g. 'Document has no content to analyze', 422 validation) always show 'Failed to query document'. The actionable backend detail is thrown away.
- **Evidence:** interceptor: `const friendlyError = { message, status, originalError: error }; return Promise.reject(friendlyError);` — no `.response` field. Consumer (useQuery.ts:10): `const message = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to query document';` — `.response` is undefined on the rejected object, so it's ALWAYS the fallback. LoginForm.tsx:26 and SignupForm.tsx:40 use the identical broken pattern.
- **Fix:** Have consumers read `error.message` (the interceptor already computes the friendly/`detail` message there, including the 422 detail parsing). E.g. in useQuery.ts: `const message = (error as { message?: string })?.message || 'Failed to query document';`. Same for LoginForm/SignupForm. Alternatively, make the interceptor attach `response` (or a `detail`) onto the rejected object so the existing `.response.data.detail` reads resolve.

### H14. Anomalies polling stops on stale prop status before final results load → "No Risks Found" shown despite findings
- **File:** `frontend/src/hooks/useAnomalies.ts:13-18` · **Category:** race · **Finder:** fe-auth-doc-pages · **Verifier confidence:** high
- **Impact:** DocumentPage runs two INDEPENDENT 3s polls: useDocument (keyed off its own query data) and useAnomalies (keyed off the documentStatus PROP passed down from DocumentPage). The backend writes anomalies and flips processing_status to 'completed' ATOMICALLY in one db.commit() (backend/app/api/v1/upload.py:280-289). On the frontend the two intervals fire at different wall-clock times. When useDocument's poll observes 'completed' first, DocumentPage re-renders and passes 'completed' to useAnomalies; the refetchInterval closure then returns false and the anomalies interval is cancelled BEFORE its own next tick. The anomalies query's last successful fetch happened during 'analyzing_anomalies' (up to 3s before the commit) and returned an empty array, and nothing invalidates queryKey ['anomalies', documentId] on completion (only useFeedback invalidates, and only after feedback). Net effect: AnomalyList falls into the !anomalies||length===0 && !isAnalyzing branch and renders the green 'No Risks Found' card even though the document has anomalies. User must hard-refresh to see them. This is intermittent and depends on poll phase alignment, making it a classic flaky data-correctness bug.
- **Evidence:** useAnomalies.ts:
  queryKey: ['anomalies', documentId],   // status NOT in key → no auto-refetch on status change
  refetchInterval: () => {
    if (documentStatus === 'analyzing_anomalies' || documentStatus === 'processing' || documentStatus === 'embedding_completed') return 3000;
    return false; // stops as soon as the PROP flips to completed
  }
DocumentPage.tsx:23  const { data: anomalies } = useAnomalies(id!, document?.processing_status);
upload.py:280-289  db.add(anomaly)... document.processing_status='completed'; db.commit()  // anomalies + completed land together
- **Fix:** Don't gate the anomalies poll on a sibling query's status. Either (a) include the status in the anomalies queryKey so a transition forces a refetch, or (b) in useDocument's onSuccess / a useEffect in DocumentPage, call queryClient.invalidateQueries({queryKey:['anomalies', id]}) when processing_status becomes 'completed', or (c) drive the anomalies refetchInterval off the anomalies query's own document fetch rather than a passed-down prop. Simplest robust fix: when status transitions to a terminal state, invalidate the anomalies (and report) queries once.

### H15. Failed analysis (anomaly_detection_failed) is silently rendered as "No Risks Found"
- **File:** `frontend/src/pages/DocumentPage.tsx:27-29, 43-49, 105-110` · **Category:** error-handling · **Finder:** fe-auth-doc-pages · **Verifier confidence:** high
- **Impact:** The backend sets processing_status='anomaly_detection_failed' when the background anomaly detection throws (backend/app/api/v1/upload.py:306), and also documents 'failed' as a terminal state. The frontend has NO branch for these. In DocumentPage, isAnalyzing is true only for the three in-progress statuses, so the processing banner is hidden; docError only catches a failed DOCUMENT fetch (the doc itself loads fine), so no error Alert is shown; and AnomalyList (line 116-148) renders the green 'No Risks Found' success card whenever anomalies is empty and isAnalyzing is false. Consequently a document whose analysis crashed is presented to the user as a clean, risk-free document — a misleading, potentially harmful false-negative for a risk-analysis product. The user has no indication anything went wrong and no way to retry.
- **Evidence:** DocumentPage.tsx:27  const isAnalyzing = document?.processing_status === 'analyzing_anomalies' || ... === 'processing' || ... === 'embedding_completed';
// no handling for 'anomaly_detection_failed' / 'failed'
upload.py:306  document.processing_status = "anomaly_detection_failed"
AnomalyList.tsx:136-148  // !anomalies||0 && !isAnalyzing → 'No Risks Found' (emerald success card)
- **Fix:** Add an explicit terminal-failure branch: if document.processing_status === 'anomaly_detection_failed' || 'failed', render a destructive Alert ('Analysis failed — please re-run') in DocumentPage and short-circuit AnomalyList's success state. Optionally expose a re-analyze action (api.reanalyzeDocument already exists).

### H16. get_performance_metrics crashes with KeyError — feedback_stats dict is missing every key it reads
- **File:** `backend/app/api/v1/anomalies.py:130-180` · **Category:** crash · **Finder:** x-async · **Verifier confidence:** high
- **Impact:** feedback_stats is hardcoded as {"total_feedback": 0, "positive": 0, "negative": 0}, but the code then reads feedback_stats['dismissal_rate'] (line 143/156/173), ['total_feedback_collected'] (171), ['calibrator_fitted'] (176), ['retrain_count'] (177), ['last_retrain_date'] (178) — none of which exist. The first access (line 143) raises KeyError, caught by the broad except at 192 and re-raised as a 500. The endpoint can never succeed. Additionally detector.confidence_calibrator (line 147) does not exist on the refactored thin AnomalyDetector, which would also raise AttributeError.
- **Evidence:** feedback_stats = {"total_feedback": 0, "positive": 0, "negative": 0}
...
false_positive_rate = feedback_stats['dismissal_rate']   # KeyError: 'dismissal_rate'
...
if detector.confidence_calibrator.is_fitted:             # AttributeError: no such attribute
- **Fix:** Remove the dead feedback/calibrator code paths (ActiveLearningManager was deleted in the refactor) and compute metrics only from columns that exist, or rebuild feedback_stats with the keys actually read. Drop the confidence_calibrator reference.

### H17. reanalysis path of get_anomaly_report calls non-existent detector.set_user_preferences → 500
- **File:** `backend/app/api/v1/anomalies.py:794-796` · **Category:** crash · **Finder:** x-async · **Verifier confidence:** high
- **Impact:** When force_reanalysis=true (or DB read fails through), the report endpoint does detector = AnomalyDetector(); if prefs: detector.set_user_preferences(prefs). set_user_preferences does not exist on the refactored AnomalyDetector (grep confirms no definition anywhere in app/core). Any reanalysis request that supplies a valid user_preferences JSON raises AttributeError, caught at line 827 and returned as a 500 'Failed to generate anomaly report'. The reanalysis feature is broken whenever preferences are passed.
- **Evidence:** detector = AnomalyDetector()
if prefs:
    detector.set_user_preferences(prefs)   # AttributeError: 'AnomalyDetector' has no attribute 'set_user_preferences'
- **Fix:** Remove the set_user_preferences call (preferences are no longer consumed by the thin detector), or reimplement preference handling. Also confirm the rest of the reanalysis path matches the new detect_anomalies signature.

### H18. submit_feedback calls non-existent detector.collect_user_feedback → 500 on every feedback submission
- **File:** `backend/app/api/v1/anomalies.py:888-912` · **Category:** crash · **Finder:** x-async · **Verifier confidence:** high
- **Impact:** The feedback endpoint constructs AnomalyDetector() and calls detector.collect_user_feedback(...). That method was removed with the ActiveLearningManager in the simple-engineering refactor and does not exist on the current detector. Every feedback POST raises AttributeError, caught by the except at 936 and returned as a 500. The entire user-feedback feature is non-functional and also leaks an Anthropic client per call (see resource-leak finding).
- **Evidence:** detector = AnomalyDetector()
...
result = detector.collect_user_feedback(
    anomaly_id=anomaly_id,
    user_action=internal_action,
    confidence_at_detection=feedback.confidence_at_detection
)   # AttributeError: no such method
- **Fix:** Either persist feedback directly to the FeedbackEvent table from the route, or restore a collect_user_feedback implementation. Remove the dead detector instantiation regardless.

### H19. Total LLM detection failure is swallowed and the document is silently marked completed with 0 anomalies
- **File:** `backend/app/core/llm_clause_detector.py:492-505` · **Category:** error-handling · **Finder:** x-async · **Verifier confidence:** high
- **Impact:** detect_risky_clauses wraps the whole batch flow in try/except and, on ANY exception (e.g. all batches fail their single retry, Claude outage, repeated 429s), logs and returns an empty findings list instead of raising. detect_anomalies in anomaly_detector.py also catches missing-protections failures non-fatally. The background task then receives a valid report with empty alerts and sets document.processing_status='completed', anomaly_count=0 (upload.py:285-289). The user sees a fully-analyzed document with zero risks found, indistinguishable from a genuinely clean document — a silent false-negative / data-integrity failure. There is no 'partial failure' or 'retry' state. The 'keyword detection still runs at higher level' comment is stale: the refactor deleted the fallback stages.
- **Evidence:** except Exception as e:
    logger.error(f"LLM clause detection failed entirely: {e}", exc_info=True)
    # Graceful fallback — keyword detection still runs at higher level.
    all_findings = []   # <-- but there is NO keyword fallback anymore (refactor deleted stages)
...
# upload.py background task then:
document.processing_status = "completed"   # even though detection produced nothing
- **Fix:** Distinguish 'LLM produced 0 findings' from 'LLM failed'. Have detect_risky_clauses re-raise on total batch failure (or return a status flag); in the background task, on detection error set processing_status to a retryable 'analysis_failed' state rather than 'completed', so 0-anomaly false-negatives aren't presented as clean results.

### H20. risk_title and risk_category are stored in DB and rendered by the UI but are absent from the AnomalyResponse schema/serializer, so every card shows generic "Risk Detected" with no category
- **File:** `backend/app/schemas/anomaly.py:154-181` · **Category:** contract-mismatch · **Finder:** x-contract · **Verifier confidence:** high
- **Impact:** The Anomaly DB model has risk_title and risk_category columns (backend/app/models/anomaly.py:22,26) and they are persisted on upload (upload.py:272,276). The frontend AnomalyCard renders anomaly.risk_title (AnomalyCard.tsx:68) and anomaly.risk_category (AnomalyCard.tsx:37-39). But AnomalyResponse extends AnomalyBase, which declares ONLY clause_text/section/clause_number/severity/explanation/consumer_impact/recommendation/prevalence/risk_flags — no risk_title, no risk_category. The list/detail serializers in anomalies.py (get_anomalies lines 486-504, get_anomaly_detail 551-563, reanalyze 359-371) construct AnomalyResponse explicitly without passing risk_title/risk_category. Because these are explicit constructor calls against a schema that doesn't define the fields, the values are silently dropped. Result: the only anomaly payload the UI actually consumes (useAnomalies -> getAnomalies) never contains risk_title or risk_category, so every card always shows the fallback heading "Risk Detected" and never shows a category chip. (The richer _anomaly_to_ranked_dict DOES include them, but that feeds /anomalies/report, whose RankedAnomaly arrays the FE does not render — DocumentPage only reads report.competitive_benchmark.)
- **Evidence:** schemas/anomaly.py AnomalyBase (154-165) has no risk_title/risk_category; AnomalyResponse(AnomalyBase) (174-181) adds only id/document_id/created_at. anomalies.py get_anomalies serializer (486-504) passes no risk_title/risk_category. AnomalyCard.tsx:68 `{anomaly.risk_title || 'Risk Detected'}` and :37 `anomaly.risk_category && anomaly.risk_category !== 'other'`.
- **Fix:** Add `risk_title: Optional[str] = None` and `risk_category: Optional[str] = None` to AnomalyBase (or AnomalyResponse), and pass `risk_title=a.risk_title, risk_category=a.risk_category` in the get_anomalies / get_anomaly_detail / reanalyze AnomalyResponse constructions.

### H21. POST /anomalies/{anomaly_id}/feedback always returns 500 (calls removed detector.collect_user_feedback)
- **File:** `backend/app/api/v1/anomalies.py:886-912` · **Category:** crash · **Finder:** x-security · **Verifier confidence:** high
- **Impact:** After ownership is verified, the handler instantiates AnomalyDetector() and calls detector.collect_user_feedback(...). That method does not exist on AnomalyDetector (confirmed by grep: no `def collect_user_feedback` anywhere in app/). Every valid feedback submission raises AttributeError, is caught by the broad except, and returns HTTP 500 'Failed to collect feedback.' The user-facing feedback UI is therefore completely broken and silently loses all feedback (nothing is persisted before the crash).
- **Evidence:** detector = AnomalyDetector()
...
result = detector.collect_user_feedback(
    anomaly_id=anomaly_id,
    user_action=internal_action,
    confidence_at_detection=feedback.confidence_at_detection
)  # AnomalyDetector has no such method -> AttributeError
- **Fix:** Persist feedback directly: insert a FeedbackEvent/anomaly-feedback row in the DB inside the request, build FeedbackStats from real counts (or simplify the response schema), and remove the call to the non-existent detector.collect_user_feedback.

### H22. GET /anomalies/report/{document_id} reanalysis path 500s (calls removed set_user_preferences + emits wrong response shape)
- **File:** `backend/app/api/v1/anomalies.py:792-823` · **Category:** crash · **Finder:** x-security · **Verifier confidence:** high
- **Impact:** Any user can reach the reanalysis branch (force_reanalysis=true, or document status != 'completed', or if the DB-read branch throws). That branch builds AnomalyDetector() and, when user_preferences are supplied, calls detector.set_user_preferences(prefs) — a method that does not exist (grep confirms) → AttributeError → 500. Even without preferences, the branch returns the thin-orchestrator dict from detect_anomalies, but the route declares response_model=AnomalyReportResponse, which requires fields the orchestrator never produces (compound_risks, ranking_metadata.{suppression_rate,avg_score,top_score,...}, pipeline_performance.{stage1_detections,...}). The orchestrator instead returns pipeline_performance keys checklist_findings/ranked_high/... and omits compound_risks, so FastAPI response validation raises and returns 500. The advertised 'force reanalysis' feature cannot succeed.
- **Evidence:** detector = AnomalyDetector()
if prefs:
    detector.set_user_preferences(prefs)   # no such method -> AttributeError
...
report = await detector.detect_anomalies(...)
...
return report   # dict lacks compound_risks/ranking_metadata subfields required by AnomalyReportResponse
- **Fix:** Remove the dead set_user_preferences call, and map the orchestrator report into AnomalyReportResponse (or relax the response_model to a dict) so the returned shape matches the declared schema. Reuse _anomaly_to_ranked_dict-style adaptation as the DB-read branch already does.

### H23. submit_feedback / reanalyze leak removed '6-stage pipeline' internals and reachable 500s expose stack via exc_info logging only — but endpoints advertise nonexistent behavior
- **File:** `backend/app/api/v1/anomalies.py:200-213` · **Category:** contract-mismatch · **Finder:** x-security · **Verifier confidence:** high
- **Impact:** POST /anomalies/reanalyze/{document_id} docstring and GET /report docstring advertise a '6-stage anomaly detection pipeline' (Pattern/Semantic/Statistical, Clustering, Compound Risk, Isotonic calibration) that was deleted in the refactor; reanalyze_document actually runs the thin LLM checklist orchestrator. reanalyze itself works (it adapts to AnomalyListResponse), but the misleading contract plus the report endpoint's stage1..stage6 response fields (PipelinePerformance schema) are filled with fabricated/constant values (stage2_filtered_out=0, stage5_calibrated=total, etc.) in the DB-read branch. Consumers/monitoring that trust these 'pipeline_performance' numbers get fabricated data, not a real defect in flow but a data-integrity/observability concern.
- **Evidence:** "pipeline_performance": {
    "stage1_detections": total,
    "stage2_passed": total,
    "stage2_filtered_out": 0,
    "stage3_clustered": total,
    "stage4_compounds": 0,
    "stage5_calibrated": total,
    "stage6_ranked": total,
    ...
}
- **Fix:** Update the docstrings and the AnomalyReportResponse/PipelinePerformance schema to reflect the current checklist+ranker flow, and stop emitting hard-coded stageN metrics that no longer correspond to any pipeline stage.

## MEDIUM (27)

### M1. get_anomaly_report reanalysis path returns a dict that fails AnomalyReportResponse validation → 500
- **File:** `backend/app/api/v1/anomalies.py:799-816` · **Category:** contract-mismatch · **Finder:** be-anomalies-api · **Verifier confidence:** high
- **Impact:** The reanalysis branch returns the raw report dict from detector.detect_anomalies(...) (line 816). The endpoint declares response_model=AnomalyReportResponse, which REQUIRES ranking_metadata (RankingMetadata with required fields total_detected/total_shown/total_suppressed/suppression_rate/avg_score/top_score/top_categories/alert_budget_applied/user_preferences_applied) and pipeline_performance (PipelinePerformance with required fields stage1_detections, stage2_passed, stage2_filtered_out, stage3_clustered, stage4_compounds, stage5_calibrated, stage6_ranked, total_clauses_analyzed, total_processing_time_ms). But the minimal detector emits pipeline_performance = {checklist_findings, ranked_high, ranked_medium, ranked_low, total_processing_time_ms} (anomaly_detector.py:166-172) and a ranking_metadata produced by AlertRanker that does not match the stage-based schema. FastAPI response validation will raise ResponseValidationError → HTTP 500. So even with the set_user_preferences bug fixed, force_reanalysis=true always 500s. The DB-read fast path (lines 681-720) does NOT hit this because it manually constructs a fully-conformant dict.
- **Evidence:** if isinstance(report, dict):
    ...
    return report   # report['pipeline_performance'] = {'checklist_findings':..., 'ranked_high':...}; schema requires stage1_detections..stage6_ranked + total_clauses_analyzed → ResponseValidationError
- **Fix:** Map the detector's report into the AnomalyReportResponse shape before returning (synthesize the stage_* and ranking_metadata fields the same way the DB-read path does at lines 681-720), or relax/replace AnomalyReportResponse with a schema matching the minimal pipeline output.

### M2. Signup duplicate-email check uses raw (non-normalized) email while storage lowercases it → duplicate/uniqueness mismatch yields 500
- **File:** `backend/app/api/v1/auth.py:47, 66` · **Category:** data-integrity · **Finder:** be-auth-security · **Verifier confidence:** high
- **Impact:** The existing-user check queries `User.email == user_data.email` using the RAW request email, but the row is stored as `user_data.email.lower().strip()`. Pydantic's EmailStr lowercases only the domain, NOT the local part, so an input like 'Alice@Example.com' stays 'Alice@example.com'. Flow: (1) user signs up as 'alice@example.com' (stored lowercased). (2) Someone signs up as 'Alice@example.com' — the uniqueness query compares 'Alice@example.com' against the stored 'alice@example.com' and finds NO match, so the duplicate guard is bypassed. (3) The INSERT then violates the DB UNIQUE constraint on users.email, raising IntegrityError, which is swallowed by the broad `except Exception` at line 87 and converted to a generic HTTP 500 'Failed to create user account.' The user gets a confusing 500 instead of a clean 400, and the legitimate case-insensitive duplicate is never reported correctly. Verified empirically: EmailStr('Alice@Example.com') -> 'Alice@example.com', which != 'alice@example.com'.
- **Evidence:** existing_user = db.query(User).filter(User.email == user_data.email).first()  # raw, not lowered
...
user = User(email=user_data.email.lower().strip(), ...)  # stored lowered
...
except Exception as e:
    raise HTTPException(status_code=500, detail="Failed to create user account.")
- **Fix:** Normalize once at the top: `email = user_data.email.lower().strip()` and use that variable BOTH for the uniqueness filter (`User.email == email`) and the User(...) insert. Additionally, catch IntegrityError specifically and return a 400 'Email already registered' so a race or any residual case mismatch surfaces as 400, not 500.

### M3. Broad `except Exception` in signup masks HTTPException-worthy errors and turns duplicate-insert races into 500
- **File:** `backend/app/api/v1/auth.py:87-93` · **Category:** error-handling · **Finder:** be-auth-security · **Verifier confidence:** high
- **Impact:** The try/except around user creation catches every Exception (including sqlalchemy.exc.IntegrityError from a concurrent duplicate signup, and any DB-level constraint/length error) and rewrites them all to a generic HTTP 500. Two concurrent signups for the same email both pass the line-47 existence check, then one INSERT succeeds and the second raises IntegrityError → 500 instead of 400. This is also the second-order effect of the case-normalization bug above. There is no specific handling for the expected, recoverable duplicate-key condition, so the API contract (400 for already-registered) is violated under races and case-variant inputs.
- **Evidence:** try:
    user = User(...)
    db.add(user); db.commit(); db.refresh(user)
    ...
except Exception as e:
    logger.error(f"Signup failed: {e}", exc_info=True)
    db.rollback()
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user account.")
- **Fix:** Catch `from sqlalchemy.exc import IntegrityError` explicitly and return HTTP 400 'Email already registered'; only fall back to 500 for truly unexpected errors. Keep the rollback.

### M4. SlowAPI limiter uses in-memory storage with per-process counters and no shared backend — rate limits are not enforced across workers/restarts
- **File:** `backend/app/core/rate_limit.py:11-14` · **Category:** logic · **Finder:** be-auth-security · **Verifier confidence:** high
- **Impact:** The Limiter is constructed with no `storage_uri`, so SlowAPI defaults to in-memory (memory://) per-process counters. The auth limits (signup 10/hour, login 20/hour) are the only brute-force / enumeration protection on these endpoints. With more than one Uvicorn/Gunicorn worker (or any horizontally-scaled deployment), each process keeps its OWN counter, so the effective limit is N_workers × the configured value, and counters reset on every restart/redeploy. The app already configures REDIS_URL in config.py, so a shared store is available but unused. This materially weakens the login/signup throttle the rest of the auth design relies on.
- **Evidence:** limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_HOUR}/hour"],
)  # no storage_uri -> in-memory, per-process
- **Fix:** Pass `storage_uri=settings.REDIS_URL` (with a fallback warning if Redis is down) so rate-limit counters are shared across workers and survive restarts.

### M5. get_performance_metrics reads feedback_stats['dismissal_rate'] / ['total_feedback_collected'] from a dict that lacks those keys → KeyError 500
- **File:** `backend/app/api/v1/anomalies.py:143, 147, 156, 171, 173, 176` · **Category:** crash · **Finder:** be-db-integrity · **Verifier confidence:** high
- **Impact:** After the refactor, feedback_stats is hardcoded to `{"total_feedback": 0, "positive": 0, "negative": 0}` (line 130). The code then accesses `feedback_stats['dismissal_rate']` (143, 156, 158, 173, 186), `feedback_stats['total_feedback_collected']` (171), `feedback_stats['calibrator_fitted']` (176), `feedback_stats['retrain_count']` (177), `feedback_stats['last_retrain_date']` (178) — none of those keys exist → KeyError. Additionally line 147 `detector.confidence_calibrator.is_fitted` references an attribute that no longer exists → AttributeError. The generic except returns HTTP 500. The admin metrics endpoint is therefore permanently broken.
- **Evidence:** Line 130: `feedback_stats = {"total_feedback": 0, "positive": 0, "negative": 0}`. Line 143: `false_positive_rate = feedback_stats['dismissal_rate']` (KeyError). Line 147: `if detector.confidence_calibrator.is_fitted:` — AnomalyDetector has no confidence_calibrator attribute.
- **Fix:** Populate the placeholder dict with all keys the code reads (dismissal_rate, total_feedback_collected, calibrator_fitted, retrain_count, last_retrain_date) set to safe defaults, and remove the detector.confidence_calibrator reference. Or compute these from the feedback_events table now that it should be the source of truth.

### M6. DATABASE_URL points at Supabase SESSION pooler (:5432) but pool_size+max_overflow=15 per process and no pool_recycle → connection-limit exhaustion / stale connections
- **File:** `backend/app/db/session.py:15-21` · **Category:** resource-leak · **Finder:** be-db-integrity · **Verifier confidence:** high
- **Impact:** The engine uses the default QueuePool with pool_size=5 + max_overflow=10 = up to 15 server connections per worker process. .env DATABASE_URL targets `aws-1-eu-central-2.pooler.supabase.com:5432` — Supabase's SESSION pooler (port 5432; the transaction pooler is 6543). The session pooler keeps one upstream Postgres connection per client connection for the whole session and has a low hard cap on the IPv4/free tiers. With multiple uvicorn workers (e.g. 4 × 15 = 60) the app can exceed the pooler limit; new checkouts get rejected with 'remaining connection slots reserved' / 'max clients reached' → request 500s under load. Compounding: there is no `pool_recycle` set, so QueuePool will hand out connections the pooler has already closed for idle timeout; pool_pre_ping mitigates this on checkout but at the cost of an extra round-trip and does not prevent mid-request drops.
- **Evidence:** session.py:15-21 `create_engine(settings.DATABASE_URL, pool_size=settings.DATABASE_POOL_SIZE, max_overflow=settings.DATABASE_MAX_OVERFLOW, pool_pre_ping=True, echo=...)` with config defaults DATABASE_POOL_SIZE=5, DATABASE_MAX_OVERFLOW=10 (config.py:41-42). .env DATABASE_URL host=...pooler.supabase.com:5432 (session pooler).
- **Fix:** Either point at the transaction pooler (:6543) and use NullPool/pool_size small with pool_pre_ping, or keep the session pooler but set conservative pool_size (e.g. 2) + max_overflow (e.g. 3) sized so pool_size*workers stays under the pooler cap, and add pool_recycle (e.g. 300s) to evict connections before the pooler idle-kills them.

### M7. Three data-rights protections lack requires_context, so they false-fire as 'missing' on documents with no personal-data processing
- **File:** `backend/app/core/expected_protections.py:79-102` · **Category:** logic · **Finder:** be-patterns-data · **Verifier confidence:** high
- **Impact:** data_deletion_right (high_if_missing), data_export_right (medium_if_missing) and data_access_right (medium_if_missing) are the only three protections that omit requires_context/relevance_test, whereas every other data/privacy protection (retention_period_specific, breach_notification, advertising_optout) is gated with requires_context=True and a relevance_test telling the LLM to mark 'not_applicable' for docs with no data-handling section. Without the gate, the LLM is not instructed to suppress these on a pure ToS / B2B / fixed agreement that does not process personal data, so they tend to be reported 'absent' and emitted as findings (data_deletion_right at HIGH). This is an inconsistency with the sibling data protections and a likely false-positive source on non-privacy documents — exactly the 'arbitration-opt-out on a UK doc' class of noise the relevance gate was designed to prevent.
- **Evidence:** data_deletion_right entry (lines 80-86) has no 'requires_context' / 'relevance_test' keys; compare retention_period_specific (114-122) which has `"requires_context": True, "relevance_test": "Only relevant for documents that collect and store personal data ... A pure ToS with no personal-data processing should mark 'not_applicable'."`. Confirmed at runtime: data_deletion_right/data_export_right/data_access_right report requires_context == False while all other gated protections are True.
- **Fix:** Add requires_context=True plus a relevance_test ('Only relevant for documents that collect/store personal data; a pure ToS with no personal-data processing should mark not_applicable') to data_deletion_right, data_export_right, and data_access_right, mirroring retention_period_specific/breach_notification.

### M8. compare_documents crashes (500) when a document has NULL metadata
- **File:** `backend/app/api/v1/compare.py:75` · **Category:** crash · **Finder:** be-query-main · **Verifier confidence:** high
- **Impact:** `doc.document_metadata.get("company", "Unknown")` calls `.get()` directly on `document_metadata`, which is a nullable JSON column (`Document.document_metadata = Column(JSON, nullable=True)`). If any of the compared documents has `document_metadata IS NULL` (legacy rows, a metadata-extraction path that stored None, or any future code path that doesn't set it), this raises `AttributeError: 'NoneType' object has no attribute 'get'`. The surrounding broad `except Exception` (compare.py:141) swallows it and returns a generic HTTP 500 'Document comparison failed. Please try again.' — so the comparison feature is permanently broken for that document set, not transiently. Notably, the other consumers of this column guard against None: anomalies.py:291 uses `if document.document_metadata:` and anomalies.py:644 uses `document.document_metadata or {}`. compare.py is the only unguarded reader.
- **Evidence:** compare.py:75 `"company": doc.document_metadata.get("company", "Unknown"),` inside the per-doc loop. Model: document.py:37-39 `document_metadata = Column(JSON, nullable=True)`. Contrast anomalies.py:644 `metadata = document.document_metadata or {}`.
- **Fix:** Defensively coerce: `(doc.document_metadata or {}).get("company", "Unknown")`.

### M9. Comparison endpoint has no processing-status gate — compares unfinished documents with bogus zero risk scores
- **File:** `backend/app/api/v1/compare.py:39-58` · **Category:** logic · **Finder:** be-query-main · **Verifier confidence:** high
- **Impact:** Unlike the query endpoint (which gates on `allowed_statuses` and rejects documents still being processed), compare_documents only checks ownership and count. A user can compare documents that are still in `analyzing_anomalies` (or even `failed`) status. Such documents have `risk_score = NULL` (coerced to 0.0 at line 76) and zero anomalies (the background detection task hasn't run yet). The endpoint then confidently reports the unfinished document as the 'BEST' option with 'risk score 0.0/10' and 0 high-risk clauses, and computes `differences` against meaningless zeros. This produces actively misleading recommendations to the user about which T&C is safer — the core output of the feature — with no error or warning.
- **Evidence:** compare.py:39-58 validates only `Document.id.in_(...)`, `Document.user_id == current_user.id`, count == requested, and count >= 2. No `processing_status` check (compare with query.py:138-143 which enforces `allowed_statuses`). compare.py:76 `"risk_score": doc.risk_score or 0.0` and compare.py:122 `best_doc = min(comparisons, key=lambda x: x["risk_score"])` then drive the recommendation text at compare.py:125-133.
- **Fix:** Reject or flag documents not in a completed/queryable status before comparing (mirror query.py's allowed_statuses check), or exclude unanalyzed docs from the best/worst recommendation and surface a warning.

### M10. Q&A citations never include the real clause number (wrong metadata key)
- **File:** `backend/app/api/v1/query.py:222` · **Category:** logic · **Finder:** be-query-main · **Verifier confidence:** high
- **Impact:** Citations are built with `clause_id=metadata.get("clause_id", f"clause_{idx + 1}")`, but the metadata stored in Pinecone never contains a `clause_id` key. The legal chunker (`legal_chunker.py::_create_chunk`) writes the clause reference under the key `clause_number` (and the upsert in `pinecone_service.upsert_chunks` adds only `document_id`, `chunk_index`, `text`). A repo-wide search confirms `"clause_id"` appears only at this read site. Therefore `metadata.get("clause_id", ...)` ALWAYS falls back to the synthetic `clause_1`, `clause_2`, ... and the actual document clause number (e.g. '5.2'), which IS present in `metadata['clause_number']` and is even used correctly two lines above when building the context (`metadata.get('clause_number', 'N/A')`), is silently discarded. Every Q&A citation shown to the user is mislabeled with a meaningless sequential id instead of the real clause reference, defeating the whole point of citation-backed answers. The frontend CitationCard renders this fallback as `[clause_1]`.
- **Evidence:** query.py:209-210 builds context with the CORRECT key: `f"Clause: {metadata.get('clause_number', 'N/A')}\n"`; query.py:222 builds the Citation with the WRONG key: `clause_id=metadata.get("clause_id", f"clause_{idx + 1}"),`. legal_chunker.py:108-115 stores metadata as `{"section":..., "section_number":..., "clause_number": clause_number, "chunk_index":..., "context":...}` — no `clause_id`. `grep "clause_id"` across app/ returns only the query.py:222 read.
- **Fix:** Use the key that is actually stored: `clause_id=metadata.get("clause_number") or f"clause_{idx + 1}"`. Optionally also pass the section/clause to the frontend so the citation can display the genuine reference.

### M11. _clean_metadata crashes on non-string LLM values (e.g. numeric version) -> all metadata silently discarded
- **File:** `backend/app/core/metadata_extractor.py:161` · **Category:** error-handling · **Finder:** be-services · **Verifier confidence:** high
- **Impact:** _clean_metadata iterates string fields including 'version' and 'contact_email' and calls value.strip() at line 161. The values come straight from Claude's JSON. The prompt asks for 'version': 'Version number if mentioned', and LLMs frequently emit a JSON number (e.g. "version": 2.0 or "version": 3) rather than a string. value.strip() then raises AttributeError ('float'/'int' has no attribute 'strip'). The guard `if value and value != "null" and value.strip()` evaluates value.strip() eagerly because `and` short-circuits only on falsy, and a non-empty number is truthy -> it reaches .strip() and throws. extract_metadata() wraps the whole thing in try/except (line 79-82) and returns _get_default_metadata(), so a single bad field type silently throws away the CORRECTLY extracted company_name, jurisdiction, dates, etc. -> document shows blank/default metadata even though Claude returned good data.
- **Evidence:** for field in [..., "version", "contact_email", "website"]:
    value = metadata.get(field)
    if value and value != "null" and value.strip():   # AttributeError if value is int/float
        cleaned[field] = value.strip()
- **Fix:** Coerce/guard before stripping: `value = metadata.get(field); if value is not None and not isinstance(value, str): value = str(value); if value and value.strip().lower() != 'null': cleaned[field] = value.strip() else: cleaned[field] = None`. Apply the same str() coercion in the date loop.

### M12. Metadata key mismatch: detector & reports always see company='Unknown' (extractor emits 'company_name')
- **File:** `backend/app/api/v1/upload.py:195` · **Category:** contract-mismatch · **Finder:** be-upload-pipeline · **Verifier confidence:** high
- **Impact:** MetadataExtractor._clean_metadata only ever produces the key 'company_name' (metadata_extractor.py:151-164; prompt also returns 'company_name'). The metadata dict passed to the background task is exactly that cleaned dict plus detected_document_type. But run_anomaly_detection_background reads company_name = metadata.get('company', 'Unknown') at line 195 — the key 'company' is never set anywhere in the pipeline (grep confirms only readers reference 'company', no writer). So company_name is ALWAYS 'Unknown' regardless of what Claude extracted. This wrong value is then threaded into AnomalyDetector.detect_anomalies(company_name=...) where it feeds the detection prompts (anomaly_detector.py:104,117) and the final report's company_name field (anomaly_detector.py:156). _infer_service_type happens to also read 'company_name' (line 115) so service-type inference survives, masking the bug, but the detector context and report are degraded.
- **Evidence:** # upload.py:195
company_name = metadata.get("company", "Unknown")  # extractor emits 'company_name', never 'company'
# metadata_extractor.py:151
for field in ["company_name", "jurisdiction", ...]:  # key is company_name
- **Fix:** Read the correct key: `company_name = metadata.get("company_name") or metadata.get("company") or "Unknown"`. (Same latent issue in anomalies.py:293 and compare.py:75 which also read 'company'.)

### M13. Eval alignment drops duplicate-clause findings, scoring the WRONG severity vs production
- **File:** `backend/evals/baseline_runner.py:82 (also runner.py:78, run_gemini_agreement.py:94, judge/runner.py:512)` · **Category:** data-integrity · **Finder:** evals · **Verifier confidence:** high
- **Impact:** All four alignment helpers build `by_id = {str(f.get('clause_number')): f for f in findings}`. `detect_risky_clauses` legitimately returns MULTIPLE findings sharing one clause_number: (a) compound clause refs ("28-30", "2,4,28") are expanded so each matched clause gets its own finding (llm_clause_detector.py:1305-1319), and (b) multiple distinct catalog patterns can each cite the same clause (the documented "MED×3"/same-clause duplication). The dict comprehension keeps only the LAST finding per clause_number and silently discards the rest. Production instead collapses same-clause findings to the STRONGEST severity (anomaly_detector.py:_dedupe_findings Pass 2 via `_stronger`). So when the detector flags clause 5 as both critical and medium, the eval scores it MEDIUM (last wins) while production reports CRITICAL. This understates measured recall / severity-kappa / category-recall on exactly the multi-pattern clauses production handles best, and makes the headline benchmark numbers not reflect production behavior.
- **Evidence:** by_id = {str(f.get("clause_number")): f for f in findings}  # dict overwrite keeps LAST finding
# verified: findings=[{'clause_number':'5','severity':'critical',...},{'clause_number':'5','severity':'medium',...}]
# -> preds[0]['severity'] == 'medium' (the critical finding is dropped)
# production _dedupe_findings Pass 2: elif _stronger(f, cur): result[result.index(cur)] = f  (keeps strongest)
- **Fix:** Before building the alignment map, group findings by str(clause_number) and pick the strongest severity (and merge category), mirroring production `_dedupe_findings`/`_stronger`. E.g. for each clause_number keep the finding with the max SEVERITY_TIER rather than the last one. Apply in all four sites (baseline_runner._align_predictions, runner._align, run_gemini_agreement._run_production_detector, judge/runner._cli_main).

### M14. auto_promote_*.py auto-relabel the SEALED gold holdout with regex heuristics
- **File:** `backend/evals/datasets/auto_promote_critical.py:99-110, 192-198 (and auto_promote_high.py:129-140, 219-223)` · **Category:** data-integrity · **Finder:** evals · **Verifier confidence:** high
- **Impact:** Both auto_promote scripts read gold_holdout.jsonl (the hand-labeled, firewall-sealed test set) and, with --apply, atomically REWRITE the file, mutating `expected_severity` of rows whose text matches narrow regex patterns (e.g. medium->high, medium/high->critical). This converts hand-adjudicated gold labels into machine-generated ones derived from the very keyword heuristics the detector is conceptually similar to, which inflates measured agreement and undermines the holdout's value as an independent reference. There is no provenance flag distinguishing auto-promoted rows from human-labeled ones after the write, and the dry-run/--apply gate is the only safeguard. Because the firewall only blocks production-code READS, it does not protect against this in-eval WRITE corruption of the gold set.
- **Evidence:** # auto_promote_critical.py
for i, _rec, _hits in proposals:
    rows[i]["expected_severity"] = "critical"
atomic_rewrite(rows)   # rewrites gold_holdout.jsonl in place
# match_patterns() is pure regex over rec['text']
- **Fix:** Do not mutate gold_holdout.jsonl in place. Write proposals to a separate review queue file (e.g. gold_holdout_promotions_proposed.jsonl) and require a human regrade step (regrade_gold_holdout) to accept each, stamping a `label_source: human|auto-promoted` provenance field. At minimum add a `provenance`/`auto_promoted_from` field on every mutated row so auto-relabeled gold is auditable and can be excluded from headline metrics.

### M15. Documented runtime prompt-equality hash check between judges does not exist
- **File:** `backend/evals/judge/openai_judge.py:42-43 (and claude_judge.py JUDGE_SYSTEM_PROMPT)` · **Category:** contract-mismatch · **Finder:** evals · **Verifier confidence:** high
- **Impact:** openai_judge.py states: "The harness verifies prompt equality at runtime via a hash check." No such check exists anywhere (grep of evals/ finds only the comment plus an unrelated cache-key hash). The two JUDGE_SYSTEM_PROMPT constants are duplicated by hand across claude_judge.py and openai_judge.py with an instruction to "update BOTH files in lockstep." They are byte-identical today, but nothing enforces it. If a future edit changes one prompt and not the other, the cross-family agreement metric silently conflates prompt drift with model disagreement (the exact failure the module docstring warns about) and no test or runtime guard catches it — the harness keeps reporting an 'independent vendor' agreement number that is actually measuring two different rubrics.
- **Evidence:** # openai_judge.py:42-43
# "If you update the rubric, update BOTH files in lockstep. The harness
#  verifies prompt equality at runtime via a hash check."
# grep -rn 'hash' evals/judge/ -> only the cache-key sha256 in runner.py; NO prompt-equality assertion
- **Fix:** Either implement the promised guard (e.g. assert hashlib.sha256(claude_judge.JUDGE_SYSTEM_PROMPT)==hashlib.sha256(openai_judge.JUDGE_SYSTEM_PROMPT) at JudgeRunner construction, or a unit test that compares the two constants) or remove the false claim from the docstring. A unit test asserting the two prompts are equal is the cheapest fix.

### M16. signup() returns User but backend response includes is_superuser the frontend User type omits; also no token issued so user is set but unauthenticated
- **File:** `frontend/src/contexts/AuthContext.tsx:60-63` · **Category:** contract-mismatch · **Finder:** fe-api-state · **Verifier confidence:** high
- **Impact:** `api.signup` returns the created user and AuthContext.signup does `setUser(newUser)` then SignupForm navigates to /dashboard. But signup does NOT issue/store a token (backend /auth/signup returns UserResponse, not a Token; api.ts:166-169 never calls setToken). So after signup `setUser` makes `isAuthenticated` true, ProtectedRoute lets the user into /dashboard, but `api.getToken()` is null → the first protected API call (useDocuments → GET /documents/) returns 401 → interceptor fires `auth:logout`, clears (nonexistent) token, sets user null, and the user is bounced to /login. The user experiences 'account created' → dashboard flashes → immediately kicked to login. Expected flow is to log in after signup. (Secondary: backend UserResponse includes `is_superuser` which the frontend `User` type doesn't model — harmless but a drift.)
- **Evidence:** AuthContext.tsx:61 `const newUser = await api.signup(data); setUser(newUser);` with no token; api.ts signup (166-169) returns `response.data` and never `setToken`. Backend signup returns UserResponse (auth.py:78-85), not a token. useDocuments fires immediately on /dashboard; 401 path in api.ts:93-97 dispatches `auth:logout`.
- **Fix:** After successful signup, call login() with the same credentials (to obtain and store a token) before navigating, or have the backend return a token on signup and store it. Add `is_superuser?: boolean` to the User type for accuracy.

### M17. useDocument polls forever when the background task fails with `anomaly_detection_failed` (status not in stop-set, but also not 'completed')
- **File:** `frontend/src/hooks/useDocuments.ts:21-28` · **Category:** logic · **Finder:** fe-api-state · **Verifier confidence:** high
- **Impact:** The polling predicate keeps polling for statuses `analyzing_anomalies | processing | embedding_completed` and stops (returns false) for anything else. The failure status written by the background task is `anomaly_detection_failed` (upload.py:306). That is NOT in the keep-polling set, so polling correctly STOPS — but the document then sits in `anomaly_detection_failed` and NO frontend code recognizes it: DocumentPage.tsx:27-29 and AnalysisResults.tsx:20-22 only treat the three in-progress statuses as `isAnalyzing`, and useAnomalyReport is gated on `=== 'completed'`. Result: a failed analysis renders as a finished document with zero anomalies and 'No Risks Found' (AnomalyList.tsx:136-148), giving the user a false 'this document is safe' signal instead of an error state. There is no failure UI anywhere for `anomaly_detection_failed` (or a generic `failed`).
- **Evidence:** upload.py:306 `document.processing_status = 'anomaly_detection_failed'` on background exception. Frontend grep for failure handling: only the three in-progress statuses appear in DocumentPage/AnalysisResults; no `failed`/`anomaly_detection_failed` branch exists. AnomalyList empty + not-analyzing → renders 'No Risks Found'.
- **Fix:** Add an explicit failure branch: treat `processing_status` containing 'failed' as an error state in DocumentPage/AnomalyList and show a 'Analysis failed — re-run' message instead of 'No Risks Found'. Keep polling stopped for failed states.

### M18. Frontend sends `suggested_severity` in feedback payload but backend silently drops it → wrong-severity signal lost
- **File:** `frontend/src/types/index.ts:204-210` · **Category:** contract-mismatch · **Finder:** fe-api-state · **Verifier confidence:** high
- **Impact:** `FeedbackPayload` declares `suggested_severity` and FeedbackButtons.tsx:104-107 sends it as a first-class field on the wrong-severity path. The backend `FeedbackRequest` (anomaly.py:353-371) defines only `user_action`, `feedback_text`, `confidence_at_detection` and is a plain Pydantic BaseModel (extra fields ignored by default). So `suggested_severity` is dropped server-side. The only place the suggested severity survives is the `[suggested_severity=...]` prefix the component also stuffs into `feedback_text` — but `feedback_text` is merely `logger.info`'d (anomalies.py:920-922) and not persisted to any FeedbackEvent in the current code path. Net: the user's structured 'this should be X severity' input is silently discarded. The frontend type advertises a contract the backend does not honor.
- **Evidence:** types/index.ts:209 `suggested_severity?: 'critical' | 'high' | 'medium' | 'low';` sent at FeedbackButtons.tsx:106 `suggested_severity: suggestedSeverity` — but FeedbackRequest schema (anomaly.py:353-371) has no such field and no `model_config` allowing/capturing extras; handler only logs `feedback_text`.
- **Fix:** Either add `suggested_severity` to the backend `FeedbackRequest` and persist it, or remove the field from `FeedbackPayload`/`FeedbackButtons` to stop advertising a non-functional contract. At minimum keep the `[suggested_severity=...]` text encoding AND persist `feedback_text`.

### M19. Login/Signup error toast is always the generic fallback (reads wrong error shape)
- **File:** `frontend/src/components/auth/LoginForm.tsx:26` · **Category:** contract-mismatch · **Finder:** fe-auth-doc-pages · **Verifier confidence:** high
- **Impact:** The axios response interceptor in services/api.ts (lines 81-147) catches every error and REJECTS a reshaped object {message, status, originalError} — the original AxiosError is nested under .originalError, so the top-level object has no .response property. LoginForm reads (error as {response?:{data?:{detail?:string}}})?.response?.data?.detail, which is always undefined on a rejected request, so the toast always shows the hardcoded fallback 'Login failed. Please check your credentials.' regardless of the real server message (e.g. 'Too many requests', 'Service temporarily unavailable', 422 validation detail). SignupForm has the identical defect (SignupForm.tsx:39-41), so a duplicate-email or validation message from the server is never shown. (This is the tracked error-shape bug; confirmed it manifests in both auth forms — the correct field is error.message.)
- **Evidence:** api.ts:141-147  const friendlyError = { message, status: error.response?.status, originalError: error }; return Promise.reject(friendlyError);
LoginForm.tsx:26  const message = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Login failed. Please check your credentials.';
SignupForm.tsx:39-41  (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Signup failed. Please try again.';
- **Fix:** Read the reshaped field: const message = (error as { message?: string })?.message || 'Login failed...'; (matches what useDocuments hooks already do correctly with e?.message). Apply the same to SignupForm.

### M20. Dashboard only fetches first 10 documents — stats and list silently truncated
- **File:** `frontend/src/hooks/useDocuments.ts:8-11` · **Category:** data-integrity · **Finder:** fe-auth-doc-pages · **Verifier confidence:** high
- **Impact:** useDocuments calls api.getDocuments() with no arguments, and api.getDocuments defaults to skip=0, limit=10 (services/api.ts:224). The hook returns only response.documents (the 10-row page) and discards response.total. DashboardPage then renders documents.length as the 'Documents / Total analyzed' stat and computes totalAnomalies, highRiskDocs, and totalClauses by reducing over ONLY those 10 documents (DashboardPage.tsx:39-41,77). There is no pagination UI and no way to load more. A user with more than 10 documents sees a wrong document count, wrong aggregate anomaly/clause/high-risk numbers, and is unable to open documents beyond the 10th from the dashboard.
- **Evidence:** useDocuments.ts:8-11  queryFn: async () => { const response = await api.getDocuments(); return response.documents; }
api.ts:224  async getDocuments(skip = 0, limit = 10)  // hardcoded page size, never overridden
DashboardPage.tsx:39  const totalAnomalies = documents?.reduce((sum, doc) => sum + (doc.anomaly_count || 0), 0) || 0;  // over <=10 docs
DashboardPage.tsx:77  {documents?.length || 0}  // shows 10 max, response.total ignored
- **Fix:** Either request a high limit explicitly (api.getDocuments(0, 1000)), implement pagination using response.total/skip/limit, or compute the stat cards from response.total / a dedicated aggregate endpoint rather than the truncated page.

### M21. useDocument polling stops permanently on a transient fetch error after upload navigation
- **File:** `frontend/src/hooks/useDocuments.ts:21-28` · **Category:** error-handling · **Finder:** fe-auth-doc-pages · **Verifier confidence:** high
- **Impact:** The refetchInterval for useDocument reads query.state.data?.processing_status. If a poll request errors (e.g. a transient 404 from read-replica lag right after navigating to /documents/:id, a 500, or a network blip), query.state.data is undefined, so the interval function returns false and polling stops permanently. With the global retry:1 default the query gives up after two attempts and DocumentPage shows 'Failed to load document.' with no further auto-retry, even though the document exists and will resolve momentarily. The user is stuck until a manual refresh.
- **Evidence:** useDocuments.ts:21-28  refetchInterval: (query) => { const status = query.state.data?.processing_status; if (status === 'analyzing_anomalies' || ...) return 3000; return false; }  // undefined status on error → false → polling dies
- **Fix:** Keep polling while the query is in an error/loading state with unknown status: e.g. if (query.state.status === 'error') return 3000; before the status check, or treat undefined status (not yet a terminal value) as 'keep polling' with a bounded retry count.

### M22. Synchronous ML embedding (model.encode) blocks the event loop on every upload and Q&A request
- **File:** `backend/app/services/embedding_service.py:91, 128` · **Category:** race · **Finder:** x-async · **Verifier confidence:** high
- **Impact:** create_embedding/batch_create_embeddings are declared async but call the synchronous, CPU/ML-bound sentence-transformers `self.model.encode(...)` directly on the event loop with no run_in_executor/to_thread offload. encode() of a multi-hundred-clause document takes hundreds of ms to seconds of pure CPU. Because all FastAPI routes run on a single event loop, this freezes the ENTIRE server (health checks, other users' requests, in-flight background detection) for the duration. DocumentProcessor deliberately offloads PDF parsing to an executor (document_processor.py:109/154/198), so embedding NOT being offloaded is an inconsistency that defeats that effort. Called from the upload pipeline (document_pipeline.py:361) and the user-facing Q&A endpoint (query.py:161).
- **Evidence:** async def create_embedding(...):
    ...
    embedding = self.model.encode(text, convert_to_numpy=True)   # blocking, on the loop
...
async def batch_create_embeddings(...):
    ...
    embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)  # blocking, on the loop
- **Fix:** Wrap encode() in await asyncio.get_running_loop().run_in_executor(None, ...) (or asyncio.to_thread) exactly like DocumentProcessor does for PDF parsing, so CPU-bound embedding work doesn't block the loop.

### M23. Pinecone client calls are synchronous network I/O inside async methods, blocking the event loop
- **File:** `backend/app/services/pinecone_service.py:149, 210, 266, 304` · **Category:** race · **Finder:** x-async · **Verifier confidence:** high
- **Impact:** PineconeService methods are async but call the synchronous Pinecone SDK over the network with no executor offload: self.index.upsert (upsert_chunks, batched in a loop), self.index.query (query), self.index.delete (delete_document), self.index.describe_index_stats (get_index_stats/initialize). Each is a blocking HTTP round-trip executed on the event loop. During an upload, upsert_chunks loops over batches synchronously; during Q&A, query() blocks; during delete, delete() blocks. All other concurrent requests stall for the full network latency of each Pinecone call.
- **Evidence:** for i in range(0, len(vectors), BATCH_SIZE):
    batch = vectors[i : i + BATCH_SIZE]
    self.index.upsert(vectors=batch, namespace=namespace)   # sync network call on the loop
...
results = self.index.query(vector=query_embedding, ...)      # sync network call on the loop
...
self.index.delete(filter={"document_id": document_id}, namespace=namespace)  # sync on the loop
- **Fix:** Offload each blocking Pinecone call via run_in_executor/asyncio.to_thread, or use the Pinecone async client. At minimum wrap upsert/query/delete/describe_index_stats.

### M24. bcrypt password hashing/verification runs synchronously on the event loop in async auth routes
- **File:** `backend/app/utils/security.py:28, 44` · **Category:** race · **Finder:** x-async · **Verifier confidence:** high
- **Impact:** verify_password (pwd_context.verify) and get_password_hash (pwd_context.hash) perform bcrypt work that is intentionally CPU-expensive (~100-300ms at default cost). They are called directly from `async def login` (auth.py:117) and `async def signup` (auth.py:67) with no executor offload. Each login/signup blocks the single event loop for the full bcrypt duration, so concurrent logins serialize and unrelated requests stall. A burst of login attempts (or a credential-stuffing attack) becomes a trivial event-loop DoS.
- **Evidence:** auth.py:117  if not user or not verify_password(form_data.password, user.hashed_password):
security.py:28  return pwd_context.verify(truncated_password, hashed_password)  # blocking bcrypt on the loop
- **Fix:** Run bcrypt verify/hash in a thread (await asyncio.to_thread(pwd_context.verify, ...)) or make the auth routes def (sync) so Starlette runs them in its threadpool.

### M25. Frontend error toasts read error.response.data.detail, but the axios interceptor reshapes every error to {message,status,originalError} — detail is always undefined
- **File:** `frontend/src/hooks/useQuery.ts:10` · **Category:** error-handling · **Finder:** x-contract · **Verifier confidence:** high
- **Impact:** The axios response interceptor (api.ts:140-147) rejects with a flat object `{ message, status, originalError }` — it does NOT preserve a `response` property. Yet useQuery.ts reads `(error as {response?:{data?:{detail?:string}}})?.response?.data?.detail` with no fallback to `.message`, so the BE's specific 'detail' message is never shown; the toast is always the hardcoded generic 'Failed to query document'. Same pattern in LoginForm.tsx:26 and SignupForm.tsx:40 (these have no `.message` fallback either, so they always show their generic strings). This is the same class as the known LoginForm issue (b); flagging the additional confirmed instances. Note: useDocuments.ts and useFeedback.ts read `.message` FIRST, so they happen to work.
- **Evidence:** api.ts:141-147 `const friendlyError = { message, status, originalError }; return Promise.reject(friendlyError);` (no `response` key). useQuery.ts:10 `const message = (error as {...})?.response?.data?.detail || 'Failed to query document';` — `.response` is undefined on the reshaped error so detail is always undefined.
- **Fix:** Either (a) have the interceptor attach the original detail to the friendly object (e.g. `detail: error.response?.data?.detail`) and/or keep `response` intact, or (b) make all consumers read `e?.message` first (as useDocuments already does): `const message = e?.message || e?.response?.data?.detail || '...';`.

### M26. GET /anomalies/performance always returns 500 (KeyError + AttributeError on removed feedback machinery)
- **File:** `backend/app/api/v1/anomalies.py:126-176` · **Category:** crash · **Finder:** x-security · **Verifier confidence:** high
- **Impact:** The superuser-gated performance endpoint references attributes/keys that no longer exist after the simple-engineering refactor removed ActiveLearningManager. `feedback_stats` is hard-coded as {"total_feedback": 0, "positive": 0, "negative": 0}, yet the code reads feedback_stats['dismissal_rate'] (line 143, 156, 158, 186), feedback_stats['total_feedback_collected'] (171), feedback_stats['calibrator_fitted'] (176), etc. — all KeyErrors. Before that, line 147 reads detector.confidence_calibrator.is_fitted, but AnomalyDetector has no confidence_calibrator attribute (grep confirms only detect_anomalies + calculate_document_risk_score exist) → AttributeError. Any superuser hitting this monitoring endpoint gets a 500 with a generic 'Failed to fetch performance metrics' message; the feature is entirely non-functional.
- **Evidence:** feedback_stats = {"total_feedback": 0, "positive": 0, "negative": 0}
...
if detector.confidence_calibrator.is_fitted:  # AttributeError
...
false_positive_rate = feedback_stats['dismissal_rate']  # KeyError
- **Fix:** Either delete the endpoint (the active-learning/calibration machinery it reports on was removed) or rewrite it to compute real metrics: derive dismissal_rate/false_positive_rate from a persisted feedback table, drop the confidence_calibrator reference, and populate feedback_stats keys that PerformanceMetrics actually requires.

### M27. Background anomaly-detection task can leave documents stuck in 'analyzing_anomalies' forever
- **File:** `backend/app/api/v1/upload.py:282-298` · **Category:** data-integrity · **Finder:** x-security · **Verifier confidence:** high
- **Impact:** In run_anomaly_detection_background, when detection succeeds the document status is set to 'completed' ONLY inside `if document:` after a re-query. If detect_anomalies succeeds but the final `db.query(Document)...first()` returns None (e.g. document deleted by the user mid-analysis, or a replica/visibility lag), the else-branch only logs an error and the status is never advanced from 'analyzing_anomalies'. The except-handler that sets 'anomaly_detection_failed' is not reached because no exception was raised. The document then permanently reports 'still processing' to the frontend (GET /report returns HTTP 202 forever at line 638-642), and Q&A is degraded. Because the background task swallows the case, there is no retry or terminal failure state.
- **Evidence:** document = db.query(Document).filter(Document.id == document_id).first()
if document:
    document.processing_status = "completed"
    db.commit()
...
else:
    logger.error(f"Document {document_id} not found when updating anomaly results")  # status left as analyzing_anomalies
- **Fix:** Guarantee a terminal status: re-fetch and update status in a finally-style block, or if the document vanished, treat it as done/abort cleanly. At minimum add a watchdog/timeout that flips long-stuck 'analyzing_anomalies' rows to a failed state so the UI doesn't hang.

## LOW (37)

### L1. get_anomalies severity filter accepts 'critical' in code but docs/UI advertise only low/medium/high; mismatch silently returns empty + double-counts in 'high' bucket
- **File:** `backend/app/api/v1/anomalies.py:404-406, 440-441` · **Category:** logic · **Finder:** be-anomalies-api · **Verifier confidence:** high
- **Impact:** The severity Query param description says 'Filter by severity: low, medium, high' and there is no validation/enum, so an arbitrary value (e.g. 'High', 'severe', typo) is lowercased and used in an equality filter, silently returning an empty list rather than a 422 — a confusing contract for clients. More concretely, the response's high_risk_count (line 509) only counts severity=='high' and exposes a separate critical_risk_count, but the frontend AnomalyListResponse maps high/medium/low and the report DB-path lumps critical into high — inconsistent bucketing of 'critical' across endpoints can under/over-report counts to the UI. Lower severity since it degrades correctness rather than crashing.
- **Evidence:** severity: Optional[str] = Query(None, description="Filter by severity: low, medium, high")
...
if severity:
    query = query.filter(Anomaly.severity == severity.lower())   # no membership check; 'critical' valid in DB but absent from docs
- **Fix:** Constrain severity to a Literal/enum (low|medium|high|critical) so invalid values 422 instead of silently returning []; align the documented filter values with the DB enum and the bucketing used in get_anomaly_report.

### L2. JWT verification does not require the `exp` claim — tokens minted without expiry are accepted forever
- **File:** `backend/app/api/deps.py:54-65` · **Category:** security · **Finder:** be-auth-security · **Verifier confidence:** high
- **Impact:** `jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])` is called with no `options` enforcing required claims. python-jose only validates `exp` if it is PRESENT; a token with no `exp` claim decodes successfully (verified empirically: `jwt.decode` of `{'sub':'u2'}` returns the payload with no error). create_access_token always adds exp today, but get_current_user trusts ANY validly-signed token. If a token is ever issued elsewhere (e.g. the dead `app/utils/auth.py` duplicate, a future script, or a manually crafted token signed with a leaked/weak SECRET_KEY) without `exp`, it is accepted as a permanent credential. There is also no `require_exp`/`verify_exp` hardening. Same gap exists in `decode_access_token` in utils/security.py.
- **Evidence:** payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
user_id: str = payload.get("sub")
if user_id is None:
    raise credentials_exception
# no options={'require': ['exp'], 'verify_exp': True}
- **Fix:** Pass `options={"require": ["exp", "sub"], "verify_exp": True}` (and a `verify_signature` is default-on) to jwt.decode in both deps.py and utils/security.py so tokens lacking exp are rejected.

### L3. login leaks corrupt/legacy password-hash rows as 500 instead of 401
- **File:** `backend/app/api/v1/auth.py:117` · **Category:** error-handling · **Finder:** be-auth-security · **Verifier confidence:** high
- **Impact:** verify_password calls pwd_context.verify(plain, hashed). If a user row has a non-bcrypt or malformed hashed_password (empty string, legacy migration artifact, partially-written value), passlib raises UnknownHashError ('') or ValueError ('$2b$broken') rather than returning False. Verified empirically: verify_password('x','') -> UnknownHashError; verify_password('x','$2b$broken') -> ValueError. login() does not wrap verify_password in try/except, so such a row yields an unhandled 500 on login (and is an availability/enumeration signal: a 500 vs 401 distinguishes 'account exists with bad hash'). Note hashed_password is NOT-NULL so empty-string requires a bad write, but corrupt/legacy hashes are plausible.
- **Evidence:** if not user or not verify_password(form_data.password, user.hashed_password):
    ... 401
# verify_password -> pwd_context.verify can raise UnknownHashError/ValueError, uncaught
- **Fix:** Wrap verify_password in try/except (passlib.exc.UnknownHashError, ValueError) and treat any exception as a failed verification (return False / raise the same 401), so corrupt hashes never produce a 500 or a distinguishable response.

### L4. ProxyHeadersMiddleware trusted_hosts passed a raw space-separated string, not a list — trusted-proxy parsing likely wrong, enabling X-Forwarded-For spoofing of rate-limit keys
- **File:** `backend/app/main.py:152-153` · **Category:** security · **Finder:** be-auth-security · **Verifier confidence:** high
- **Impact:** TRUSTED_PROXY_IPS is a plain str default '127.0.0.1' (config.py line 22) and is passed directly as `trusted_hosts=trusted_proxy` to uvicorn's ProxyHeadersMiddleware. ProxyHeadersMiddleware expects either '*' or a list/comma-separated set of hosts; a space-separated string like '127.0.0.1 10.0.0.5' is not parsed into multiple hosts (it splits on commas, not spaces), so multi-proxy configs silently fail to trust the real proxy. More importantly, the rate limiter (rate_limit.py) keys on get_remote_address, which reads X-Forwarded-For only when the peer is a trusted proxy. If the trusted-hosts set is misconfigured (wrong format) the middleware may either ignore XFF (clients behind the real proxy all share the proxy IP → one shared rate-limit bucket, easy DoS of all users) or, if set to '*', trust XFF from anyone (clients spoof XFF to evac their own per-IP limit and bypass the 10/hour signup and 20/hour login caps → credential-stuffing / enumeration). Either way the per-key rate limiting is not reliably correct.
- **Evidence:** TRUSTED_PROXY_IPS: str = "127.0.0.1"  # "Space-separated IPs"
...
trusted_proxy = getattr(settings, "TRUSTED_PROXY_IPS", "127.0.0.1")
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=trusted_proxy)  # str, comment claims space-separated
- **Fix:** Parse TRUSTED_PROXY_IPS into a list (split on comma/space) and pass the list to trusted_hosts; document that the format must match what ProxyHeadersMiddleware expects (comma-separated or list). Verify in the deployed env that the actual upstream proxy IP (Supabase/Render/etc.) is included so XFF is honored for exactly that hop and not for arbitrary clients.

### L5. Two divergent copies of the password/JWT utilities; dead app/utils/auth.py lacks bcrypt truncation and a hardcoded 15-min default
- **File:** `backend/app/utils/auth.py:16-23, 42` · **Category:** logic · **Finder:** be-auth-security · **Verifier confidence:** high
- **Impact:** app/utils/auth.py duplicates verify_password/get_password_hash/create_access_token but does NOT apply the 72-byte truncation that the live app/utils/security.py does, and uses a hardcoded 15-minute default expiry instead of settings.ACCESS_TOKEN_EXPIRE_MINUTES. It is currently dead code (grep shows nothing imports app.utils.auth except v1/auth which imports from utils.security). The risk is regression: if any future caller imports get_password_hash from utils.auth, hashes will differ from the truncated ones written by security.py for >72-byte passwords, causing verification failures / inconsistent behavior across the two modules.
- **Evidence:** # app/utils/auth.py
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)   # NO [:72] truncation, unlike security.py
...
expire = datetime.now(timezone.utc) + timedelta(minutes=15)  # ignores settings
- **Fix:** Delete app/utils/auth.py (it is unused) or re-export from app/utils/security.py so there is a single source of truth for hashing/JWT.

### L6. Timestamp columns are TIMESTAMP WITHOUT TIME ZONE but store tz-aware UTC datetimes → tzinfo silently stripped / shifted; inconsistent with feedback_events
- **File:** `backend/app/models/document.py:48-49` · **Category:** data-integrity · **Finder:** be-db-integrity · **Verifier confidence:** high
- **Impact:** User/Document/Clause/Anomaly/AnalysisLog define `created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))` — `DateTime` (no timezone=True) maps to Postgres TIMESTAMP WITHOUT TIME ZONE. The default produces a tz-AWARE UTC value. On insert, psycopg2 sends the aware value and Postgres stores it after converting to the session TimeZone and DROPPING the offset; on read it comes back NAIVE. Meanwhile feedback_events.created_at uses `DateTime(timezone=True)` (TIMESTAMPTZ). The mix means (a) timestamps from these tables are returned without offset and the report endpoint emits them via `document.updated_at.isoformat()` (anomalies.py:685) with no 'Z'/offset, so the frontend interprets UTC values as local time — wrong displayed times; (b) comparing a naive stored value against `datetime.now(timezone.utc)` (aware) anywhere raises `TypeError: can't compare offset-naive and offset-aware datetimes`. If the DB session TimeZone is not UTC, the stored wall-clock is also shifted.
- **Evidence:** document.py:48 `created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)` (DateTime, naive column) vs feedback_event.py:42-46 `created_at = Column(DateTime(timezone=True), ...)`. anomalies.py:685 serializes `document.updated_at.isoformat()` for analysis_date with no tz normalization.
- **Fix:** Make all timestamp columns `DateTime(timezone=True)` (and migrate existing columns to TIMESTAMPTZ) so offsets are preserved consistently, OR standardize on naive-UTC everywhere and store `datetime.utcnow()`. Pick one and apply uniformly to avoid the naive/aware comparison crashes and the frontend off-by-timezone display.

### L7. feedback_events.anomaly_id / document_id have no foreign keys; user_id FK has no ondelete → orphan rows and FK-violation 500 on user delete
- **File:** `backend/app/models/feedback_event.py:35-37` · **Category:** data-integrity · **Finder:** be-db-integrity · **Verifier confidence:** high
- **Impact:** feedback_events.anomaly_id (line 36) and document_id (line 37) are plain String columns with NO ForeignKeyConstraint (the migration d2a4b5 only adds an FK for user_id). So feedback rows can reference anomalies/documents that don't exist or that get deleted, leaving permanently orphaned rows that the hydration query would load and try to act on. Separately, the user_id FK (`ForeignKeyConstraint(['user_id'], ['users.id'])`) has no `ondelete`, and User has no relationship to FeedbackEvent, so it's not in any ORM cascade. Deleting a user who has feedback rows would raise a ForeignKey violation → IntegrityError → 500 (no user-delete endpoint exists today, so latent). Because the write path is currently broken (see other finding) this is low impact now, but it's a schema design defect to fix alongside reviving the feature.
- **Evidence:** feedback_event.py:36 `anomaly_id = Column(String(36), nullable=False)` and :37 `document_id = Column(String(36), nullable=True)` — no ForeignKey. Migration d2a4b5 only declares `sa.ForeignKeyConstraint(['user_id'], ['users.id'])` (no ondelete) and no FK for anomaly_id/document_id.
- **Fix:** Add ForeignKeyConstraint for anomaly_id→anomalies.id and document_id→documents.id with ondelete='CASCADE', and add ondelete='CASCADE' to the user_id FK (plus an ORM relationship on User if cascade-on-delete is desired). Do this in a migration before re-enabling feedback writes.

### L8. Anomaly.risk_title is persisted but absent from AnomalyResponse schema and dropped by every AnomalyResponse serializer → frontend contract gap
- **File:** `backend/app/schemas/anomaly.py:154-181` · **Category:** contract-mismatch · **Finder:** be-db-integrity · **Verifier confidence:** high
- **Impact:** The Anomaly model has risk_title (anomaly.py:22) and the upload background task persists it (upload.py:272). However AnomalyBase/AnomalyResponse (schemas/anomaly.py:154-181) do not declare risk_title, and the three AnomalyResponse constructions in the anomalies router (lines 359-372, 486-504, 551-565) never pass it. So the GET /anomalies/{document_id}, /anomalies/detail/{id}, and re-analyze responses silently drop the LLM-generated title the column exists to surface, forcing the frontend back to a generic placeholder for those endpoints. (The /report endpoint's _anomaly_to_ranked_dict at line 52 DOES include risk_title, so the data is reachable there, confirming the column is intentionally meant to be exposed.) Not a crash — Pydantic ignores the extra attribute — but the persisted field never reaches the AnomalyResponse consumers.
- **Evidence:** Model: anomaly.py:22 `risk_title = Column(String(200), nullable=True)`. Schema AnomalyBase has no risk_title field (anomaly.py:154-165). Serializers at anomalies.py:359-372 / 486-504 / 551-565 omit risk_title, while _anomaly_to_ranked_dict (anomalies.py:52) includes it.
- **Fix:** Add `risk_title: Optional[str] = None` to AnomalyResponse (or AnomalyBase) and pass `risk_title=a.risk_title` in the three AnomalyResponse(...) constructions so the persisted title reaches the list/detail endpoints.

### L9. Dedup Pass 2 docstring claims missing-protection findings are never merged, but they carry a non-empty clause_number and bypass the skip guard
- **File:** `backend/app/core/anomaly_detector.py:226-228, 264-278` · **Category:** logic · **Finder:** be-detection-core · **Verifier confidence:** high
- **Impact:** The Pass-2 docstring states: 'Findings with no clause_number (e.g. missing-protection findings) are NEVER merged here'. The skip relies on `if not clause` (line 266). But missing-protection findings are emitted with clause_number = 'MISSING:<pid>' (llm_clause_detector.py line 968), a non-empty string, so they are NOT skipped — they fall through into the by_clause merge map. In practice each protection id is unique so two missing-protection findings never share a 'MISSING:pid' key and no incorrect merge occurs today, so this is a latent contract bug rather than an active data-loss bug. However the comment's assumption is false, so any future change that lets two findings share a MISSING key (or a real clause and a MISSING clause collide) would silently collapse a true positive. The guard does not implement the documented behavior.
- **Evidence:** # llm_clause_detector.py:968
"clause_number": f"MISSING:{pid}",
...
# anomaly_detector.py:265-266
clause = str(f.get("clause_number") or "").strip()
if not clause:  # MISSING:pid is truthy, so this is FALSE -> not skipped
    result.append(f); continue
- **Fix:** Make the guard match the documented intent: skip findings whose detection_source == 'missing_protection' (or whose clause_number startswith 'MISSING:') from the Pass-2 location-based merge, instead of relying on emptiness of clause_number.

### L10. Cost-cap pre-flight check races under concurrent voting; per-doc LLM spend cap can be blown past
- **File:** `backend/app/core/llm_clause_detector.py:552-557, 607-620, 749` · **Category:** race · **Finder:** be-detection-core · **Verifier confidence:** high
- **Impact:** Self-consistency voting fans out ALL critical-finding votes concurrently via asyncio.gather (line 552-557). Each _majority_vote_critical reads the shared self._cost_tracker_usd to project cost and decide whether to skip (line 612-613), but the tracker is only incremented later, inside _single_vote_call (line 749). Because every concurrent vote reads the tracker BEFORE any of them has incremented it, they all see the same stale (low) value and all pass the cap check. With up to MAX_CRITICAL_VOTES_PER_DOC=5 criticals * 3 calls each = 15 calls launched in parallel, the per-document spend can substantially exceed settings.MAX_LLM_USD_PER_DOC (default $0.50). The cap is read-modify-write on a non-atomic float with no lock. The cap therefore does not actually bound concurrent spend; it only bounds spend in the (non-existent) serial case.
- **Evidence:** tasks = [self._majority_vote_critical(findings[i], ...) for i in critical_indices]
voted = await asyncio.gather(*tasks, ...)   # all criticals concurrent
...
projected = self._cost_tracker_usd + per_call_cost * SELF_CONSISTENCY_VOTES  # reads stale shared value
if projected > settings.MAX_LLM_USD_PER_DOC: ... return None
...
# cost only added AFTER the check, in a different coroutine:
self._cost_tracker_usd += self._estimate_call_cost_usd(...)  # line 749, no lock
- **Fix:** Serialize the cap-relevant section (reserve projected cost before awaiting) by incrementing self._cost_tracker_usd with the projected amount inside _majority_vote_critical under an asyncio.Lock, or run the per-critical votes sequentially, or pre-reserve cost atomically before launching the fan-out so each vote's projection reflects already-committed spend.

### L11. Multi-clause range/list expansion is immediately undone by dedup Pass 1, so the documented 'finding spans several clauses' behavior never reaches output
- **File:** `backend/app/core/llm_clause_detector.py:1221-1263, 1305-1319` · **Category:** logic · **Finder:** be-detection-core · **Verifier confidence:** high
- **Impact:** _resolve_clause_refs is documented to expand a compound ref like '28-30' or '2, 4, 28' to EVERY member clause 'so a finding spanning several clauses is not collapsed to a single clause' (line 1228-1229), and _parse_response duplicates the finding across each resolved clause_number (line 1305-1319) with identical pattern_id and risk_title. But _dedupe_findings Pass 1 (anomaly_detector.py:238-258) keys by pattern_id (or normalized title for novel) and collapses all those duplicates back to ONE finding, keeping a single clause_number. The net effect contradicts the stated design: the multi-clause expansion produces N identical findings that are then re-collapsed to 1, so the work is wasted and the finding ends up attached to whichever single clause sorted/ordered first — not 'spanning several clauses'. For 'novel' findings the title-normalization key can also merge two genuinely different novel risks that happen to share a normalized title across the expanded clauses. Net: expansion + dedup is internally inconsistent; at best a no-op, at worst it loses the multi-clause association the code claims to preserve.
- **Evidence:** # resolve expands one ref into many clause_numbers, parse duplicates the finding:
for clause_num in matched_nums:
    validated.append({... "clause_number": clause_num, "pattern_id": pattern_id or None, "risk_title": risk_title ...})
# then dedup Pass 1 collapses by pattern_id/title back to one:
if pid and pid not in ("novel","none"): key = "pattern:"+pid  # all N copies share this key -> 1 survives
- **Fix:** Decide on one behavior: either keep multi-clause findings distinct (give Pass 1 a composite key that includes clause_number, or exempt expanded multi-clause sets from Pass 1), or stop expanding compound refs to N findings in _parse_response (resolve to the single most-representative clause) so the documented intent and the dedup behavior agree.

### L12. Vote tie/split logic keeps original severity but still marks was_voted and reports a 'split' agreement, which mislabels low-confidence singletons
- **File:** `backend/app/core/llm_clause_detector.py:674-693` · **Category:** logic · **Finder:** be-detection-core · **Verifier confidence:** high
- **Impact:** In _majority_vote_critical, when only 1 of 3 vote calls returns valid JSON, len(votes)==1 so the 1-1-1 branch (line 675) is skipped and the tie branch (line 679, needs >=2 distinct) is skipped, so it takes top[0][0] as voted_severity with agreement f'{1}/{1}'. A single surviving vote thus DEMOTES (or changes) a critical finding based on one model call, which defeats the purpose of self-consistency (the comment at line 691-693 acknowledges 'low-confidence' but still applies the change rather than keeping the original). Conversely, when exactly 2 valid votes disagree (1-1), line 679-683 correctly keeps original as 'split'. The 1-of-3 case is the inconsistency: a lone vote can silently flip a critical to medium/low, removing it from the high_severity bucket entirely. Since voting only runs on criticals and only demotes downstream, a transient 2-of-3 call failure can erase a genuine critical based on a single LLM response.
- **Evidence:** if len(votes) == 3 and len(set(votes)) == 3: voted_severity = original_severity  # only the 3-valid case
elif len(top) >= 2 and top[0][1] == top[1][1]: voted_severity = original_severity
else:
    voted_severity = top[0][0]   # 1 valid vote -> takes that single vote, can demote critical
    ... agreement = f"{top[0][1]}/{len(votes)}"  # e.g. '1/1'
- **Fix:** Require a minimum quorum (e.g. >=2 valid votes) before allowing a severity change; if fewer than 2 valid votes returned, keep original_severity and mark agreement as 'insufficient' rather than applying a single-vote demotion.

### L13. Bare/loose keywords in risk_indicators patterns produce false-positive clause metadata (account_inactivity_reclaim, data_throttling, warrantless_law_enforcement)
- **File:** `backend/app/core/risk_indicators.py:473-489 (account_inactivity_reclaim), 933-943 (data_throttling), 381-397 (warrantless_law_enforcement)` · **Category:** logic · **Finder:** be-patterns-data · **Verifier confidence:** high
- **Impact:** Several RiskIndicators patterns key off keywords that are far too generic, causing benign clauses to be tagged with a (medium/critical) risk indicator in clause_metadata (risk_indicators / pattern_severity, stored on the Clause row). account_inactivity_reclaim lists the bare phrases '6 months' and 'six months', so any clause mentioning six months (warranty period, support SLA) is tagged MEDIUM 'account_inactivity_reclaim'. data_throttling lists 'network management' and 'prioritization', so a benign 'we use reasonable network management' clause is tagged MEDIUM. warrantless_law_enforcement includes 'law enforcement partnership', and because the indicator name normalizes into CriticalPatterns.ALWAYS_CRITICAL, ANY clause containing that phrase (even a benign cooperation statement) is elevated to severity 'critical' in clause metadata. These wrong values are persisted as clause_metadata.pattern_severity / risk_indicators. Impact is bounded because this metadata does not drive the user-facing alert list (that comes from the LLM), but it is wrong stored data that any future consumer of clause_metadata (or a reviewer reading the row) will trust.
- **Evidence:** account_inactivity_reclaim keywords include bare "6 months","six months"; reproduced: 'We provide a six months warranty on all hardware purchases.' -> detect_indicators returns account_inactivity_reclaim/medium. data_throttling keywords include 'network management','prioritization'; 'We use reasonable network management techniques...' -> data_throttling/medium. warrantless_law_enforcement keyword 'law enforcement partnership'; 'We may share information with law enforcement partnership programs to protect users.' -> warrantless_law_enforcement/critical (is_critical_pattern True via ALWAYS_CRITICAL normalization at lines 1153-1166).
- **Fix:** Drop the bare duration tokens ('6 months','six months') from account_inactivity_reclaim and require co-occurrence with an inactivity/reclaim term. Remove or tighten 'network management'/'prioritization' for data_throttling (require 'throttle'/'reduce speeds'/'deprioritization'). For warrantless_law_enforcement, require explicit 'without a warrant'/'without judicial' wording (the pattern already lists those) and drop 'law enforcement partnership' which does not imply warrantlessness.

### L14. Dead detection code in risk_indicators (detect_pattern_clusters / calculate_indicator_score / get_risk_category_distribution / DANGEROUS_PATTERN_CLUSTERS) — references stale pattern keys, can mislead future use
- **File:** `backend/app/core/risk_indicators.py:1039-1095 (clusters), 1256-1335 (cluster/score helpers)` · **Category:** logic · **Finder:** be-patterns-data · **Verifier confidence:** high
- **Impact:** detect_pattern_clusters, calculate_indicator_score and get_risk_category_distribution have zero callers in app/. The DANGEROUS_PATTERN_CLUSTERS they reference list pattern names (e.g. 'biometric_data_collection','warrantless_law_enforcement','digital_ownership_illusion') that exist as HIGH_RISK_PATTERNS keys, but the surveillance_cluster requires min_patterns=3 and combines keys whose keyword sets overlap, and the helper is never invoked in the live pipeline (the 6-stage pipeline was deleted per anomaly_detector.py docstring). This is not a live wrong-output bug, but it is stale detection data/logic that a maintainer could wire back in expecting it to work against the current catalog — and several cluster member names (e.g. 'unlimited_liability' appears in clusters and HIGH_RISK_PATTERNS, but 'biometric_data_collection' is elevated to critical, changing the severity the cluster assumes). Flagging so it is not mistaken for active, correct code.
- **Evidence:** grep for detect_pattern_clusters / calculate_indicator_score / get_risk_category_distribution callers across app/ returns only their own def lines (no consumers). anomaly_detector.py docstring: 'retired the 6-stage pipeline ... Stages 2-5 were subtractive'. The only live consumer of RiskIndicators is document_pipeline._prepare_clause_records, which calls detect_indicators and _calculate_max_severity only.
- **Fix:** Delete the unused cluster/score helpers and DANGEROUS_PATTERN_CLUSTERS, or move them behind an explicit, tested entrypoint. If kept, add a module note that they are not part of the live detection flow.

### L15. Catalog 'aliases' field is populated but never rendered into the LLM prompt — dead anchor data, weakening recall it was meant to provide
- **File:** `backend/app/core/risk_patterns.py:19, 37, 53 (and every entry with 'aliases')` · **Category:** contract-mismatch · **Finder:** be-patterns-data · **Verifier confidence:** high
- **Impact:** RiskPattern declares an 'aliases' field documented as 'alternate phrasings the LLM should also recognize', and ~24 patterns populate it (e.g. sale_of_personal_data_without_consent -> ['sell your data','transfer for monetary consideration']; sole_remedy_company_discretion -> ['at Apple's option', ...]). But _render_patterns_block() in llm_clause_detector.py only emits id/title/severity/category/description/example — it never includes aliases. So none of the alias phrasings are ever shown to the LLM. The aliases were specifically added as recognition anchors for hard-to-detect patterns (statute-of-limitations 'time-bar', DNT 'GPC', etc.); their omission means the catalog silently under-delivers the few-shot grounding its authors intended, with no error. Same dead-field issue applies to the 'keywords' field on ExpectedProtection (declared, populated, never consumed).
- **Evidence:** _render_patterns_block (llm_clause_detector.py:1000-1019): `lines.append(f"{i}. [{p.get('id')}] {p.get('title')} (default: {p.get('severity')}, category: {p.get('category')})")` ... `lines.append(f"   What it looks like: {p.get('description', '')}")` ... `ex = p.get("example")` — no reference to p.get('aliases'). grep for 'aliases' across app/ shows only definitions in risk_patterns.py, zero consumers. grep for protection 'keywords' consumption returns nothing.
- **Fix:** Render aliases in _render_patterns_block, e.g. append `Also phrased as: "alias1"; "alias2"` when p.get('aliases') is non-empty. Either consume ExpectedProtection['keywords'] similarly in the protections block, or delete the field to avoid implying it does something.

### L16. Direct index `metadata['text']` can raise KeyError → 500 if a retrieved vector lacks text metadata
- **File:** `backend/app/api/v1/query.py:211-228` · **Category:** error-handling · **Finder:** be-query-main · **Verifier confidence:** high
- **Impact:** While building context and citations the code indexes `metadata['text']` directly (three times: lines 212, 225, 227) instead of `.get()`, even though every other field (section, clause_number, clause_id) uses `.get()` with a default. `pinecone_service.query` returns `metadata = match.get("metadata", {})`, i.e. an empty dict when a match has no metadata. Any vector retrieved without a `text` key (a malformed/externally-upserted vector, or a future schema change) makes `metadata['text']` raise KeyError, caught by the broad handler at query.py:304 and surfaced as a generic 500 'Query processing failed.' The current chunker always sets text, so probability is low, but the inconsistency is a latent crash and the failure mode (500 on an otherwise valid query) is user-facing.
- **Evidence:** query.py:212 `f"Content: {metadata['text']}"`; query.py:225-227 `metadata["text"][:300] + "..." if len(metadata["text"]) > 300 else metadata["text"]`. pinecone_service.py:225 returns `"metadata": match.get("metadata", {})` (empty dict possible).
- **Fix:** Use `text = metadata.get("text", "")` once and skip/guard matches with empty text, or default safely so a missing field can't 500 the request.

### L17. Unreachable / dead exception handler in lifespan masks intent (second `except Exception` on same try)
- **File:** `backend/app/main.py:93-94` · **Category:** error-handling · **Finder:** be-query-main · **Verifier confidence:** high
- **Impact:** The embedding-init `try` opened at line 79 already has a catch-all `except Exception as e:` at line 85. Lines 90-92 are comments, and line 93 introduces a SECOND `except Exception as e:` clause attached to the same try. Python accepts this syntactically (it parses), but the first catch-all consumes every exception, so the line-93 handler ('Active learning hydration check skipped') is permanently unreachable dead code. More importantly it signals a botched refactor: the active-learning init block this handler was meant to guard was deleted, leaving a stray handler. If a future edit relies on this handler running, it silently won't. No runtime failure today, but it is misleading and brittle.
- **Evidence:** main.py:79 `try:` (embedding init); main.py:85 `except Exception as e:` (catches all, sets app.state.embedding=None); main.py:93 `except Exception as e:` / main.py:94 `logger.warning(f"Active learning hydration check skipped: {e}")` — a second catch-all on the same try that can never execute.
- **Fix:** Delete the dead `except` block at lines 90-94 (the active-learning init it guarded was removed in the refactor).

### L18. CLAUDE_TIMEOUT setting is never wired into the Anthropic client; Q&A path has no request timeout
- **File:** `backend/app/services/claude_service.py:40` · **Category:** resource-leak · **Finder:** be-services · **Verifier confidence:** high
- **Impact:** settings.CLAUDE_TIMEOUT (default 60s) is defined in config.py:29 but is never passed to anthropic.AsyncAnthropic(...) nor to messages.create(). The SDK therefore falls back to its built-in default request timeout (600s in anthropic 0.43.0). The detector internal calls wrap each request in asyncio.wait_for(..., timeout=120/180) so they are bounded, but the user-facing Q&A path calls claude_service.create_completion(...) at query.py:245 with NO wait_for wrapper. A hung/slow Claude response there will block the request and its worker for up to 600s instead of the intended 60s, exhausting the worker pool under load and stalling unrelated requests. Additionally, the retry predicate lists the builtin TimeoutError (retry_if_exception_type((anthropic.APIError, TimeoutError))) -- but the SDK raises anthropic.APITimeoutError, never builtin TimeoutError; APITimeoutError happens to be an APIError subclass so it is still retried, making the explicit TimeoutError entry dead/misleading.
- **Evidence:** self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)  # no timeout=
...
# config.py:29  CLAUDE_TIMEOUT: int = 60   <- never referenced anywhere
# query.py:245  answer = await claude_service.create_completion(... )  # no asyncio.wait_for guard
- **Fix:** Pass the configured timeout: anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=settings.CLAUDE_TIMEOUT). Optionally also accept a per-call timeout via self.client.with_options(timeout=...). Drop the redundant builtin TimeoutError from the retry predicate (or replace with anthropic.APITimeoutError for clarity).

### L19. Embedding cache key uses non-deterministic, collision-prone hash() -> wrong Q&A retrieval + permanently cold cache
- **File:** `backend/app/services/embedding_service.py:78` · **Category:** data-integrity · **Finder:** be-services · **Verifier confidence:** high
- **Impact:** create_embedding caches under cache_key = f"embedding_local:{hash(text)}". Python's built-in hash() for str is salted per-process via PYTHONHASHSEED (confirmed: sys.flags.hash_randomization == 1, PYTHONHASHSEED unset in this env). Two distinct consequences: (1) The same question text produces a DIFFERENT key after every process/worker restart, so the embedding cache is effectively never reused across restarts or across multiple uvicorn workers -- the 24h TTL is dead weight and every query re-embeds. (2) hash() is a 64-bit truncating hash; two different texts that collide return the FIRST text's cached embedding for the SECOND text. Because this embedding is then fed straight into pinecone_service.query() for the Q&A retrieval (query.py:161-173), a collision returns clauses for the wrong question -> the user gets a confident, cited answer about the wrong clause (silent wrong output). Even without a raw collision, the per-worker salt means worker A's cached embedding for text T is invisible/garbage to worker B because the key differs; but if a key from one PYTHONHASHSEED happens to numerically equal a key produced under another seed for different text, a cross-worker mismatch serves a wrong vector.
- **Evidence:** cache_key = f"embedding_local:{hash(text)}"
cached = await self.cache.get(cache_key)
if cached:
    return cached   # may be the embedding of a DIFFERENT text on hash collision / cross-process
- **Fix:** Use a stable content hash: cache_key = f"embedding_local:{hashlib.sha256(text.encode('utf-8')).hexdigest()}". This is deterministic across processes/restarts and collision-resistant. (query.py already uses hashlib.sha256 for its own cache key at line 146 -- mirror that.)

### L20. PDF validation rejects valid uppercase extensions and PDFs whose %PDF- header is not at byte 0
- **File:** `backend/app/api/v1/upload.py:72-82` · **Category:** logic · **Finder:** be-upload-pipeline · **Verifier confidence:** high
- **Impact:** validate_file uses file.filename.endswith('.pdf') (case-sensitive) so a legitimately-named file 'Contract.PDF' / '.Pdf' is rejected with a 400 even though it is a valid PDF. Separately, content.startswith(b'%PDF-') requires the signature at the very first byte. The PDF spec only requires the %PDF- header to appear within the first 1024 bytes; many real-world PDFs (and files saved with a UTF-8 BOM or leading whitespace) place bytes before the header. Such valid PDFs are rejected as 'not a valid PDF (missing PDF header)'. Both are false-negative validation failures that block legitimate uploads.
- **Evidence:** if not file.filename.endswith(".pdf"):  # case-sensitive, rejects .PDF
    raise HTTPException(400, ...)
if not content.startswith(b"%PDF-"):  # header must be at byte 0; spec allows within first 1024 bytes
    raise HTTPException(400, ...)
- **Fix:** Lower-case the extension check: `file.filename.lower().endswith('.pdf')`. For the magic-bytes check, search the first ~1024 bytes: `if b'%PDF-' not in content[:1024]:` (or use content.lstrip()[:5]).

### L21. file.filename can be None on multipart upload → AttributeError 500 instead of 400
- **File:** `backend/app/api/v1/upload.py:72` · **Category:** crash · **Finder:** be-upload-pipeline · **Verifier confidence:** high
- **Impact:** UploadFile.filename is Optional[str] and is None when a multipart part is sent without a filename (a trivially craftable request, e.g. curl -F 'file=@-;type=application/pdf' with no filename, or a malformed client). validate_file immediately calls file.filename.endswith('.pdf') with no None guard, raising AttributeError: 'NoneType' object has no attribute 'endswith'. This is an unhandled exception in the request path before the try/except (the call at line 366 is outside the try block that starts at 376), so it escapes to a generic 500 Internal Server Error instead of a clean 400 validation message. A bad-but-expected client input produces a server error.
- **Evidence:** def validate_file(file: UploadFile, content: bytes) -> float:
    if not file.filename.endswith(".pdf"):  # file.filename may be None -> AttributeError
- **Fix:** Guard for missing filename: `if not file.filename or not file.filename.lower().endswith('.pdf'): raise HTTPException(400, 'Only PDF files are supported.')`. Also consider moving validate_file inside the outer try so unexpected errors are normalized.

### L22. Temp directory leaked when os.remove fails (rmdir skipped) and on event-loop file-handle edge
- **File:** `backend/app/api/v1/upload.py:460-466` · **Category:** resource-leak · **Finder:** be-upload-pipeline · **Verifier confidence:** high
- **Impact:** The finally block runs `if temp_path.exists(): os.remove(temp_path)` then `if Path(temp_dir).exists(): os.rmdir(temp_dir)`. If os.remove raises (e.g. permission error, or a transient handle on some platforms), the exception propagates out of finally and os.rmdir is never reached, leaking both the file and the mkdtemp() directory. Over many failed uploads these temp dirs accumulate under the system temp location. Because mkdtemp creates a unique dir per upload, leaked dirs are never reused or cleaned. An exception in finally also masks the original exception being propagated.
- **Evidence:** finally:
    if temp_path.exists():
        os.remove(temp_path)        # if this raises, rmdir below never runs
    if Path(temp_dir).exists():
        os.rmdir(temp_dir)
- **Fix:** Use shutil.rmtree(temp_dir, ignore_errors=True) in the finally block (removes file + dir atomically and never raises), or wrap each removal in its own try/except so cleanup always completes.

### L23. Background-task exceptions before the try/handler (or process restart) leave docs stuck with no failure status
- **File:** `backend/app/api/v1/upload.py:172-174, 410-417` · **Category:** error-handling · **Finder:** be-upload-pipeline · **Verifier confidence:** high
- **Impact:** run_anomaly_detection_background is scheduled via FastAPI BackgroundTasks, which runs after the 201 response is returned, so any failure inside it can never be surfaced to the uploading client. Two concrete gaps: (1) The await asyncio.sleep(1) and db = SessionLocal() at lines 172-174 execute BEFORE the try block (line 176). If SessionLocal() raises (pool exhausted under the new Supabase pooler / connection limit), the exception propagates uncaught, the status-update code in the except/finally never runs, and the document remains 'analyzing_anomalies' forever — frontend polls indefinitely. (2) If the worker process is restarted/redeployed between returning the response and the task finishing (common on PaaS), the in-memory BackgroundTask is lost with the document stuck at 'analyzing_anomalies'; there is no reconciliation/sweeper to mark orphaned 'analyzing_anomalies' docs as failed. In both cases the only observable symptom is an eternally-spinning UI.
- **Evidence:** await asyncio.sleep(1)
db = SessionLocal()   # <-- outside the try; if this raises, no status update ever happens

try:
    logger.info(...)
    ... detection ...
except Exception:
    ... set anomaly_detection_failed ...
finally:
    db.close()
- **Fix:** Move SessionLocal() creation inside the try (or wrap the whole body) so any failure flips status to a failed state. Add a startup/cron sweep that marks documents stuck in 'analyzing_anomalies'/'embedding_completed' past a timeout as failed so the UI stops polling. Consider a durable job queue instead of in-process BackgroundTasks for crash resilience.

### L24. macro-F1 computed as harmonic mean of macro-P/macro-R, not mean of per-class F1
- **File:** `backend/evals/metrics/severity.py:136-138` · **Category:** logic · **Finder:** evals · **Verifier confidence:** high
- **Impact:** macro_f1 is computed as `_safe_div(2*macro_p*macro_r, macro_p+macro_r)` (F1 of the averaged precision/recall). The standard macro-F1 is the unweighted mean of the per-class F1 scores. These differ whenever per-class precision/recall are unbalanced across classes, so the reported `macro.f1` can be materially higher or lower than the conventional macro-F1 a reader expects from a 'macro F1' label. This silently misstates a headline-adjacent metric used in baseline_runner/runner reports.
- **Evidence:** macro_p = sum(out_per[s]["precision"] for s in SEVERITIES) / len(SEVERITIES)
macro_r = sum(out_per[s]["recall"] for s in SEVERITIES) / len(SEVERITIES)
macro_f1 = _safe_div(2 * macro_p * macro_r, macro_p + macro_r)  # F1-of-means, not mean-of-F1
- **Fix:** Compute macro_f1 = sum(out_per[s]['f1'] for s in SEVERITIES)/len(SEVERITIES). If the F1-of-means quantity is intentionally wanted, rename it (e.g. 'f1_of_macro_pr') to avoid implying standard macro-F1.

### L25. Null prevalence from backend renders as misleading "0.0% / Rare / red" in AnomalyCard
- **File:** `frontend/src/components/anomaly/AnomalyCard.tsx:19-34, 163` · **Category:** contract-mismatch · **Finder:** fe-anomaly-analysis · **Verifier confidence:** high
- **Impact:** The frontend Anomaly type declares prevalence: number (non-optional, types/index.ts:82) but the backend schema and DB column are nullable: AnomalyBase.prevalence is Optional[float]=None (backend/app/schemas/anomaly.py:164), the DB column is nullable=True (models/anomaly.py:27), and the list serializer returns the raw value `"prevalence": anomaly.prevalence` (api/v1/anomalies.py:54), which serializes to JSON null. When prevalence is null: every comparison `anomaly.prevalence < 0.3` evaluates true (null coerces to 0), so the card always labels the clause "Rare" with red styling, and formatPercentage(null) => `(null*100).toFixed(1)` => "0.0%". The Prevalence row is rendered unconditionally, so a clause with unknown prevalence is shown as "0.0% — Rare" in alarming red, which is incorrect/misleading rather than informative.
- **Evidence:** AnomalyCard.tsx:20 `anomaly.prevalence < 0.3 ? 'Rare' : ...`; :163 `{formatPercentage(anomaly.prevalence)}`. formatters.ts:8-9 `return \`${(value * 100).toFixed(1)}%\``. Backend: schemas/anomaly.py:164 `prevalence: Optional[float] = Field(None, ...)`; api/v1/anomalies.py:54 `"prevalence": anomaly.prevalence`.
- **Fix:** Make prevalence optional in the TS type and guard the UI: only render the Prevalence section when `anomaly.prevalence != null`, or coerce/branch so a null prevalence shows '—' / 'Unknown' instead of '0.0% Rare'. Also harden formatPercentage against null/undefined (return '—' when value == null).

### L26. Wrong-severity feedback: suggested_severity field is silently dropped by backend (data fidelity)
- **File:** `frontend/src/components/anomaly/FeedbackButtons.tsx:104-107` · **Category:** contract-mismatch · **Finder:** fe-anomaly-analysis · **Verifier confidence:** high
- **Impact:** FeedbackButtons sends a top-level `suggested_severity` field in the feedback payload (and the TS FeedbackPayload includes it, types/index.ts:209), but the backend FeedbackRequest schema (schemas/anomaly.py:353-371) only defines user_action, feedback_text, confidence_at_detection and has no model_config — so Pydantic v2's default `extra='ignore'` silently drops suggested_severity. The structured signal is therefore never persisted via that field. It is only partially recoverable because the component also embeds `[suggested_severity=...]` into feedback_text. Net effect: the FeedbackEvent.suggested_severity DB column (models/feedback_event.py:40) is never populated through this path, so any analytics keying off that column will be empty. Not a crash (extra='ignore', not 'forbid'), but the dedicated field is dead.
- **Evidence:** FeedbackButtons.tsx:104-107 `submit('dismiss', { feedback_text: composedText, suggested_severity: suggestedSeverity });`. Backend FeedbackRequest has only user_action/feedback_text/confidence_at_detection and no `extra` config (schemas/anomaly.py:356-371). feedback_event.py:40 `suggested_severity = Column(String(20), nullable=True)` exists but is never set from this endpoint.
- **Fix:** Either add `suggested_severity: Optional[str]` to FeedbackRequest and persist it to FeedbackEvent.suggested_severity in the endpoint, or drop the field from the frontend payload entirely and rely solely on the feedback_text encoding so the contract is honest.

### L27. AuthContext.login does two awaited calls with no rollback; if getCurrentUser fails after token is stored, app is left token-authed but user=null
- **File:** `frontend/src/contexts/AuthContext.tsx:53-58` · **Category:** error-handling · **Finder:** fe-api-state · **Verifier confidence:** high
- **Impact:** `login()` awaits `api.login(data)` (which stores the access_token in localStorage at api.ts:183) and then awaits `api.getCurrentUser()`. If `getCurrentUser` throws (network blip, 500 on /auth/me, or transient pooler error), the error propagates to LoginForm's catch and shows a toast, but the token remains in localStorage and `setUser` is never called. State is now inconsistent: `isAuthenticated` (derived from `!!user`) is false so ProtectedRoute redirects to /login, yet `api.getToken()` returns a valid token. On next mount AuthContext.checkAuth will recover, but within the same session the user is stuck: re-submitting login may hit the 20/hour rate limit, and `isAuthenticated` never reflects the stored token. There is no try/catch to clear the token on the second-step failure.
- **Evidence:** `const login = async (data) => { await api.login(data); const currentUser = await api.getCurrentUser(); setUser(currentUser); }` — no catch; api.login already did `this.setToken(response.data.access_token)` (api.ts:183).
- **Fix:** Wrap the getCurrentUser step so a failure clears the token: `try { await api.login(data); const u = await api.getCurrentUser(); setUser(u); } catch (e) { api.clearToken(); setUser(null); throw e; }`.

### L28. useFeedback invalidates a non-existent query key `anomaly-report`; the report cache is never refreshed after feedback
- **File:** `frontend/src/hooks/useFeedback.ts:86-87` · **Category:** logic · **Finder:** fe-api-state · **Verifier confidence:** high
- **Impact:** On feedback success the hook invalidates `['anomalies']` and `['anomaly-report']`. The actual report query key (useAnomalyReport.ts:6) is `['anomalyReport', documentId]` (camelCase, no hyphen). `['anomaly-report']` matches nothing, so the report query is never invalidated. Any report-derived UI (e.g. AnalysisResults consuming `report.competitive_benchmark` in DocumentPage) will keep showing stale data after a feedback action that should affect it. The `['anomalies']` invalidation does work (prefix match), but it triggers a network refetch of anomalies on every feedback submit even though the submitted/feedback state is driven purely by localStorage, not server data — a wasted refetch that can briefly flip cards back to the unsubmitted state if the refetch lands before the localStorage write is read.
- **Evidence:** useFeedback.ts: `queryClient.invalidateQueries({ queryKey: ['anomalies'] }); queryClient.invalidateQueries({ queryKey: ['anomaly-report'] });` vs useAnomalyReport.ts:6 `queryKey: ['anomalyReport', documentId]`.
- **Fix:** Use the correct key `['anomalyReport']` if a report refresh is actually intended; otherwise drop both invalidations since submitted-state is localStorage-driven, not query-driven. Remove the `['anomalies']` invalidation to avoid the wasted/possibly-flickering refetch.

### L29. getApiBaseUrl produces a double slash / wrong scheme for trailing-slash or proxied env URLs
- **File:** `frontend/src/services/api.ts:25-37` · **Category:** logic · **Finder:** fe-api-state · **Verifier confidence:** high
- **Impact:** `getApiBaseUrl` unconditionally appends `/api/v1` to `VITE_API_URL` and, in PROD, does `url.replace('http://', 'https://')`. Two latent defects: (1) if `VITE_API_URL` is set with a trailing slash (a very common deploy mistake, e.g. `https://api.example.com/`), the result is `https://api.example.com//api/v1` — many gateways 404 on the doubled slash. (2) `String.replace('http://','https://')` replaces the FIRST occurrence anywhere, so a value like `http://localhost/proxy?u=http://x` is mangled; and an `https://` URL is left alone (fine) but a bare `localhost:8000` without scheme silently becomes `localhost:8000/api/v1` (no scheme → axios treats it as relative). Current committed .env files avoid these, but the function offers no normalization, so any operator-set URL with a trailing slash breaks all API calls.
- **Evidence:** `return url + '/api/v1';` (no trim of trailing '/'); `return url.replace('http://', 'https://') + '/api/v1';` (first-occurrence replace, no anchoring).
- **Fix:** Normalize: `const base = url.replace(/\/+$/, ''); const https = import.meta.env.PROD ? base.replace(/^http:\/\//, 'https://') : base; return https + '/api/v1';` and validate a scheme is present.

### L30. No 401-driven logout when a token expires mid-session on a TanStack query; user sees stale data + error toasts instead of redirect
- **File:** `frontend/src/services/api.ts:93-97` · **Category:** logic · **Finder:** fe-api-state · **Verifier confidence:** high
- **Impact:** The 401 branch clears the token and dispatches `auth:logout`, which AuthContext handles by clearing user + queryClient. This works for mutations and the auth flow. However, App.tsx configures queries with `retry: 1`, and on a 401 the interceptor will run TWICE (initial + retry) firing two `auth:logout` events and two toasts before the redirect settles; more importantly, since `refetchOnWindowFocus:false` and `staleTime:5min`, a token that expires while the user idles on /dashboard won't trigger any request to surface the 401 until an action occurs, at which point the redirect is correct but the dashboard may have already rendered stale cached data for a now-unauthenticated user. Minor UX/security smell rather than a hard failure.
- **Evidence:** api.ts:93-97 dispatches `auth:logout` inside the interceptor; App.tsx:11 `retry: 1` means the 401 request is retried, re-entering this branch and re-dispatching. No 401-specific `retry: false` guard.
- **Fix:** Set `retry` to a function that returns false for 401/403 in the QueryClient defaults, and/or guard the dispatch so it fires once. Consider clearing the query cache immediately on 401.

### L31. Upload success toast claims analysis is complete while it is still running in the background
- **File:** `frontend/src/hooks/useDocuments.ts:40, 58` · **Category:** logic · **Finder:** fe-auth-doc-pages · **Verifier confidence:** high
- **Impact:** useUploadDocument/useUploadText fire toast.success('Document uploaded and analyzed successfully!') / 'Text uploaded and analyzed successfully!' in onSuccess. But the upload endpoint returns processing_status='analyzing_anomalies' (backend/app/api/v1/upload.py:428) and runs detection in a BackgroundTask afterwards. The toast asserts analysis is finished when it has not even started, contradicting the in-app 'Analyzing in progress...' banner the user simultaneously sees on the document page. Misleading for a product whose core value is the analysis result.
- **Evidence:** useDocuments.ts:40  toast.success('Document uploaded and analyzed successfully!');
upload.py:421-428  return DocumentResponse(... processing_status="analyzing_anomalies", ...)  // analysis runs in background_tasks after response
- **Fix:** Reword to reflect reality, e.g. 'Document uploaded — analysis in progress' so it matches the polling/processing UI.

### L32. Long-running detect_anomalies holds the request DB session/pooler connection for minutes (pool exhaustion)
- **File:** `backend/app/api/v1/anomalies.py:287-350 (and 799)` · **Category:** resource-leak · **Finder:** x-async · **Verifier confidence:** high
- **Impact:** reanalyze_document and the reanalysis branch of get_anomaly_report (line 799) run detect_anomalies — multiple Claude calls plus self-consistency voting, up to 180s+ per batch — while the request's db session (from Depends(get_db)) stays checked out from the engine pool the whole time. The pool is small (pool_size=5, max_overflow=10 = 15 connections) against the Supabase IPv4 pooler. A handful of concurrent reanalyses (limited only by 5/hour/IP, trivially exceeded across IPs) keep up to 15 pooler connections idle-but-checked-out for minutes, blocking all other DB-touching requests until QueuePool timeout, which surfaces as 500s app-wide.
- **Evidence:** db: Session = Depends(get_db),   # session bound to whole request
...
detection_result = await detector.detect_anomalies(...)  # minutes of LLM work, db held idle
...
db.commit()
- **Fix:** Don't hold the ORM session across the LLM phase: read the clauses, close/return the session, run detection, then open a fresh short-lived session to persist results (mirroring the upload background task pattern). Or move reanalysis to a background task.

### L33. Documents stuck in 'analyzing_anomalies' forever when the background task dies or the doc lookup returns None
- **File:** `backend/app/api/v1/upload.py:283-317` · **Category:** data-integrity · **Finder:** x-async · **Verifier confidence:** high
- **Impact:** The post-upload detection runs as a FastAPI BackgroundTask (in-process, same event loop, no persistence). Two stuck-state paths: (1) If the process is restarted/killed during the ~3-min detection (common on serverless/PaaS deploys), the task is lost and the document remains processing_status='analyzing_anomalies' with no recovery mechanism — get_anomaly_report returns HTTP 202 'still in progress' indefinitely. (2) On the success path, after detection the code re-fetches the document (line 283) and only updates status if it still exists; if the row is gone or the lookup returns None it logs and exits the try WITHOUT updating status and WITHOUT raising — the only finally action is db.close(). Combined with the swallow-all detection behavior, a doc can sit in 'analyzing_anomalies' permanently.
- **Evidence:** document = db.query(Document).filter(Document.id == document_id).first()
if document:
    ... document.processing_status = "completed"; db.commit()
else:
    logger.error(...)   # no status change, no raise — doc left 'analyzing_anomalies'
- **Fix:** Add a sweeper/timeout that flips stale 'analyzing_anomalies' rows older than N minutes to a failed/retry state on startup or via a periodic job; or use a durable task queue. Ensure every exit path sets a terminal status.

### L34. validate_file crashes with AttributeError (500) when an upload has no filename
- **File:** `backend/app/api/v1/upload.py:72` · **Category:** crash · **Finder:** x-async · **Verifier confidence:** high
- **Impact:** validate_file does `if not file.filename.endswith(".pdf")`. UploadFile.filename is Optional[str] and can be None when a multipart part omits the filename. file.filename.endswith then raises AttributeError, which is caught by the catch-all except at line 453 and returned as a generic 500 instead of the intended 400 'Only PDF files are supported'. A malformed/abusive multipart request thus produces a 500 and a misleading error.
- **Evidence:** if not file.filename.endswith(".pdf"):   # AttributeError if file.filename is None
    raise HTTPException(status_code=400, detail="Only PDF files are supported...")
- **Fix:** Guard for None first: `if not file.filename or not file.filename.lower().endswith('.pdf'):` and raise the 400.

### L35. Temp directory leaks if temp-file removal fails in upload cleanup
- **File:** `backend/app/api/v1/upload.py:460-466` · **Category:** resource-leak · **Finder:** x-async · **Verifier confidence:** high
- **Impact:** The finally block does os.remove(temp_path) then os.rmdir(temp_dir). If os.remove raises (file still open/locked, or a permissions issue), the exception propagates out of finally and os.rmdir never runs, leaking the temp directory (and its file) created under tempfile.mkdtemp() with no cleanup. Repeated failures accumulate temp dirs and disk usage. Using mkdtemp + rmdir is also brittle: rmdir fails if any extra file landed in the dir.
- **Evidence:** finally:
    if temp_path.exists():
        os.remove(temp_path)        # if this raises, rmdir below never runs
    if Path(temp_dir).exists():
        os.rmdir(temp_dir)
- **Fix:** Use shutil.rmtree(temp_dir, ignore_errors=True) in the finally (removes the dir and any contents and won't raise), or wrap each removal in its own try/except.

### L36. Every AnomalyDetector() in request handlers leaks an unclosed Anthropic AsyncAnthropic (httpx) client
- **File:** `backend/app/core/anomaly_detector.py:63-65` · **Category:** resource-leak · **Finder:** x-async · **Verifier confidence:** high
- **Impact:** AnomalyDetector.__init__ default-constructs ClaudeService() when no claude_service is passed, and ClaudeService.__init__ creates anthropic.AsyncAnthropic(...) which owns an httpx connection pool. The request handlers in anomalies.py construct AnomalyDetector() with NO services on every call: get_performance_metrics (126), get_anomaly_report reanalysis (794), submit_feedback (888). None of them ever call detector.claude.close(). Each request therefore opens a new httpx client/connection pool that is never released. Under sustained traffic this accumulates open file descriptors/sockets (FD exhaustion) even though most of those endpoints currently 500 before using Claude. It also instantiates EmbeddingService()/PineconeService() needlessly.
- **Evidence:** self.embedding = embedding_service or EmbeddingService()
self.claude = claude_service or ClaudeService()   # new AsyncAnthropic httpx client each time
self.pinecone = pinecone_service or PineconeService()
# claude_service.py:40  self.client = anthropic.AsyncAnthropic(api_key=...)
# anomalies.py never calls detector.claude.close()
- **Fix:** Inject the shared app.state.claude/embedding/pinecone into these handlers (as upload.py does) instead of default-constructing, or close the client in a finally. Best: reuse the singletons created at startup.

### L37. Unbounded skip/limit on GET /anomalies/{document_id} allows negative/huge pagination
- **File:** `backend/app/api/v1/anomalies.py:408-409` · **Category:** error-handling · **Finder:** x-security · **Verifier confidence:** high
- **Impact:** Unlike list_documents (which uses Query(ge=0)/Query(ge=1,le=200)), get_anomalies declares skip:int=0 and limit:int=100 with no Query() bounds. A client can pass limit=100000000 to force the DB to materialize/serialize an unbounded result set (memory/CPU DoS on a doc with many anomalies), or negative offsets which SQLAlchemy/Postgres reject at execution time, surfacing as an unhandled 500 rather than a clean 422.
- **Evidence:**     skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
- **Fix:** Mirror list_documents: skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=200).
