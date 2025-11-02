#!/usr/bin/env python3
"""
Email notification script for CCMHA Schedule (Improved)
- Added test mode
- Better error handling
- Configurable paths
- Enhanced logging
"""

import os
import sys
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import List, Dict
import csv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class EmailNotifier:
    """Handle email notifications for schedule updates"""

    def __init__(self, smtp_server: str, smtp_port: int,
                 sender_email: str, sender_password: str, test_mode: bool = False):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.test_mode = test_mode

        if test_mode:
            logger.info("TEST MODE: Emails will not be sent")

    def create_html_report(self, games: List[Dict]) -> str:
        """Create an HTML email report from games data"""

        if not games:
            return """
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2 style="color: #2c3e50;">CCMHA Weekly Schedule Report - Amherst Stadium</h2>
                    <p style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107;">
                        <strong>No games scheduled</strong> at Amherst Stadium for the upcoming week.
                    </p>
                    <p style="color: #7f8c8d; font-size: 12px;"><em>Report generated: {}</em></p>
                </body>
            </html>
            """.format(datetime.now().strftime('%Y-%m-%d %H:%M'))

        # Start HTML
        html = """
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                h2 {{ color: #2c3e50; }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 20px 0;
                }}
                th {{
                    background-color: #3498db;
                    color: white;
                    padding: 12px;
                    text-align: left;
                }}
                td {{
                    border: 1px solid #ddd;
                    padding: 10px;
                }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                tr:hover {{ background-color: #e8f4f8; }}
                .summary {{
                    background-color: #d4edda;
                    border-left: 4px solid #28a745;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 5px;
                }}
                .footer {{
                    margin-top: 30px;
                    font-size: 12px;
                    color: #7f8c8d;
                }}
                .test-mode {{
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 10px;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <h2>🏒 CCMHA Weekly Schedule Report - Amherst Stadium</h2>

            <div class="summary">
                <strong>Summary:</strong> {game_count} game(s) scheduled at Amherst Stadium for the upcoming week
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Time</th>
                        <th>Type</th>
                        <th>League</th>
                        <th>Team</th>
                        <th>Venue</th>
                    </tr>
                </thead>
                <tbody>
        """.format(game_count=len(games))

        # Add game rows
        for game in games:
            # Format time nicely
            start_time = game.get('start_time', 'TBA')
            end_time = game.get('end_time', '')
            time_display = f"{start_time}"
            if end_time:
                time_display = f"{start_time} - {end_time}"

            html += f"""
                    <tr>
                        <td>{game.get('date', 'TBA')}</td>
                        <td>{time_display}</td>
                        <td>{game.get('type', 'N/A')}</td>
                        <td>{game.get('league', 'N/A')}</td>
                        <td>{game.get('team', 'TBA')}</td>
                        <td>{game.get('venue', 'N/A')}</td>
                    </tr>
            """

        # Close HTML
        test_mode_banner = ""
        if self.test_mode:
            test_mode_banner = """
            <div class="test-mode">
                <strong>⚠️ TEST MODE:</strong> This email was generated in test mode and would not normally be sent.
            </div>
            """

        html += """
                </tbody>
            </table>

            {test_mode_banner}

            <div class="footer">
                <p><em>Report generated: {timestamp}</em></p>
                <p>This is an automated report. For the latest schedule, visit:
                <a href="https://ccmha.grayjayleagues.com/l/561/cumberland-county-minor-hockey-association/schedule/">
                CCMHA Schedule</a></p>
            </div>
        </body>
        </html>
        """.format(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M'),
            test_mode_banner=test_mode_banner
        )

        return html

    def send_email(self, recipient_emails: List[str],
                   subject: str, html_content: str,
                   attachment_path: str = None) -> bool:
        """Send email with HTML content and optional attachment"""

        if self.test_mode:
            logger.info("="*60)
            logger.info("TEST MODE - Email would be sent to:")
            logger.info(f"Recipients: {recipient_emails}")
            logger.info(f"Subject: {subject}")
            logger.info(f"Attachment: {attachment_path}")
            logger.info("="*60)
            # Still create the email for validation
            msg = self._create_message(recipient_emails, subject, html_content, attachment_path)
            logger.info("Email created successfully (not sent in test mode)")
            return True

        logger.info(f"Preparing email to {len(recipient_emails)} recipient(s)")

        try:
            msg = self._create_message(recipient_emails, subject, html_content, attachment_path)

            # Connect to SMTP server and send
            logger.info(f"Connecting to {self.smtp_server}:{self.smtp_port}")
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                server.starttls()
                logger.info("Logging in to SMTP server...")
                server.login(self.sender_email, self.sender_password)
                logger.info("Sending email...")
                server.send_message(msg)

            logger.info("Email sent successfully!")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP Authentication failed. Check email credentials.")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error occurred: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            return False

    def _create_message(self, recipient_emails: List[str],
                       subject: str, html_content: str,
                       attachment_path: str = None) -> MIMEMultipart:
        """Create email message with content and attachment"""
        msg = MIMEMultipart('alternative')
        msg['From'] = self.sender_email
        msg['To'] = ', '.join(recipient_emails)
        msg['Subject'] = subject

        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)

        # Attach CSV file if provided
        if attachment_path and os.path.exists(attachment_path):
            try:
                with open(attachment_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename={os.path.basename(attachment_path)}'
                    )
                    msg.attach(part)
                    logger.info(f"Attached file: {attachment_path}")
            except Exception as e:
                logger.warning(f"Failed to attach file {attachment_path}: {e}")

        return msg


