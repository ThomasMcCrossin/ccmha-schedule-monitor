#!/usr/bin/env python3
"""
CCMHA Schedule Change Detector
Monitors for changes in the next 7 days and sends email alerts
"""

import os
import sys
import logging
import hashlib
import json
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def load_schedule_csv(filepath: str) -> List[Dict]:
    """Load schedule from CSV file"""
    if not os.path.exists(filepath):
        logger.warning(f"Schedule file not found: {filepath}")
        return []

    try:
        df = pd.read_csv(filepath)
        return df.to_dict('records')
    except Exception as e:
        logger.error(f"Error loading CSV: {e}")
        return []


def filter_next_n_days(items: List[Dict], days: int = 7) -> List[Dict]:
    """Filter items to only include next N days (excluding today's completed games)"""
    now = datetime.now()
    today = now.date()
    end_date = today + timedelta(days=days)

    filtered = []
    for item in items:
        try:
            item_date = datetime.strptime(item['date'], '%Y-%m-%d').date()

            # For future dates, include all games
            if item_date > today and item_date <= end_date:
                filtered.append(item)
            # For today's games, only include if they haven't started yet
            elif item_date == today:
                # Try to parse start time to check if game is in the future
                try:
                    start_time_str = item.get('start_time', '')
                    if start_time_str:
                        # Parse time (format: HH:MM or HH:MM:SS)
                        game_datetime = datetime.strptime(f"{item['date']} {start_time_str}", '%Y-%m-%d %H:%M:%S' if ':' in start_time_str and start_time_str.count(':') == 2 else '%Y-%m-%d %H:%M')
                        # Only include if game hasn't started yet (or started within last hour for safety margin)
                        if game_datetime > now - timedelta(hours=1):
                            filtered.append(item)
                    else:
                        # No time info, include it to be safe
                        filtered.append(item)
                except (ValueError, KeyError):
                    # If we can't parse the time, include it to be safe
                    filtered.append(item)

        except (ValueError, KeyError) as e:
            logger.warning(f"Could not parse date for item: {e}")
            continue

    return filtered


def create_schedule_key(item: Dict) -> str:
    """Create unique key for a schedule item"""
    return f"{item['date']}_{item['start_time']}_{item['type']}_{item['league']}"


def create_schedule_hash(items: List[Dict]) -> str:
    """Create hash of schedule for comparison"""
    # Sort items to ensure consistent hashing
    sorted_items = sorted(items, key=lambda x: (x['date'], x['start_time'], x['type']))

    # Create string representation
    schedule_str = json.dumps(sorted_items, sort_keys=True)

    # Return hash
    return hashlib.md5(schedule_str.encode()).hexdigest()


def detect_changes(old_items: List[Dict], new_items: List[Dict]) -> Dict:
    """Detect what changed between two schedules"""

    # Create sets of keys
    old_keys = {create_schedule_key(item): item for item in old_items}
    new_keys = {create_schedule_key(item): item for item in new_items}

    old_key_set = set(old_keys.keys())
    new_key_set = set(new_keys.keys())

    # Find additions and deletions
    added_keys = new_key_set - old_key_set
    removed_keys = old_key_set - new_key_set
    common_keys = old_key_set & new_key_set

    # Find modifications (same key but different details)
    modified_keys = []
    for key in common_keys:
        old_item = old_keys[key]
        new_item = new_keys[key]

        # Check if team or venue changed
        if (old_item.get('team') != new_item.get('team') or
            old_item.get('venue') != new_item.get('venue') or
            old_item.get('end_time') != new_item.get('end_time')):
            modified_keys.append((key, old_item, new_item))

    changes = {
        'added': [new_keys[key] for key in added_keys],
        'removed': [old_keys[key] for key in removed_keys],
        'modified': modified_keys,
        'has_changes': len(added_keys) > 0 or len(removed_keys) > 0 or len(modified_keys) > 0
    }

    return changes


def save_snapshot(items: List[Dict], filepath: str):
    """Save current schedule as snapshot for future comparison"""
    try:
        df = pd.DataFrame(items)
        df.to_csv(filepath, index=False)
        logger.info(f"Saved snapshot to {filepath}")
    except Exception as e:
        logger.error(f"Error saving snapshot: {e}")


