#!/usr/bin/env python3
"""
Anomaly Detection System - Deployment Script

Automates deployment of the 6-stage anomaly detection pipeline with:
- Dependency verification
- Database migration
- Pinecone index validation
- Baseline corpus loading
- Calibrator training
- Smoke testing
- API endpoint verification
- Deployment report generation

Usage:
    python scripts/deploy_anomaly_detection.py
    python scripts/deploy_anomaly_detection.py --skip-baseline
    python scripts/deploy_anomaly_detection.py --test-only

Author: AI Engineering Team
Version: 1.0.0
"""

import sys
import os
import argparse
import subprocess
import importlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('deployment.log')
    ]
)
logger = logging.getLogger(__name__)


class DeploymentError(Exception):
    """Custom exception for deployment failures."""
    pass


class AnomalyDetectionDeployer:
    """
    Automated deployment system for anomaly detection pipeline.

    Handles all deployment steps with comprehensive error checking,
    rollback instructions, and detailed reporting.
    """

    def __init__(self, args: argparse.Namespace):
        """
        Initialize deployer with command-line arguments.

        Args:
            args: Parsed command-line arguments
        """
        self.args = args
        self.deployment_start = datetime.utcnow()
        self.deployment_log = []
        self.errors = []
        self.warnings = []

        # Deployment status
        self.status = {
            'dependencies': 'pending',
            'migrations': 'pending',
            'pinecone': 'pending',
            'baseline_corpus': 'pending' if not args.skip_baseline else 'skipped',
            'calibrator': 'pending' if not args.skip_calibrator else 'skipped',
            'smoke_tests': 'pending',
            'api_verification': 'pending'
        }

    def log_step(self, step: str, status: str, message: str = ""):
        """Log deployment step."""
        timestamp = datetime.utcnow().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'step': step,
            'status': status,
            'message': message
        }
        self.deployment_log.append(log_entry)

        if status == 'success':
            logger.info(f"✓ {step}: {message}")
        elif status == 'warning':
            logger.warning(f"⚠ {step}: {message}")
            self.warnings.append(log_entry)
        elif status == 'error':
            logger.error(f"✗ {step}: {message}")
            self.errors.append(log_entry)
        else:
            logger.info(f"• {step}: {message}")

    def check_dependencies(self) -> bool:
        """
        Check that all required dependencies are installed.

        Returns:
            True if all dependencies are installed, False otherwise
        """
        self.log_step('Dependencies', 'info', 'Checking required packages...')

        required_packages = [
            ('sentence_transformers', 'sentence-transformers'),
            ('sklearn', 'scikit-learn'),
            ('numpy', 'numpy'),
            ('pinecone', 'pinecone-client'),
            ('sqlalchemy', 'sqlalchemy'),
            ('alembic', 'alembic'),
            ('fastapi', 'fastapi'),
            ('redis', 'redis'),
        ]

        missing_packages = []

        for module_name, package_name in required_packages:
            try:
                importlib.import_module(module_name)
                self.log_step('Dependencies', 'success', f'{package_name} installed')
            except ImportError:
                missing_packages.append(package_name)
                self.log_step('Dependencies', 'error', f'{package_name} NOT installed')

        if missing_packages:
            self.status['dependencies'] = 'failed'
            error_msg = (
                f"Missing required packages: {', '.join(missing_packages)}\n"
                f"Install with: pip install {' '.join(missing_packages)}"
            )
            self.log_step('Dependencies', 'error', error_msg)
            return False

        self.status['dependencies'] = 'success'
        self.log_step('Dependencies', 'success', 'All required packages installed')
        return True

    def run_migrations(self) -> bool:
        """
        Run Alembic database migrations.

        Returns:
            True if migrations successful, False otherwise
        """
        if self.args.test_only:
            self.log_step('Migrations', 'info', 'Skipped (test-only mode)')
            self.status['migrations'] = 'skipped'
            return True

        self.log_step('Migrations', 'info', 'Running database migrations...')

        try:
            # Check current migration
            result = subprocess.run(
                ['python', '-m', 'alembic', 'current'],
                capture_output=True,
                text=True,
                cwd='backend'
            )

            self.log_step('Migrations', 'info', f'Current: {result.stdout.strip()}')

            # Run migrations
            result = subprocess.run(
                ['python', '-m', 'alembic', 'upgrade', 'head'],
                capture_output=True,
                text=True,
                cwd='backend'
            )

            if result.returncode != 0:
                self.status['migrations'] = 'failed'
                self.log_step('Migrations', 'error', f'Migration failed: {result.stderr}')
                return False

            self.status['migrations'] = 'success'
            self.log_step('Migrations', 'success', 'Database migrations completed')
            return True

        except Exception as e:
            self.status['migrations'] = 'failed'
            self.log_step('Migrations', 'error', f'Exception: {str(e)}')
            return False

    def verify_pinecone_indexes(self) -> bool:
        """
        Verify Pinecone indexes exist and are accessible.

        Returns:
            True if indexes valid, False otherwise
        """
        self.log_step('Pinecone', 'info', 'Verifying Pinecone indexes...')

        try:
            import pinecone
            from app.core.config import settings

            # Initialize Pinecone
            pinecone.init(
                api_key=settings.PINECONE_API_KEY,
                environment=settings.PINECONE_ENVIRONMENT
            )

            # Check if index exists
            index_name = settings.PINECONE_INDEX_NAME

            if index_name not in pinecone.list_indexes():
                self.status['pinecone'] = 'failed'
                self.log_step('Pinecone', 'error', f'Index "{index_name}" not found')
                return False

            # Connect to index
            index = pinecone.Index(index_name)

            # Check namespaces
            stats = index.describe_index_stats()
            namespaces = stats.get('namespaces', {})

            required_namespaces = ['baseline', 'user_tcs']
            missing_namespaces = [ns for ns in required_namespaces if ns not in namespaces]

            if missing_namespaces:
                self.log_step(
                    'Pinecone',
                    'warning',
                    f'Missing namespaces: {", ".join(missing_namespaces)}'
                )

            # Log statistics
            for ns, ns_stats in namespaces.items():
                vector_count = ns_stats.get('vector_count', 0)
                self.log_step('Pinecone', 'info', f'{ns}: {vector_count:,} vectors')

            self.status['pinecone'] = 'success'
            self.log_step('Pinecone', 'success', 'Pinecone indexes verified')
            return True

        except Exception as e:
            self.status['pinecone'] = 'failed'
            self.log_step('Pinecone', 'error', f'Exception: {str(e)}')
            return False

    def validate_baseline_corpus(self) -> bool:
        """
        Validate baseline corpus is loaded and ready.

        Returns:
            True if baseline corpus valid, False otherwise
        """
        if self.args.skip_baseline:
            self.log_step('Baseline Corpus', 'info', 'Skipped (--skip-baseline)')
            return True

        self.log_step('Baseline Corpus', 'info', 'Validating baseline corpus...')

        try:
            import pinecone
            from app.core.config import settings

            # Connect to Pinecone
            pinecone.init(
                api_key=settings.PINECONE_API_KEY,
                environment=settings.PINECONE_ENVIRONMENT
            )
            index = pinecone.Index(settings.PINECONE_INDEX_NAME)

            # Get baseline stats
            stats = index.describe_index_stats()
            baseline_stats = stats.get('namespaces', {}).get('baseline', {})
            vector_count = baseline_stats.get('vector_count', 0)

            # Minimum requirement: 100 documents * ~50 clauses avg = 5,000 vectors
            min_vectors = 5000

            if vector_count < min_vectors:
                self.status['baseline_corpus'] = 'failed'
                self.log_step(
                    'Baseline Corpus',
                    'error',
                    f'Insufficient baseline vectors: {vector_count:,} (minimum: {min_vectors:,})'
                )
                return False

            self.log_step(
                'Baseline Corpus',
                'success',
                f'Baseline corpus validated: {vector_count:,} vectors'
            )

            # Try a sample query
            try:
                sample_query = [0.1] * 768  # Dummy embedding
                results = index.query(
                    vector=sample_query,
                    namespace='baseline',
                    top_k=1,
                    include_metadata=True
                )

                if results and results['matches']:
                    self.log_step('Baseline Corpus', 'success', 'Sample query successful')
                else:
                    self.log_step('Baseline Corpus', 'warning', 'Sample query returned no results')

            except Exception as e:
                self.log_step('Baseline Corpus', 'warning', f'Sample query failed: {str(e)}')

            self.status['baseline_corpus'] = 'success'
            return True

        except Exception as e:
            self.status['baseline_corpus'] = 'failed'
            self.log_step('Baseline Corpus', 'error', f'Exception: {str(e)}')
            return False

    def train_calibrator(self) -> bool:
        """
        Train confidence calibrator on historical feedback data.

        Returns:
            True if training successful, False otherwise
        """
        if self.args.skip_calibrator:
            self.log_step('Calibrator Training', 'info', 'Skipped (--skip-calibrator)')
            return True

        self.log_step('Calibrator Training', 'info', 'Training confidence calibrator...')

        try:
            # Check if we have enough feedback data
            # In production, this would query the database
            # For now, we'll check if a training file exists

            training_data_path = Path('data/training/feedback_data.json')

            if not training_data_path.exists():
                self.log_step(
                    'Calibrator Training',
                    'warning',
                    'No training data found. Calibrator will use defaults.'
                )
                self.status['calibrator'] = 'warning'
                return True

            # Load training data
            with open(training_data_path) as f:
                training_data = json.load(f)

            sample_count = len(training_data)

            if sample_count < 50:
                self.log_step(
                    'Calibrator Training',
                    'warning',
                    f'Insufficient training samples: {sample_count} (minimum: 50)'
                )
                self.status['calibrator'] = 'warning'
                return True

            self.log_step(
                'Calibrator Training',
                'info',
                f'Found {sample_count} training samples'
            )

            # Train calibrator
            from app.core.confidence_calibrator import ConfidenceCalibrator
            import numpy as np

            calibrator = ConfidenceCalibrator()

            # Extract predictions and labels
            predictions = np.array([s['predicted_confidence'] for s in training_data])
            labels = np.array([1 if s['was_correct'] else 0 for s in training_data])

            # Train
            calibrator.fit(predictions, labels)

            # Calculate ECE
            ece = calibrator._calculate_expected_calibration_error(predictions, labels)

            self.log_step(
                'Calibrator Training',
                'success',
                f'Calibrator trained on {sample_count} samples (ECE: {ece:.4f})'
            )

            # Save calibrator
            import pickle
            model_dir = Path('models')
            model_dir.mkdir(exist_ok=True)

            with open(model_dir / 'calibrator.pkl', 'wb') as f:
                pickle.dump(calibrator, f)

            self.log_step('Calibrator Training', 'success', 'Calibrator model saved')

            if ece > 0.05:
                self.log_step(
                    'Calibrator Training',
                    'warning',
                    f'ECE above target: {ece:.4f} > 0.05'
                )
                self.status['calibrator'] = 'warning'
            else:
                self.status['calibrator'] = 'success'

            return True

        except Exception as e:
            self.status['calibrator'] = 'failed'
            self.log_step('Calibrator Training', 'error', f'Exception: {str(e)}')
            return False

    def run_smoke_tests(self) -> bool:
        """
        Run smoke tests on sample documents.

        Returns:
            True if smoke tests pass, False otherwise
        """
        self.log_step('Smoke Tests', 'info', 'Running smoke tests...')

        try:
            from app.core.anomaly_detector import AnomalyDetector

            # Create test clauses
            test_clauses = [
                {
                    'clause_number': '1.1',
                    'text': 'We may sell your personal data to third parties for marketing purposes.'
                },
                {
                    'clause_number': '1.2',
                    'text': 'We collect standard information like name and email for account creation.'
                },
                {
                    'clause_number': '2.1',
                    'text': 'We are not liable for any damages, including financial losses.'
                }
            ]

            # Initialize detector
            detector = AnomalyDetector()

            # Run detection
            start_time = time.time()

            try:
                report = detector.detect_anomalies(
                    clauses=test_clauses,
                    document_id='smoke_test_001',
                    company_name='Test Company',
                    document_context={}
                )

                elapsed_time = time.time() - start_time

                # Verify report structure
                required_keys = [
                    'document_id',
                    'overall_risk_score',
                    'high_severity_alerts',
                    'medium_severity_alerts',
                    'low_severity_alerts',
                    'compound_risks',
                    'ranking_metadata',
                    'pipeline_performance'
                ]

                missing_keys = [k for k in required_keys if k not in report]

                if missing_keys:
                    self.log_step(
                        'Smoke Tests',
                        'error',
                        f'Missing report keys: {", ".join(missing_keys)}'
                    )
                    self.status['smoke_tests'] = 'failed'
                    return False

                # Log results
                total_alerts = report['total_alerts_shown']
                risk_score = report['overall_risk_score']

                self.log_step(
                    'Smoke Tests',
                    'success',
                    f'Pipeline executed: {total_alerts} alerts, risk score: {risk_score:.1f}/10'
                )
                self.log_step(
                    'Smoke Tests',
                    'success',
                    f'Processing time: {elapsed_time:.2f}s'
                )

                # Check performance
                if elapsed_time > 30:
                    self.log_step(
                        'Smoke Tests',
                        'warning',
                        f'Slow processing: {elapsed_time:.2f}s (target: <30s)'
                    )

                self.status['smoke_tests'] = 'success'
                return True

            except Exception as e:
                self.status['smoke_tests'] = 'failed'
                self.log_step('Smoke Tests', 'error', f'Pipeline execution failed: {str(e)}')
                return False

        except Exception as e:
            self.status['smoke_tests'] = 'failed'
            self.log_step('Smoke Tests', 'error', f'Exception: {str(e)}')
            return False

    def verify_api_endpoints(self) -> bool:
        """
        Verify API endpoints are accessible and responding.

        Returns:
            True if API verification successful, False otherwise
        """
        if self.args.test_only:
            self.log_step('API Verification', 'info', 'Skipped (test-only mode)')
            self.status['api_verification'] = 'skipped'
            return True

        self.log_step('API Verification', 'info', 'Verifying API endpoints...')

        try:
            import requests

            # API base URL (adjust based on environment)
            base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')

            # Try to connect to health endpoint
            try:
                response = requests.get(f'{base_url}/health', timeout=5)

                if response.status_code == 200:
                    self.log_step('API Verification', 'success', 'Health endpoint responding')
                else:
                    self.log_step(
                        'API Verification',
                        'warning',
                        f'Health endpoint returned: {response.status_code}'
                    )
            except requests.RequestException as e:
                self.log_step(
                    'API Verification',
                    'warning',
                    f'Health endpoint not accessible: {str(e)}'
                )

            # Check docs endpoint
            try:
                response = requests.get(f'{base_url}/api/v1/docs', timeout=5)

                if response.status_code == 200:
                    self.log_step('API Verification', 'success', 'API docs accessible')
                else:
                    self.log_step(
                        'API Verification',
                        'warning',
                        f'API docs returned: {response.status_code}'
                    )
            except requests.RequestException as e:
                self.log_step(
                    'API Verification',
                    'warning',
                    f'API docs not accessible: {str(e)}'
                )

            self.status['api_verification'] = 'success'
            return True

        except Exception as e:
            self.status['api_verification'] = 'warning'
            self.log_step(
                'API Verification',
                'warning',
                f'Could not verify API: {str(e)}'
            )
            return True  # Don't fail deployment on API verification

    def generate_deployment_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive deployment report.

        Returns:
            Deployment report dictionary
        """
        deployment_end = datetime.utcnow()
        duration = (deployment_end - self.deployment_start).total_seconds()

        # Determine overall status
        failed_steps = [k for k, v in self.status.items() if v == 'failed']
        warning_steps = [k for k, v in self.status.items() if v == 'warning']

        if failed_steps:
            overall_status = 'FAILED'
        elif warning_steps:
            overall_status = 'SUCCESS_WITH_WARNINGS'
        else:
            overall_status = 'SUCCESS'

        report = {
            'deployment_id': self.deployment_start.strftime('%Y%m%d_%H%M%S'),
            'start_time': self.deployment_start.isoformat(),
            'end_time': deployment_end.isoformat(),
            'duration_seconds': duration,
            'overall_status': overall_status,
            'step_status': self.status,
            'errors': self.errors,
            'warnings': self.warnings,
            'deployment_log': self.deployment_log,
            'summary': {
                'total_steps': len(self.status),
                'successful': sum(1 for v in self.status.values() if v == 'success'),
                'failed': len(failed_steps),
                'warnings': len(warning_steps),
                'skipped': sum(1 for v in self.status.values() if v == 'skipped')
            }
        }

        return report

    def print_deployment_report(self, report: Dict[str, Any]):
        """Print formatted deployment report."""
        print("\n" + "=" * 70)
        print("ANOMALY DETECTION DEPLOYMENT REPORT")
        print("=" * 70)
        print(f"\nDeployment ID: {report['deployment_id']}")
        print(f"Status: {report['overall_status']}")
        print(f"Duration: {report['duration_seconds']:.2f} seconds")
        print(f"\nStep Summary:")
        print(f"  ✓ Successful: {report['summary']['successful']}")
        print(f"  ✗ Failed: {report['summary']['failed']}")
        print(f"  ⚠ Warnings: {report['summary']['warnings']}")
        print(f"  ⊘ Skipped: {report['summary']['skipped']}")

        print(f"\nStep Status:")
        for step, status in report['step_status'].items():
            symbol = {
                'success': '✓',
                'failed': '✗',
                'warning': '⚠',
                'skipped': '⊘',
                'pending': '○'
            }.get(status, '?')
            print(f"  {symbol} {step}: {status}")

        if report['errors']:
            print(f"\nErrors ({len(report['errors'])}):")
            for error in report['errors']:
                print(f"  • {error['step']}: {error['message']}")

        if report['warnings']:
            print(f"\nWarnings ({len(report['warnings'])}):")
            for warning in report['warnings']:
                print(f"  • {warning['step']}: {warning['message']}")

        print("\n" + "=" * 70)

        # Print next steps
        if report['overall_status'] == 'FAILED':
            print("\n⚠ DEPLOYMENT FAILED - ROLLBACK INSTRUCTIONS:")
            print("1. Review error messages above")
            print("2. Fix issues and re-run deployment")
            print("3. If database was migrated, rollback with:")
            print("   cd backend && python -m alembic downgrade -1")
            print("4. Check deployment.log for detailed logs")
        elif report['overall_status'] == 'SUCCESS_WITH_WARNINGS':
            print("\n⚠ DEPLOYMENT COMPLETED WITH WARNINGS:")
            print("1. Review warning messages above")
            print("2. Address warnings before production use")
            print("3. Some features may have limited functionality")
        else:
            print("\n✓ DEPLOYMENT SUCCESSFUL!")
            print("1. Run final tests: pytest backend/tests/test_anomaly_detection_pipeline.py")
            print("2. Start API server: uvicorn app.main:app --reload")
            print("3. Access API docs: http://localhost:8000/api/v1/docs")
            print("4. Monitor logs: tail -f deployment.log")

        print("=" * 70 + "\n")

    def save_deployment_report(self, report: Dict[str, Any]):
        """Save deployment report to file."""
        report_path = Path(f"deployment_report_{report['deployment_id']}.json")

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Deployment report saved to: {report_path}")

    def deploy(self) -> bool:
        """
        Run complete deployment process.

        Returns:
            True if deployment successful, False otherwise
        """
        logger.info("=" * 70)
        logger.info("ANOMALY DETECTION DEPLOYMENT STARTED")
        logger.info("=" * 70)

        try:
            # Run deployment steps
            steps = [
                ('Check Dependencies', self.check_dependencies),
                ('Run Migrations', self.run_migrations),
                ('Verify Pinecone', self.verify_pinecone_indexes),
                ('Validate Baseline Corpus', self.validate_baseline_corpus),
                ('Train Calibrator', self.train_calibrator),
                ('Run Smoke Tests', self.run_smoke_tests),
                ('Verify API Endpoints', self.verify_api_endpoints),
            ]

            for step_name, step_func in steps:
                logger.info(f"\n{'─' * 70}")
                logger.info(f"STEP: {step_name}")
                logger.info(f"{'─' * 70}")

                success = step_func()

                # Stop on critical failures
                if not success and step_name in [
                    'Check Dependencies',
                    'Run Migrations',
                    'Run Smoke Tests'
                ]:
                    logger.error(f"Critical step failed: {step_name}")
                    logger.error("Deployment aborted")
                    return False

            return True

        except KeyboardInterrupt:
            logger.warning("\n\nDeployment interrupted by user")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during deployment: {str(e)}", exc_info=True)
            return False


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Deploy Anomaly Detection System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full deployment
  python scripts/deploy_anomaly_detection.py

  # Skip baseline corpus validation
  python scripts/deploy_anomaly_detection.py --skip-baseline

  # Skip calibrator training
  python scripts/deploy_anomaly_detection.py --skip-calibrator

  # Test-only mode (no database changes)
  python scripts/deploy_anomaly_detection.py --test-only

  # Multiple flags
  python scripts/deploy_anomaly_detection.py --skip-baseline --skip-calibrator
        """
    )

    parser.add_argument(
        '--skip-baseline',
        action='store_true',
        help='Skip baseline corpus validation'
    )

    parser.add_argument(
        '--skip-calibrator',
        action='store_true',
        help='Skip calibrator training'
    )

    parser.add_argument(
        '--test-only',
        action='store_true',
        help='Run tests without deployment (no database changes)'
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create deployer
    deployer = AnomalyDetectionDeployer(args)

    # Run deployment
    success = deployer.deploy()

    # Generate report
    report = deployer.generate_deployment_report()

    # Print report
    deployer.print_deployment_report(report)

    # Save report
    deployer.save_deployment_report(report)

    # Exit with appropriate code
    if success and report['overall_status'] == 'SUCCESS':
        sys.exit(0)
    elif report['overall_status'] == 'SUCCESS_WITH_WARNINGS':
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