def load_games_from_csv(csv_file: str) -> List[Dict]:
    """Load games data from CSV file"""
    games = []
    try:
        if not os.path.exists(csv_file):
            logger.error(f"CSV file not found: {csv_file}")
            return games

        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            games = list(reader)

        logger.info(f"Loaded {len(games)} games from {csv_file}")
    except Exception as e:
        logger.error(f"Error loading CSV: {e}", exc_info=True)

    return games


def validate_email_config() -> bool:
    """Validate email configuration"""
    required_vars = ['SMTP_SERVER', 'SMTP_PORT', 'SENDER_EMAIL', 'SENDER_PASSWORD']
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        return False

    return True


def main():
    """Main execution function"""
    logger.info("="*60)
    logger.info("Starting CCMHA Email Notification (Improved)")
    logger.info("="*60)

    # Check test mode
    test_mode = os.getenv('TEST_MODE', 'false').lower() in ('true', '1', 'yes')

    # Validate configuration
    if not test_mode and not validate_email_config():
        logger.error("Invalid email configuration. Exiting.")
        sys.exit(1)

    # Configuration
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'your_email@gmail.com')
    SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', 'your_app_password')

    # Recipient emails
    recipient_emails_str = os.getenv('RECIPIENT_EMAILS', 'canteen@example.com')
    RECIPIENT_EMAILS = [email.strip() for email in recipient_emails_str.split(',')]

    # CSV file path
    OUTPUT_DIR = os.getenv('OUTPUT_DIR', '/var/www/ccmha')
    CSV_FILE = os.path.join(OUTPUT_DIR, 'amherst_stadium_schedule.csv')

    logger.info(f"CSV file: {CSV_FILE}")
    logger.info(f"Recipients: {len(RECIPIENT_EMAILS)}")

    # Load games from CSV
    games = load_games_from_csv(CSV_FILE)

    # Create email notifier
    notifier = EmailNotifier(
        smtp_server=SMTP_SERVER,
        smtp_port=SMTP_PORT,
        sender_email=SENDER_EMAIL,
        sender_password=SENDER_PASSWORD,
        test_mode=test_mode
    )

    # Create HTML report
    html_content = notifier.create_html_report(games)

    # Prepare subject
    week_start = datetime.now().strftime('%b %d, %Y')
    subject = f"CCMHA Weekly Schedule - Amherst Stadium ({week_start})"

    if test_mode:
        subject = f"[TEST] {subject}"

    # Send email
    success = notifier.send_email(
        recipient_emails=RECIPIENT_EMAILS,
        subject=subject,
        html_content=html_content,
        attachment_path=CSV_FILE if os.path.exists(CSV_FILE) else None
    )

    logger.info("="*60)
    if success:
        logger.info("Notification completed successfully")
        logger.info("="*60)
        sys.exit(0)
    else:
        logger.error("Notification failed")
        logger.info("="*60)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Email notification failed: {e}", exc_info=True)
        sys.exit(1)