def format_changes_for_email(changes: Dict) -> str:
    """Format changes into HTML for email"""

    if not changes['has_changes']:
        return "<p>No changes detected in the next 7 days.</p>"

    html = "<h2>Schedule Changes Detected (Next 7 Days)</h2>"

    # Added items
    if changes['added']:
        html += "<h3 style='color: green;'>➕ Added Ice Times</h3>"
        html += "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse;'>"
        html += "<tr style='background-color: #4CAF50; color: white;'>"
        html += "<th>Date</th><th>Time</th><th>Type</th><th>League</th><th>Team</th><th>Venue</th>"
        html += "</tr>"

        for item in sorted(changes['added'], key=lambda x: (x['date'], x['start_time'])):
            html += f"<tr>"
            html += f"<td>{item['date']}</td>"
            html += f"<td>{item['start_time']} - {item['end_time']}</td>"
            html += f"<td>{item['type']}</td>"
            html += f"<td>{item['league']}</td>"
            html += f"<td>{item['team']}</td>"
            html += f"<td>{item['venue']}</td>"
            html += f"</tr>"
        html += "</table><br>"

    # Removed items
    if changes['removed']:
        html += "<h3 style='color: red;'>➖ Removed Ice Times</h3>"
        html += "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse;'>"
        html += "<tr style='background-color: #f44336; color: white;'>"
        html += "<th>Date</th><th>Time</th><th>Type</th><th>League</th><th>Team</th><th>Venue</th>"
        html += "</tr>"

        for item in sorted(changes['removed'], key=lambda x: (x['date'], x['start_time'])):
            html += f"<tr>"
            html += f"<td>{item['date']}</td>"
            html += f"<td>{item['start_time']} - {item['end_time']}</td>"
            html += f"<td>{item['type']}</td>"
            html += f"<td>{item['league']}</td>"
            html += f"<td>{item['team']}</td>"
            html += f"<td>{item['venue']}</td>"
            html += f"</tr>"
        html += "</table><br>"

    # Modified items
    if changes['modified']:
        html += "<h3 style='color: orange;'>🔄 Modified Ice Times</h3>"
        html += "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse;'>"
        html += "<tr style='background-color: #FF9800; color: white;'>"
        html += "<th>Date</th><th>Time</th><th>Type</th><th>League</th><th>Change</th>"
        html += "</tr>"

        for key, old_item, new_item in changes['modified']:
            html += f"<tr>"
            html += f"<td>{new_item['date']}</td>"
            html += f"<td>{new_item['start_time']} - {new_item['end_time']}</td>"
            html += f"<td>{new_item['type']}</td>"
            html += f"<td>{new_item['league']}</td>"

            # Describe what changed
            changes_desc = []
            if old_item.get('team') != new_item.get('team'):
                changes_desc.append(f"Team: {old_item.get('team')} → {new_item.get('team')}")
            if old_item.get('end_time') != new_item.get('end_time'):
                changes_desc.append(f"End time: {old_item.get('end_time')} → {new_item.get('end_time')}")
            if old_item.get('venue') != new_item.get('venue'):
                changes_desc.append(f"Venue: {old_item.get('venue')} → {new_item.get('venue')}")

            html += f"<td>{'<br>'.join(changes_desc)}</td>"
            html += f"</tr>"
        html += "</table><br>"

    # Summary
    html += f"<p style='font-weight: bold;'>"
    html += f"Summary: {len(changes['added'])} added, "
    html += f"{len(changes['removed'])} removed, "
    html += f"{len(changes['modified'])} modified"
    html += f"</p>"

    return html


def main():
    """Main execution function"""
    logger.info("="*60)
    logger.info("Starting CCMHA Schedule Change Detector")
    logger.info("="*60)

    # Configuration
    OUTPUT_DIR = os.getenv('OUTPUT_DIR', '/var/www/ccmha')
    DAYS_TO_MONITOR = int(os.getenv('CHANGE_MONITOR_DAYS', '7'))

    current_csv = os.path.join(OUTPUT_DIR, 'amherst_stadium_schedule.csv')
    snapshot_csv = os.path.join(OUTPUT_DIR, 'schedule_snapshot_7day.csv')
    changes_json = os.path.join(OUTPUT_DIR, 'schedule_changes.json')

    logger.info(f"Monitoring next {DAYS_TO_MONITOR} days")
    logger.info(f"Current schedule: {current_csv}")
    logger.info(f"Snapshot file: {snapshot_csv}")

    # Load current schedule
    current_all = load_schedule_csv(current_csv)
    if not current_all:
        logger.error("No current schedule found")
        sys.exit(1)

    # Filter to next 7 days
    current_items = filter_next_n_days(current_all, DAYS_TO_MONITOR)
    logger.info(f"Current schedule has {len(current_items)} items in next {DAYS_TO_MONITOR} days")

    # Check if snapshot exists
    if not os.path.exists(snapshot_csv):
        logger.info("No previous snapshot found - creating initial snapshot")
        save_snapshot(current_items, snapshot_csv)
        logger.info("No changes to report (first run)")
        sys.exit(0)

    # Load previous snapshot
    snapshot_all = load_schedule_csv(snapshot_csv)
    logger.info(f"Previous snapshot loaded: {len(snapshot_all)} items")

    # Filter snapshot to same time window (exclude naturally expired events)
    snapshot_items = filter_next_n_days(snapshot_all, DAYS_TO_MONITOR)
    logger.info(f"Previous snapshot filtered to next {DAYS_TO_MONITOR} days: {len(snapshot_items)} items")

    # Detect changes
    changes = detect_changes(snapshot_items, current_items)

    if changes['has_changes']:
        logger.info("CHANGES DETECTED!")
        logger.info(f"  Added: {len(changes['added'])}")
        logger.info(f"  Removed: {len(changes['removed'])}")
        logger.info(f"  Modified: {len(changes['modified'])}")

        # Save changes to JSON for email script to pick up
        with open(changes_json, 'w') as f:
            # Convert modified items to serializable format
            changes_serializable = {
                'added': changes['added'],
                'removed': changes['removed'],
                'modified': [
                    {'key': key, 'old': old, 'new': new}
                    for key, old, new in changes['modified']
                ],
                'has_changes': changes['has_changes'],
                'detection_time': datetime.now().isoformat()
            }
            json.dump(changes_serializable, f, indent=2)
        logger.info(f"Saved changes to {changes_json}")

        # Update snapshot
        save_snapshot(current_items, snapshot_csv)

        # Exit with code 1 to indicate changes found (triggers email)
        sys.exit(1)
    else:
        logger.info("No changes detected")
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Change detector failed: {e}", exc_info=True)
        sys.exit(2)
