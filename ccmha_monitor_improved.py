#!/usr/bin/env python3
"""
CCMHA Schedule Monitor - Combined Script (Improved)
Orchestrates scraping and email notification
"""

import subprocess
import sys
import os
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def run_script(script_path: str, script_name: str) -> bool:
    """Run a Python script and return success status"""
    try:
        logger.info(f"{'='*60}")
        logger.info(f"Executing: {script_name}")
        logger.info(f"{'='*60}")

        # Pass environment variables to subprocess
        env = os.environ.copy()

        result = subprocess.run(
            [sys.executable, script_path],
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        # Log output
        if result.stdout:
            logger.info(f"{script_name} output:\n{result.stdout}")

        if result.stderr:
            logger.warning(f"{script_name} stderr:\n{result.stderr}")

        if result.returncode == 0:
            logger.info(f"✓ {script_name} completed successfully")
            return True
        else:
            logger.error(f"✗ {script_name} failed with exit code {result.returncode}")
            return False

    except subprocess.TimeoutExpired:
        logger.error(f"✗ {script_name} timed out after 5 minutes")
        return False
    except Exception as e:
        logger.error(f"✗ {script_name} failed with exception: {e}", exc_info=True)
        return False


def check_environment() -> bool:
    """Check if required environment variables are set"""
    test_mode = os.getenv('TEST_MODE', 'false').lower() in ('true', '1', 'yes')

    if test_mode:
        logger.info("Running in TEST MODE - email sending will be simulated")
        return True

    required_vars = ['SENDER_EMAIL', 'SENDER_PASSWORD', 'RECIPIENT_EMAILS']
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        logger.warning(f"Missing environment variables: {', '.join(missing)}")
        logger.warning("Email notification may fail. Set TEST_MODE=true to skip email.")
        return False

    return True


def main():
    """Main execution function"""
    logger.info("="*60)
    logger.info("CCMHA Schedule Monitor - Starting (Improved)")
    logger.info("="*60)

    # Check environment
    env_ok = check_environment()
    if not env_ok:
        logger.warning("Environment check failed, but continuing...")

    # Get script directory
    script_dir = Path(__file__).parent

    # Determine which scripts to use (prefer improved versions)
    scraper_script = script_dir / 'ccmha_scraper_improved.py'
    if not scraper_script.exists():
        scraper_script = script_dir / 'ccmha_scraper.py'
        logger.info("Using original scraper script")
    else:
        logger.info("Using improved scraper script")

    email_script = script_dir / 'ccmha_email_notifier_improved.py'
    if not email_script.exists():
        email_script = script_dir / 'ccmha_email_notifier.py'
        logger.info("Using original email script")
    else:
        logger.info("Using improved email script")

    success_count = 0
    total_steps = 2

    # Step 1: Run scraper
    logger.info(f"\n{'='*60}")
    logger.info("Step 1/2: Scraping schedule...")
    logger.info(f"{'='*60}")

    if run_script(str(scraper_script), "Scraper"):
        success_count += 1
    else:
        logger.error("Scraper failed. Aborting.")
        sys.exit(1)

    # Step 2: Send email notification
    logger.info(f"\n{'='*60}")
    logger.info("Step 2/2: Sending email notification...")
    logger.info(f"{'='*60}")

    if run_script(str(email_script), "Email Notifier"):
        success_count += 1
    else:
        logger.error("Email notification failed.")
        sys.exit(1)

    # Final summary
    logger.info(f"\n{'='*60}")
    logger.info(f"CCMHA Schedule Monitor - Completed Successfully")
    logger.info(f"Steps completed: {success_count}/{total_steps}")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
