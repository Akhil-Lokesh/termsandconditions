# Anomaly Detection System - Deployment Checklist

Complete pre-deployment checklist for the 6-stage anomaly detection pipeline.

## Table of Contents

1. [Pre-Deployment Requirements](#pre-deployment-requirements)
2. [Baseline Corpus Setup](#baseline-corpus-setup)
3. [Calibrator Training](#calibrator-training)
4. [Performance Threshold Configuration](#performance-threshold-configuration)
5. [Monitoring Setup](#monitoring-setup)
6. [Gradual Rollout Plan](#gradual-rollout-plan)
7. [Validation & Testing](#validation--testing)
8. [Go-Live Checklist](#go-live-checklist)

---

## Pre-Deployment Requirements

### Infrastructure

- [ ] **PostgreSQL 15+** deployed and accessible
  - Connection string configured in `.env`
  - Database user with full permissions
  - Minimum specs: 4GB RAM, 50GB storage

- [ ] **Redis 7+** deployed for caching
  - Connection string configured in `.env`
  - Minimum specs: 2GB RAM

- [ ] **Pinecone** vector database configured
  - API key in `.env`
  - Two namespaces created: `baseline`, `user_tcs`
  - Index dimension: 768 (legal-BERT)
  - Metric: cosine similarity

### External Services

- [ ] **OpenAI API** access configured
  - API key in `.env`
  - GPT-4 access enabled
  - Rate limits understood (10K TPM recommended)

- [ ] **Pinecone API** access configured
  - API key and environment in `.env`
  - Index created with correct dimensions
  - Free tier supports up to 100K vectors

### Software Dependencies

- [ ] **Python 3.10+** installed
- [ ] **All pip dependencies** installed:
  ```bash
  pip install -r requirements.txt
  pip install -r requirements-dev.txt  # For testing
  ```

- [ ] **Legal-BERT model** downloaded:
  ```bash
  python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('nlpaueb/legal-bert-base-uncased')"
  ```
  Expected download size: ~420MB

- [ ] **NLTK data** downloaded:
  ```python
  import nltk
  nltk.download('punkt')
  nltk.download('stopwords')
  ```

### Environment Configuration

- [ ] **`.env` file** configured with all required variables:
  ```bash
  # Required
  OPENAI_API_KEY=sk-...
  PINECONE_API_KEY=...
  PINECONE_ENVIRONMENT=us-east-1-aws
  DATABASE_URL=postgresql://...
  REDIS_URL=redis://...
  SECRET_KEY=... # Use: openssl rand -hex 32

  # Anomaly Detection
  ANOMALY_DETECTION_ENABLED=true
  MAX_ALERTS=10
  TARGET_ALERTS=5
  RETRAIN_AFTER_SAMPLES=100
  DISMISSAL_THRESHOLD=0.20
  ```

- [ ] **Configuration file** created: `config/anomaly_detection.yaml`
  - Copy from `config/anomaly_detection.example.yaml`
  - Adjust thresholds for your use case
  - Review all stage settings

### Database Migration

- [ ] **Alembic migrations** run:
  ```bash
  # Check current migration status
  python -m alembic current

  # Run all migrations
  python -m alembic upgrade head

  # Verify tables exist
  python scripts/check_database.py
  ```

- [ ] **Database tables** verified:
  - `users` - User accounts
  - `documents` - Uploaded T&Cs
  - `clauses` - Extracted clauses
  - `anomalies` - Detected anomalies
  - `feedback` - User feedback for active learning

---

## Baseline Corpus Setup

### Collection Requirements

**Minimum**: 100 Terms & Conditions documents

**Diversity Requirements**:
- [ ] **10+ industries** represented:
  - Healthcare (10+ docs)
  - Financial services (10+ docs)
  - Technology/SaaS (15+ docs)
  - Gaming (10+ docs)
  - E-commerce (10+ docs)
  - Social media (10+ docs)
  - Travel/hospitality (5+ docs)
  - Education (5+ docs)
  - Dating/relationships (5+ docs)
  - Entertainment (5+ docs)

- [ ] **5+ service types** represented:
  - Mobile apps (30+ docs)
  - Web services (30+ docs)
  - Subscriptions (20+ docs)
  - Marketplaces (10+ docs)
  - Enterprise software (10+ docs)

- [ ] **Document characteristics**:
  - Recent (within 2 years): 80%+
  - Various lengths (5-50 pages)
  - Major companies represented
  - Multiple jurisdictions (US, EU, etc.)

### Collection Process

1. **Automated Collection**:
   ```bash
   # Use provided collection script
   python scripts/collect_baseline_corpus.py \
       --target-count 100 \
       --industries healthcare,finance,gaming,tech,ecommerce \
       --output data/baseline_corpus/ \
       --validate
   ```

2. **Manual Collection** (if automated fails):
   - [ ] Download PDFs from app stores, company websites
   - [ ] Verify legitimacy (real companies, not fake T&Cs)
   - [ ] Organize by industry: `data/baseline_corpus/{industry}/`

3. **Quality Check**:
   ```bash
   # Validate corpus quality
   python scripts/validate_corpus.py \
       --corpus-dir data/baseline_corpus/ \
       --min-documents 100 \
       --check-diversity \
       --check-quality
   ```

   Should output:
   ```
   ✓ Document count: 102/100
   ✓ Industry diversity: 11/10 industries
   ✓ Service type diversity: 6/5 types
   ✓ Average document length: 23 pages
   ✓ Recent documents: 87% (within 2 years)
   ✓ Extraction quality: 94% (clean text)
   ```

### Indexing to Pinecone

1. **Process and Embed**:
   ```bash
   # Extract clauses and create embeddings
   python scripts/process_baseline_corpus.py \
       --corpus-dir data/baseline_corpus/ \
       --output data/baseline_embeddings/ \
       --batch-size 100
   ```

   Expected output:
   - ~5,000-10,000 clause embeddings
   - Processing time: 30-60 minutes
   - Temporary storage: ~2GB

2. **Upload to Pinecone**:
   ```bash
   # Index baseline corpus to Pinecone
   python scripts/index_baseline.py \
       --embeddings-dir data/baseline_embeddings/ \
       --namespace baseline \
       --batch-size 100 \
       --verify
   ```

   Should output:
   ```
   ✓ Connected to Pinecone
   ✓ Namespace: baseline
   ✓ Uploaded: 8,542 vectors
   ✓ Verification: 100% success rate
   ✓ Query test: Passed
   ```

3. **Verify Index**:
   ```bash
   # Test semantic search
   python scripts/test_pinecone_search.py \
       --namespace baseline \
       --query "sell personal data to third parties" \
       --top-k 5
   ```

### Baseline Update Schedule

- [ ] **Quarterly updates** (every 3 months):
  - Add 25-50 new documents
  - Remove outdated (>2 years old)
  - Re-index updated corpus
  - Validate on test set

- [ ] **Calendar reminders** set:
  - April 1, July 1, October 1, January 1
  - Assign to: Data team

---

## Calibrator Training

### Initial Training Requirements

**Minimum**: 500 labeled feedback samples

**Composition**:
- 200+ high confidence samples (0.8-1.0 predicted)
- 200+ medium confidence samples (0.5-0.8 predicted)
- 100+ low confidence samples (0.0-0.5 predicted)

### Cold Start (0-100 samples)

**Option 1: Expert Labeling**

- [ ] Assemble expert review team (2-3 legal/privacy professionals)
- [ ] Run detection on 20 sample documents
- [ ] Experts label each detection:
  - `correct` - Genuinely problematic clause
  - `incorrect` - False positive
  - `uncertain` - Unclear, needs more context

  ```bash
  # Generate labeling interface
  python scripts/generate_labeling_ui.py \
      --documents data/sample_documents/ \
      --output labeling/cold_start/
  ```

- [ ] Export labels:
  ```bash
  python scripts/export_labels.py \
      --labeling-dir labeling/cold_start/ \
      --output data/training/cold_start_labels.json
  ```

**Option 2: Synthetic Labels**

- [ ] Use confidence heuristics:
  - Pattern matches from high-quality patterns → `correct`
  - Low semantic similarity (< 0.3) → `correct`
  - High statistical Z-scores (> 4) → `correct`

  ```bash
  python scripts/generate_synthetic_labels.py \
      --sample-documents data/sample_documents/ \
      --output data/training/synthetic_labels.json \
      --method heuristic
  ```

### Warm Start (100-500 samples)

**Beta User Feedback Collection**:

- [ ] **Recruit beta testers** (10-20 users):
  - Privacy-conscious users
  - Legal professionals
  - Tech-savvy early adopters

- [ ] **Deploy to beta environment**:
  ```bash
  # Deploy with feedback collection enabled
  ENVIRONMENT=beta python scripts/deploy.py \
      --enable-feedback \
      --feedback-incentive enabled
  ```

- [ ] **Feedback collection targets**:
  - Week 1: 50 samples
  - Week 2: 100 samples
  - Week 3: 150 samples
  - Week 4: 200 samples

- [ ] **Monitor feedback quality**:
  ```bash
  # Check feedback statistics
  python scripts/check_feedback_quality.py \
      --min-samples 100 \
      --check-distribution
  ```

### Production Training (500+ samples)

- [ ] **Initial calibrator training**:
  ```bash
  # Train calibrator on collected feedback
  python scripts/train_calibrator.py \
      --feedback-file data/training/all_feedback.json \
      --method isotonic \
      --validate \
      --output models/calibrator_v1.pkl
  ```

  Expected output:
  ```
  ✓ Training samples: 523
  ✓ Validation samples: 131
  ✓ ECE (before): 0.142
  ✓ ECE (after): 0.038  ← Target: < 0.05
  ✓ Brier improvement: 32%
  ✓ Model saved: models/calibrator_v1.pkl
  ```

- [ ] **Validate calibration**:
  ```bash
  # Plot calibration curve
  python scripts/plot_calibration.py \
      --model models/calibrator_v1.pkl \
      --test-data data/training/validation_set.json \
      --output plots/calibration_curve.png
  ```

- [ ] **Deploy calibrator**:
  ```bash
  # Copy to production
  cp models/calibrator_v1.pkl /opt/app/models/calibrator.pkl

  # Restart service
  systemctl restart anomaly-detection-api
  ```

### Retraining Schedule

- [ ] **Automatic retraining** enabled:
  - Triggers after 100 new feedback samples
  - Runs asynchronously
  - Validates before deployment
  - Logs to monitoring system

- [ ] **Manual retraining** process documented:
  ```bash
  # Force retrain (if needed)
  python scripts/retrain_calibrator.py \
      --force \
      --min-samples 100 \
      --validate \
      --auto-deploy
  ```

---

## Performance Threshold Configuration

### Detection Thresholds

- [ ] **Stage 1 thresholds** configured:
  ```yaml
  stage1_detection:
    pattern_confidence_boost: 0.15
    semantic_similarity_threshold: 0.70
    statistical_z_score_threshold: 3.0
  ```

- [ ] **Tested on validation set** (should achieve):
  - Recall: ≥ 95%
  - Precision: ≥ 70%
  - Processing time: < 5s

### Filtering Thresholds

- [ ] **Stage 2 thresholds** configured:
  ```yaml
  stage2_filtering:
    industry_filter_strength: 1.0
    service_type_filter_strength: 1.0
    temporal_penalty: 0.8
  ```

- [ ] **Tested on validation set** (should achieve):
  - FP reduction: ≥ 70%
  - Recall preservation: ≥ 98%

### Clustering Thresholds

- [ ] **Stage 3 thresholds** configured:
  ```yaml
  stage3_clustering:
    similarity_threshold: 0.85
    min_cluster_size: 2
    max_cluster_size: 10
  ```

- [ ] **Tested on validation set** (should achieve):
  - Noise reduction: 50-70%
  - No loss of unique anomalies

### Alert Budget

- [ ] **Stage 6 budget** configured:
  ```yaml
  stage6_ranking:
    max_alerts: 10
    target_alerts: 5
    min_score_threshold: 0.0  # No hard cutoff
  ```

- [ ] **Validated with user research**:
  - Users can process 3-7 alerts comfortably
  - Alert fatigue starts at 12+ alerts
  - Target: 5 alerts per document

### Performance Targets

- [ ] **System-wide targets** set:
  - Total processing time: < 30s (target: 20s)
  - Memory usage: < 1GB per request
  - Concurrent requests: 10+
  - 95th percentile latency: < 45s

---

## Monitoring Setup

### APScheduler Configuration

- [ ] **Daily monitoring** scheduled:
  ```python
  # In anomaly_detection_monitor.py
  scheduler = setup_monitoring_scheduler(db_session_factory)
  scheduler.start()
  ```

  Runs daily at 1 AM UTC:
  - Calculates daily metrics
  - Checks threshold violations
  - Generates alerts
  - Sends reports

- [ ] **Monitoring service** configured:
  ```bash
  # Add to systemd
  sudo cp deployment/anomaly-monitoring.service /etc/systemd/system/
  sudo systemctl enable anomaly-monitoring
  sudo systemctl start anomaly-monitoring
  ```

### Metrics Collection

- [ ] **Performance metrics** endpoint enabled:
  - GET `/api/v1/anomalies/performance`
  - Returns: ECE, dismissal rate, processing time, etc.
  - Authentication: Admin only

- [ ] **Metrics dashboard** configured:
  - Grafana/Datadog/New Relic integration
  - Key charts:
    - Daily anomaly count
    - Dismissal rate trend
    - ECE trend
    - Processing time percentiles
  - Alerts configured for threshold violations

### Alerting

- [ ] **Critical alerts** configured (immediate):
  - ECE > 0.10
  - Dismissal rate > 40%
  - Pipeline failure rate > 5%
  - Processing time > 60s

  Notify via:
  - PagerDuty/Opsgenie
  - Slack #anomaly-alerts
  - Email to on-call engineer

- [ ] **Warning alerts** configured (daily digest):
  - ECE > 0.05
  - Dismissal rate > 25%
  - Processing time > 45s
  - Avg alerts per doc > 10

  Notify via:
  - Email digest (8 AM daily)
  - Slack #anomaly-warnings

### Logging

- [ ] **Structured logging** enabled:
  ```python
  # In anomaly_detector.py
  logger.info(
      "Pipeline complete",
      extra={
          'document_id': document_id,
          'total_anomalies': len(anomalies),
          'processing_time_ms': elapsed_time,
          'stage1_detections': stage1_count,
          'stage6_shown': shown_count
      }
  )
  ```

- [ ] **Log aggregation** configured:
  - CloudWatch/Elasticsearch/Splunk
  - Retention: 30 days
  - Search indexes: document_id, timestamp, error

---

## Gradual Rollout Plan

### Phase 1: Internal Testing (Week 1-2)

**Objective**: Validate pipeline with internal team

- [ ] **Enable for internal users only**:
  ```python
  # In feature flags
  ANOMALY_DETECTION_ENABLED_USERS = [
      'admin@company.com',
      'qa@company.com',
      'engineering@company.com'
  ]
  ```

- [ ] **Test on 20+ sample documents**:
  - Various industries
  - Different document types
  - Known problematic clauses

- [ ] **Collect initial feedback**:
  - False positive rate
  - Missing detections
  - Processing times
  - User experience

- [ ] **Iterate based on feedback**:
  - Adjust thresholds
  - Fix bugs
  - Improve performance

**Success Criteria**:
- ✅ 90%+ of known issues detected
- ✅ < 30% false positive rate
- ✅ < 30s processing time
- ✅ No critical bugs

### Phase 2: Beta Release (Week 3-6)

**Objective**: Validate with 50 beta users

- [ ] **Expand to beta users**:
  ```python
  # Feature flag expansion
  ANOMALY_DETECTION_BETA_ENABLED = True
  BETA_USER_IDS = load_beta_users('config/beta_users.txt')
  ```

- [ ] **Set beta expectations**:
  - Email to beta users explaining feature
  - Feedback form prominently displayed
  - Incentives for detailed feedback (credits, swag)

- [ ] **Monitor beta metrics**:
  - 100+ documents analyzed
  - 200+ feedback submissions
  - Dismissal rate < 25%
  - Helpful rate > 70%

- [ ] **Weekly check-ins**:
  - Review metrics dashboard
  - Respond to user feedback
  - Make incremental improvements

**Success Criteria**:
- ✅ 500+ calibration samples collected
- ✅ ECE < 0.05
- ✅ Dismissal rate < 20%
- ✅ Positive user sentiment (NPS > 50)

### Phase 3: Limited Release (Week 7-10)

**Objective**: Release to 20% of users

- [ ] **Gradual rollout** (increase 5% per week):
  ```python
  # Week 7: 5%
  # Week 8: 10%
  # Week 9: 15%
  # Week 10: 20%

  ANOMALY_DETECTION_ROLLOUT_PERCENTAGE = 20
  ```

- [ ] **Monitor at scale**:
  - 1,000+ documents analyzed
  - 1,000+ feedback submissions
  - System performance stable
  - No increase in support tickets

- [ ] **A/B testing** (optional):
  - Control group: No anomaly detection
  - Treatment group: With anomaly detection
  - Measure: User engagement, retention, satisfaction

**Success Criteria**:
- ✅ System handles 100+ concurrent users
- ✅ Performance metrics stable
- ✅ User metrics positive
- ✅ No critical incidents

### Phase 4: Full Release (Week 11+)

**Objective**: Release to all users

- [ ] **Remove feature flag**:
  ```python
  ANOMALY_DETECTION_ENABLED = True  # For all users
  ```

- [ ] **Announcement**:
  - Blog post
  - Email to all users
  - Social media
  - Documentation updated

- [ ] **Monitor closely** (first week):
  - Daily metric reviews
  - Rapid response to issues
  - User feedback collection

- [ ] **Post-launch review** (after 2 weeks):
  - Overall performance vs. targets
  - User satisfaction survey
  - Lessons learned
  - Future improvement roadmap

**Success Criteria**:
- ✅ All performance targets met
- ✅ No major incidents
- ✅ Positive user reception
- ✅ Clear improvement over baseline

---

## Validation & Testing

### Unit Tests

- [ ] **Run unit test suite** (1,100+ tests):
  ```bash
  # Run all tests
  pytest backend/tests/ -v

  # Check coverage
  pytest backend/tests/ --cov=app.core --cov-report=html
  ```

  Required coverage:
  - Overall: > 85%
  - Core modules: > 90%
  - API endpoints: > 80%

- [ ] **Fix any test failures**:
  - Zero failures allowed
  - Flaky tests must be fixed or removed
  - All deprecation warnings addressed

### Integration Tests

- [ ] **Run integration test suite** (20+ tests):
  ```bash
  pytest backend/tests/test_anomaly_detection_pipeline.py -v -s
  ```

  All tests must pass:
  - ✅ Stage 1 recall >= 95%
  - ✅ Stage 2 FP reduction >= 70%
  - ✅ Stage 3 noise reduction >= 30%
  - ✅ Stage 5 ECE < 0.05
  - ✅ Stage 6 budget enforced
  - ✅ Full pipeline < 30s

- [ ] **Test on real documents**:
  ```bash
  python scripts/test_pipeline_e2e.py \
      --test-dir data/test_documents/ \
      --validate-against data/ground_truth.json
  ```

### Performance Testing

- [ ] **Load testing**:
  ```bash
  # Simulate 50 concurrent users
  locust -f tests/load_test.py \
      --users 50 \
      --spawn-rate 5 \
      --run-time 10m
  ```

  Targets:
  - 95th percentile latency < 45s
  - Error rate < 1%
  - Throughput > 10 req/min

- [ ] **Stress testing**:
  ```bash
  # Test failure modes
  locust -f tests/stress_test.py \
      --users 100 \
      --spawn-rate 10 \
      --run-time 5m
  ```

  Verify:
  - Graceful degradation
  - No memory leaks
  - Proper error handling

### Security Testing

- [ ] **API security audit**:
  - Authentication required for all endpoints
  - Rate limiting configured (100 req/hour per user)
  - Input validation for all parameters
  - SQL injection protection (parameterized queries)

- [ ] **Data privacy compliance**:
  - User data encrypted at rest
  - Feedback data anonymized
  - GDPR compliance (data deletion)
  - Privacy policy updated

---

## Go-Live Checklist

### Pre-Launch (T-1 week)

- [ ] **All deployment requirements met** (see above)
- [ ] **Baseline corpus indexed** (100+ T&Cs)
- [ ] **Calibrator trained** (500+ samples, ECE < 0.05)
- [ ] **All tests passing** (unit, integration, performance)
- [ ] **Monitoring configured** (metrics, alerts, logging)
- [ ] **Documentation complete** (API docs, user guide, troubleshooting)

### Launch Day (T-0)

- [ ] **Final deployment**:
  ```bash
  # Pull latest code
  git pull origin main

  # Run migrations
  python -m alembic upgrade head

  # Deploy to production
  python scripts/deploy.py --environment production

  # Restart services
  systemctl restart anomaly-detection-api
  systemctl restart anomaly-monitoring
  ```

- [ ] **Smoke tests**:
  ```bash
  # Test critical paths
  python scripts/smoke_test.py --environment production
  ```

  Verify:
  - ✅ API responding
  - ✅ Detection working
  - ✅ Feedback collection working
  - ✅ Monitoring active

- [ ] **Enable for all users**:
  ```python
  # Remove feature flag
  ANOMALY_DETECTION_ENABLED = True
  ```

- [ ] **Announcement**:
  - Send email to all users
  - Post on social media
  - Update help center

### Post-Launch (T+1 week)

- [ ] **Daily metric reviews**:
  - Check dashboard daily
  - Respond to alerts
  - Monitor user feedback

- [ ] **User feedback collection**:
  - Survey 100+ users
  - NPS score
  - Feature requests

- [ ] **Post-mortem** (if issues):
  - Document what went wrong
  - Root cause analysis
  - Action items for prevention

### Ongoing

- [ ] **Weekly performance reviews**:
  - Review weekly metrics
  - Identify trends
  - Plan improvements

- [ ] **Monthly calibrator updates**:
  - Review feedback quality
  - Retrain if needed
  - Validate calibration

- [ ] **Quarterly baseline updates**:
  - Add new T&Cs to corpus
  - Remove outdated documents
  - Re-index Pinecone

---

## Sign-Off

### Pre-Deployment Approval

- [ ] **Engineering Lead**: ______________________  Date: ___________
  - All technical requirements met
  - Tests passing
  - Code reviewed

- [ ] **QA Lead**: ______________________  Date: ___________
  - Test plan executed
  - All tests passing
  - Performance validated

- [ ] **Data Team Lead**: ______________________  Date: ___________
  - Baseline corpus ready
  - Calibrator trained
  - Monitoring configured

- [ ] **Product Manager**: ______________________  Date: ___________
  - User experience validated
  - Documentation complete
  - Rollout plan approved

### Go-Live Approval

- [ ] **CTO/VP Engineering**: ______________________  Date: ___________
  - Final approval for production deployment
  - Risk assessment reviewed
  - Rollback plan in place

---

## Rollback Plan

### Trigger Conditions

Rollback if any of:
- Critical bugs affecting > 10% of users
- Dismissal rate > 50%
- Pipeline failure rate > 20%
- Processing time consistently > 60s
- Security vulnerability discovered

### Rollback Procedure

1. **Disable feature immediately**:
   ```python
   # Emergency kill switch
   ANOMALY_DETECTION_ENABLED = False
   ```

2. **Revert to previous version**:
   ```bash
   # Rollback deployment
   git checkout <previous_tag>
   python scripts/deploy.py --environment production
   systemctl restart anomaly-detection-api
   ```

3. **Notify stakeholders**:
   - Engineering team
   - Product team
   - User-facing teams (support, success)

4. **Investigate and fix**:
   - Root cause analysis
   - Fix implementation
   - Re-test thoroughly

5. **Re-deploy when ready**:
   - Follow deployment checklist again
   - More conservative rollout

---

**Last Updated**: 2025-01-12
**Version**: 1.0.0
**Owner**: Engineering Team
