#!/usr/bin/env python3
"""
CCMHA Change Monitoring Workflow
1. Scrape current schedule
2. Detect changes in next 7 days
3. Send email if changes found
"""

import os
import sys
import logging
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def run_script(script_name: str, description: str) -> int:
    """Run a Python script and return exit code"""
    logger.info("="*60)
    logger.info(f"Executing: {description}")
    logger.info("="*60)

    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            timeout=120
        )

        # Print output
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                logger.info(f"{description} output: {line}")

        if result.stderr:
            for line in result.stderr.strip().split('\n'):
                if line.strip():
                    logger.warning(f"{description} stderr: {line}")

        logger.info(f"{description} exit code: {result.returncode}")
        return result.returncode

    except subprocess.TimeoutExpired:
        logger.error(f"{description} timed out after 120 seconds")
        return 124
    except Exception as e:
        logger.error(f"{description} failed: {e}")
        return 1


def main():
    """Main workflow"""
    logger.info("="*60)
    logger.info("CCMHA Schedule Change Monitor - Starting")
    logger.info("="*60)

    # Step 1: Scrape current schedule
    logger.info("")
    logger.info("="*60)
    logger.info("Step 1/3: Scraping current schedule...")
    logger.info("="*60)

    # Set to 7 days for change monitoring
    os.environ['DAYS_AHEAD'] = '7'
    os.environ['CHANGE_MONITOR_DAYS'] = '7'

    scraper_exit = run_script('ccmha_complete_scraper.py', 'Scraper')

    if scraper_exit != 0:
        logger.error("✗ Scraper failed")
        sys.exit(1)

    logger.info("✓ Scraper completed successfully")

    # Step 2: Detect changes
    logger.info("")
    logger.info("="*60)
    logger.info("Step 2/3: Detecting changes...")
    logger.info("="*60)

    detector_exit = run_script('ccmha_change_detector.py', 'Change Detector')

    if detector_exit == 0:
        logger.info("✓ No changes detected - monitoring complete")
        logger.info("="*60)
        logger.info("Change Monitor - Completed (No Changes)")
        logger.info("="*60)
        sys.exit(0)
    elif detector_exit == 1:
        logger.info("✓ Changes detected!")
    else:
        logger.error("✗ Change detector failed")
        sys.exit(1)

    # Step 3: Send change notification
    logger.info("")
    logger.info("="*60)
    logger.info("Step 3/3: Sending change notification...")
    logger.info("="*60)

    notifier_exit = run_script('ccmha_change_notifier.py', 'Change Notifier')

    if notifier_exit != 0:
        logger.error("✗ Change notifier failed")
        sys.exit(1)

    logger.info("✓ Change notification sent successfully")

    # Summary
    logger.info("")
    logger.info("="*60)
    logger.info("CCMHA Schedule Change Monitor - Completed Successfully")
    logger.info("Changes detected and notification sent")
    logger.info("="*60)

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nMonitoring interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Monitoring failed: {e}", exc_info=True)
        sys.exit(1)
