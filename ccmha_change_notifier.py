#!/usr/bin/env python3
"""
CCMHA Schedule Change Email Notifier
Sends email alerts when schedule changes are detected
"""

import os
import sys
import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def load_changes(filepath: str) -> dict:
    """Load changes from JSON file"""
    if not os.path.exists(filepath):
        logger.error(f"Changes file not found: {filepath}")
        return None

    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading changes: {e}")
        return None


def format_changes_html(changes: dict) -> str:
    """Format changes into HTML for email"""

    if not changes or not changes.get('has_changes'):
        return "<p>No changes detected.</p>"

    html = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; }
            h2 { color: #333; }
            h3 { margin-top: 20px; }
            table { border-collapse: collapse; width: 100%; margin-top: 10px; }
            th { background-color: #4CAF50; color: white; padding: 8px; text-align: left; }
            td { border: 1px solid #ddd; padding: 8px; }
            tr:nth-child(even) { background-color: #f2f2f2; }
            .added { background-color: #d4edda; }
            .removed { background-color: #f8d7da; }
            .modified { background-color: #fff3cd; }
        </style>
    </head>
    <body>
    """

    html += f"<h2>🔔 CCMHA Schedule Changes Detected (Next 7 Days)</h2>"
    html += f"<p><strong>Detected at:</strong> {datetime.now().strftime('%Y-%m-%d %I:%M %p')}</p>"

    # Added items
    if changes.get('added'):
        html += "<h3 style='color: green;'>➕ New Ice Times Added</h3>"
        html += "<table>"
        html += "<tr><th>Date</th><th>Time</th><th>Type</th><th>League</th><th>Team</th><th>Venue</th></tr>"

        for item in sorted(changes['added'], key=lambda x: (x['date'], x['start_time'])):
            html += f"<tr class='added'>"
            html += f"<td>{item['date']}</td>"
            html += f"<td>{item['start_time']} - {item['end_time']}</td>"
            html += f"<td>{item['type']}</td>"
            html += f"<td>{item['league']}</td>"
            html += f"<td>{item['team']}</td>"
            html += f"<td>{item['venue']}</td>"
            html += f"</tr>"
        html += "</table>"

    # Removed items
    if changes.get('removed'):
        html += "<h3 style='color: red;'>➖ Ice Times Cancelled/Removed</h3>"
        html += "<table>"
        html += "<tr><th>Date</th><th>Time</th><th>Type</th><th>League</th><th>Team</th><th>Venue</th></tr>"

        for item in sorted(changes['removed'], key=lambda x: (x['date'], x['start_time'])):
            html += f"<tr class='removed'>"
            html += f"<td>{item['date']}</td>"
            html += f"<td>{item['start_time']} - {item['end_time']}</td>"
            html += f"<td>{item['type']}</td>"
            html += f"<td>{item['league']}</td>"
            html += f"<td>{item['team']}</td>"
            html += f"<td>{item['venue']}</td>"
            html += f"</tr>"
        html += "</table>"

    # Modified items
    if changes.get('modified'):
        html += "<h3 style='color: orange;'>🔄 Ice Times Modified</h3>"
        html += "<table>"
        html += "<tr><th>Date</th><th>Time</th><th>Type</th><th>League</th><th>Changes</th></tr>"

        for mod in changes['modified']:
            old_item = mod['old']
            new_item = mod['new']

            html += f"<tr class='modified'>"
            html += f"<td>{new_item['date']}</td>"
            html += f"<td>{new_item['start_time']} - {new_item['end_time']}</td>"
            html += f"<td>{new_item['type']}</td>"
            html += f"<td>{new_item['league']}</td>"

            # Describe changes
            changes_desc = []
            if old_item.get('team') != new_item.get('team'):
                changes_desc.append(f"<strong>Team:</strong> {old_item.get('team')} → {new_item.get('team')}")
            if old_item.get('end_time') != new_item.get('end_time'):
                changes_desc.append(f"<strong>End:</strong> {old_item.get('end_time')} → {new_item.get('end_time')}")
            if old_item.get('venue') != new_item.get('venue'):
                changes_desc.append(f"<strong>Venue:</strong> {old_item.get('venue')} → {new_item.get('venue')}")

            html += f"<td>{'<br>'.join(changes_desc)}</td>"
            html += f"</tr>"
        html += "</table>"

    # Summary
    html += f"""
    <div style='margin-top: 30px; padding: 15px; background-color: #f0f0f0; border-left: 4px solid #4CAF50;'>
        <h3 style='margin-top: 0;'>Summary</h3>
        <ul>
            <li><strong>{len(changes.get('added', []))}</strong> ice times added</li>
            <li><strong>{len(changes.get('removed', []))}</strong> ice times removed</li>
            <li><strong>{len(changes.get('modified', []))}</strong> ice times modified</li>
        </ul>
    </div>
    """

    html += """
    <p style='margin-top: 30px; color: #666; font-size: 12px;'>
    This is an automated notification from the CCMHA Schedule Monitor.
    Changes are checked at 12:30 PM, 4:30 PM, and 1:00 AM daily for the next 7 days.
    </p>
    </body>
    </html>
    """

    return html


def send_change_notification(changes: dict, recipients: list, smtp_config: dict):
    """Send email notification about schedule changes"""

    logger.info("Preparing change notification email")

    # Create message
    msg = MIMEMultipart('alternative')
    msg['From'] = smtp_config['sender']
    msg['To'] = ', '.join(recipients)
    msg['Subject'] = f"🔔 CCMHA Schedule Alert - Changes Detected at Amherst Stadium"

    # Create HTML body
    html_content = format_changes_html(changes)

    # Attach HTML
    html_part = MIMEText(html_content, 'html')
    msg.attach(html_part)

    # Send email
    try:
        logger.info(f"Connecting to {smtp_config['server']}:{smtp_config['port']}")
        with smtplib.SMTP(smtp_config['server'], smtp_config['port']) as server:
            server.starttls()

            logger.info("Logging in to SMTP server...")
            server.login(smtp_config['sender'], smtp_config['password'])

            logger.info("Sending change notification...")
            server.send_message(msg)

        logger.info("✓ Change notification sent successfully!")
        return True

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def main():
    """Main execution function"""
    logger.info("="*60)
    logger.info("CCMHA Schedule Change Notifier")
    logger.info("="*60)

    # Configuration
    OUTPUT_DIR = os.getenv('OUTPUT_DIR', '/var/www/ccmha')
    changes_json = os.path.join(OUTPUT_DIR, 'schedule_changes.json')

    # SMTP configuration
    smtp_config = {
        'server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
        'port': int(os.getenv('SMTP_PORT', '587')),
        'sender': os.getenv('SENDER_EMAIL'),
        'password': os.getenv('SENDER_PASSWORD')
    }

    recipients = os.getenv('RECIPIENT_EMAILS', '').split(',')
    recipients = [r.strip() for r in recipients if r.strip()]

    if not recipients:
        logger.error("No recipients configured")
        sys.exit(1)

    if not smtp_config['sender'] or not smtp_config['password']:
        logger.error("Email credentials not configured")
        sys.exit(1)

    logger.info(f"Recipients: {len(recipients)}")

    # Load changes
    changes = load_changes(changes_json)
    if not changes:
        logger.error("No changes data found")
        sys.exit(1)

    if not changes.get('has_changes'):
        logger.info("No changes to notify about")
        sys.exit(0)

    # Send notification
    success = send_change_notification(changes, recipients, smtp_config)

    if success:
        # Clean up changes file after successful send
        try:
            os.remove(changes_json)
            logger.info("Cleaned up changes file")
        except:
            pass
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Change notifier failed: {e}", exc_info=True)
        sys.exit(1)
