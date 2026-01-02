#!/usr/bin/env python3
"""
CCMHA Complete Schedule Scraper - Gets EVERYTHING at Amherst Stadium
Uses Master Schedule API to get games, practices, and all ice times
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Schedule type mapping
SCHEDULE_TYPES = {
    1: 'Practice',
    2: 'Off-Ice Training',
    3: 'Team Meeting',
    4: 'Tournament Game',
    5: 'Other',
    6: 'Evaluation',
    7: 'Game'
}


class CCMHACompleteScraper:
    """Scraper for ALL ice times at Amherst Stadium"""

    def __init__(self, base_url: str = "https://ccmha.grayjayleagues.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })

    def get_all_schedule(self, days_ahead: int = 14) -> List[Dict]:
        """Fetch complete schedule including games, practices, everything"""
        logger.info(f"Fetching complete schedule for next {days_ahead} days")

        try:
            # Use master schedule API with ALL schedule types
            url = (f"{self.base_url}/api/teams/frontendMasterSchedule/"
                   f"?true=1&team_id=0&league_id=0"
                   f"&schedule_types=7,1,2,3,4,6,5"  # All types
                   f"&season_id=0&show_past=0")

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()

            if data.get('status') != 'success':
                logger.error(f"API returned non-success status: {data.get('status')}")
                return []

            items = data.get('data', [])
            logger.info(f"API returned {len(items)} total schedule items")

            # Filter by date range
            today = datetime.now().date()
            end_date = today + timedelta(days=days_ahead)

            filtered_items = []
            for item in items:
                # Check both team_schedule_date (practices) and game_date (games)
                date_str = item.get('team_schedule_date') or item.get('game_date')
                if date_str:
                    try:
                        item_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        if today <= item_date <= end_date:
                            filtered_items.append(item)
                    except ValueError:
                        logger.warning(f"Could not parse date: {date_str}")

            logger.info(f"Filtered to {len(filtered_items)} items in date range")
            return filtered_items

        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching schedule: {e}", exc_info=True)
            return []

    def filter_by_venue(self, items: List[Dict], venue_filter: str = "Amherst Stadium") -> List[Dict]:
        """Filter items by venue name"""
        logger.info(f"Filtering for venue: {venue_filter}")

        filtered = []
        for item in items:
            venue_name = item.get('venue_name')
            if venue_name and venue_filter.lower() in venue_name.lower():
                filtered.append(item)

        logger.info(f"Found {len(filtered)} items at {venue_filter}")
        return filtered

    def format_items(self, items: List[Dict]) -> List[Dict]:
        """Format API response into simplified structure"""
        # First, separate games and non-games to handle duplicates
        games = []
        non_games = []

        for item in items:
            # Check if this is a game or practice/other schedule item
            if 'game_id' in item:
                # This is a GAME - use game fields
                team_a = item.get('team_a_name', '')
                team_b = item.get('team_b_name', '')
                team_display = f"{team_a} vs {team_b}" if team_a and team_b else 'TBA'

                formatted_item = {
                    'date': item.get('game_date', ''),
                    'start_time': item.get('game_start_time', ''),
                    'end_time': item.get('game_end_time', ''),
                    'type': 'Game',
                    'league': item.get('league_name', ''),
                    'team': team_display,
                    'venue': item.get('venue_name', ''),
                }
                games.append(formatted_item)
            else:
                # This is a PRACTICE/OTHER - use team_schedule fields
                type_id = item.get('team_schedule_type_id', 1)
                type_name = SCHEDULE_TYPES.get(type_id, 'Other')

                formatted_item = {
                    'date': item.get('team_schedule_date', ''),
                    'start_time': item.get('team_schedule_start_time', ''),
                    'end_time': item.get('team_schedule_end_time', ''),
                    'type': type_name,
                    'league': item.get('league_name', ''),
                    'team': item.get('team_name', ''),
                    'venue': item.get('venue_name', ''),
                }
                non_games.append(formatted_item)

        # Create a set of game time slots (date + start_time)
        game_slots = {(g['date'], g['start_time']) for g in games}

        # Filter out non-games that conflict with game slots
        # (The API returns duplicate entries for games)
        non_games_filtered = [
            ng for ng in non_games
            if (ng['date'], ng['start_time']) not in game_slots
        ]

        # Combine and sort
        all_items = games + non_games_filtered
        all_items.sort(key=lambda x: (x['date'], x['start_time']))

        logger.info(f"Found {len(games)} games, {len(non_games_filtered)} practices/other (removed {len(non_games) - len(non_games_filtered)} duplicates)")

        return all_items


def save_to_csv(items: List[Dict], filename: str):
    """Save items to CSV file"""
    if not items:
        logger.warning("No items to save")
        df = pd.DataFrame(columns=[
            'date', 'start_time', 'end_time', 'type', 'league', 'team', 'venue'
        ])
        df.to_csv(filename, index=False)
        logger.info(f"Created empty CSV file: {filename}")
        return

    df = pd.DataFrame(items)
    df.to_csv(filename, index=False)
    logger.info(f"Saved {len(items)} items to {filename}")

def save_to_json(items: List[Dict], filename: str, days_ahead: int, venue_filter: str, timezone: str):
    """Save items to JSON for display clients"""
    payload = {
        'generated_at': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'timezone': timezone,
        'venue_filter': venue_filter,
        'days_ahead': days_ahead,
        'items': items
    }
    with open(filename, 'w') as f:
        json.dump(payload, f, indent=2)
    logger.info(f"Saved JSON output to {filename}")


def main():
    """Main execution function"""
    logger.info("="*60)
    logger.info("Starting CCMHA Complete Schedule Scraper")
    logger.info("="*60)

    # Configuration from environment variables
    DAYS_AHEAD = int(os.getenv('DAYS_AHEAD', '14'))
    VENUE_FILTER = os.getenv('VENUE_FILTER', 'Amherst Stadium')
    OUTPUT_DIR = os.getenv('OUTPUT_DIR', '/var/www/ccmha')
    OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'amherst_stadium_schedule.csv')
    OUTPUT_JSON = os.path.join(OUTPUT_DIR, 'amherst_stadium_schedule.json')
    TIMEZONE = os.getenv('TIMEZONE', 'America/Halifax')

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Days ahead: {DAYS_AHEAD}")
    logger.info(f"Venue filter: {VENUE_FILTER}")

    # Scrape using Master Schedule API
    scraper = CCMHACompleteScraper()

    # Get all schedule items
    all_items = scraper.get_all_schedule(DAYS_AHEAD)

    if not all_items:
        logger.warning("No schedule items found")
        save_to_csv([], OUTPUT_FILE)
        return []

    # Filter by venue
    venue_items = scraper.filter_by_venue(all_items, VENUE_FILTER)

    # Format the items
    formatted_items = scraper.format_items(venue_items)

    # Save to CSV
    save_to_csv(formatted_items, OUTPUT_FILE)
    save_to_json(formatted_items, OUTPUT_JSON, DAYS_AHEAD, VENUE_FILTER, TIMEZONE)

    # Display summary
    logger.info("="*60)
    logger.info(f"SUMMARY: Found {len(formatted_items)} ice times at {VENUE_FILTER}")
    if formatted_items:
        logger.info("Ice Times:")
        for item in formatted_items:
            logger.info(f"  {item['date']} {item['start_time']}-{item['end_time']} | {item['type']} | {item['league']} | {item['team']}")
    logger.info("="*60)

    return formatted_items


if __name__ == "__main__":
    try:
        items = main()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Scraper failed: {e}", exc_info=True)
        sys.exit(1)
