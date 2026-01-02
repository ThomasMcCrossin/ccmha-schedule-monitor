# CCMHA Schedule Monitor

Automated schedule monitoring system for Cumberland County Minor Hockey Association (CCMHA) ice times at Amherst Stadium.

## Features

✅ **Weekly Schedule Reports** (Every Sunday 8 PM)
- Complete 14-day schedule via email
- Includes all games, practices, and ice times
- HTML email + CSV attachment

✅ **Real-Time Change Monitoring** (3x Daily)
- Monitors next 7 days for schedule changes
- Checks at 12:30 PM, 4:30 PM, and 1:00 AM
- Email alerts for additions, cancellations, and modifications

✅ **Complete Data Coverage**
- All games with full team details ("Team A vs Team B")
- All practices (U9-U18, all divisions)
- Other ice times (meetings, evaluations, etc.)
- Accurate times and venue information

## Quick Start

### 1. Prerequisites

- Docker installed
- Gmail account with app password
- Linux system with cron

### 2. Setup

```bash
# Clone repository
git clone <your-repo-url>
cd grayjay-schedule

# Create .env file
cp .env.example .env
nano .env
```

### 3. Configure .env

```bash
# Email Settings
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
RECIPIENT_EMAILS=recipient@email.com

# Scraping Settings
VENUE_FILTER=Amherst Stadium
DAYS_AHEAD=14
CHANGE_MONITOR_DAYS=7

# SMTP Settings
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

### 4. Build Docker Image

```bash
docker build -f Dockerfile.api -t ccmha-monitor:api .
```

### 5. Install Cron Jobs

```bash
# Edit crontab
crontab -e

# Add these lines:
# Weekly report - Sunday 8 PM
0 20 * * 0 /usr/bin/docker run --rm -v $(pwd)/data:/data --env-file $(pwd)/.env ccmha-monitor:api python3 ccmha_monitor.py >> $(pwd)/logs/cron.log 2>&1

# Change monitoring - 12:30 PM daily
30 12 * * * /usr/bin/docker run --rm -v $(pwd)/data:/data --env-file $(pwd)/.env ccmha-monitor:api python3 ccmha_change_monitor.py >> $(pwd)/logs/change_monitor.log 2>&1

# Change monitoring - 4:30 PM daily
30 16 * * * /usr/bin/docker run --rm -v $(pwd)/data:/data --env-file $(pwd)/.env ccmha-monitor:api python3 ccmha_change_monitor.py >> $(pwd)/logs/change_monitor.log 2>&1

# Change monitoring - 1:00 AM daily
0 1 * * * /usr/bin/docker run --rm -v $(pwd)/data:/data --env-file $(pwd)/.env ccmha-monitor:api python3 ccmha_change_monitor.py >> $(pwd)/logs/change_monitor.log 2>&1
```

## Manual Testing

### Test Weekly Report
```bash
docker run --rm -v ./data:/data --env-file .env ccmha-monitor:api python3 ccmha_monitor.py
```

### Test Change Monitoring
```bash
docker run --rm -v ./data:/data --env-file .env ccmha-monitor:api python3 ccmha_change_monitor.py
```

### Test Scraper Only
```bash
docker run --rm -v ./data:/data --env-file .env ccmha-monitor:api python3 ccmha_complete_scraper.py
```

## Architecture

### Core Components

**Scrapers:**
- `ccmha_complete_scraper.py` - Fetches schedule from GrayJay API

**Email Notifiers:**
- `ccmha_email_notifier_improved.py` - Sends weekly reports
- `ccmha_change_notifier.py` - Sends change alerts

**Workflow Orchestrators:**
- `ccmha_monitor_improved.py` - Weekly report workflow
- `ccmha_change_monitor.py` - Change monitoring workflow

**Change Detection:**
- `ccmha_change_detector.py` - Detects schedule changes

### Data Flow

**Weekly Reports:**
```
Cron (Sunday 8 PM)
  → ccmha_monitor_improved.py
    → ccmha_complete_scraper.py (14 days)
      → data/amherst_stadium_schedule.csv
    → ccmha_email_notifier_improved.py
      → Email to recipients
```

**Change Monitoring:**
```
Cron (3x daily)
  → ccmha_change_monitor.py
    → ccmha_complete_scraper.py (7 days)
      → data/amherst_stadium_schedule.csv
    → ccmha_change_detector.py
      → Compare with data/schedule_snapshot_7day.csv
      → If changes: data/schedule_changes.json
    → ccmha_change_notifier.py (if changes)
      → Email alert to recipients
```

## Technical Details

### API Integration
- **Source:** GrayJay Leagues Master Schedule API
- **Endpoint:** `https://ccmha.grayjayleagues.com/api/teams/frontendMasterSchedule/`
- **Schedule Types:** Games (7), Practices (1), Off-Ice (2), Meetings (3), Tournaments (4), Evaluations (6), Other (5)
- **Data Formats:** Handles both game and team schedule data structures

### Performance
- **Execution Time:** < 1 second per scrape
- **Docker Image:** 304MB
- **Accuracy:** 100% (API-based, no browser automation)
- **Reliability:** No dependencies on page rendering

### Data Deduplication
- API returns overlapping entries for games
- System prefers game entries over practice entries for same time slot
- Ensures clean schedule without duplicates

## Monitoring

### View Logs
```bash
# Weekly reports
tail -f logs/cron.log

# Change monitoring
tail -f logs/change_monitor.log
```

### View Data
```bash
# Current full schedule
cat data/amherst_stadium_schedule.csv

# JSON output (for signage dashboards)
cat data/amherst_stadium_schedule.json

# 7-day snapshot
cat data/schedule_snapshot_7day.csv

# Detected changes (if any)
cat data/schedule_changes.json
```

### Check Cron Jobs
```bash
crontab -l | grep ccmha
```

## Troubleshooting

### No Email Received?
1. Check logs for errors
2. Verify email in spam folder
3. Test manually with commands above
4. Verify .env credentials

### Missing Games/Practices?
1. Check CSV file: `cat data/amherst_stadium_schedule.csv`
2. Verify on CCMHA website
3. Review logs for API errors

### No Change Alerts?
- Normal! Only sends when changes detected
- Check: `tail logs/change_monitor.log`

## Configuration

All settings in `.env`:

```bash
# How many days ahead for weekly reports
DAYS_AHEAD=14

# How many days to monitor for changes
CHANGE_MONITOR_DAYS=7

# Which venue to filter
VENUE_FILTER=Amherst Stadium

# Email recipients (comma-separated)
RECIPIENT_EMAILS=email1@example.com,email2@example.com
```

## File Structure

```
grayjay-schedule/
├── ccmha_complete_scraper.py       # Main scraper
├── ccmha_email_notifier_improved.py # Weekly email sender
├── ccmha_change_detector.py        # Change detection logic
├── ccmha_change_notifier.py        # Change alert sender
├── ccmha_change_monitor.py         # Change monitoring workflow
├── ccmha_monitor_improved.py       # Weekly report workflow
├── Dockerfile.api                  # Docker image definition
├── requirements.txt                # Python dependencies
├── .env                           # Configuration (not in git)
├── data/                          # Schedule data (not in git)
│   ├── amherst_stadium_schedule.csv
│   ├── amherst_stadium_schedule.json
│   ├── schedule_snapshot_7day.csv
│   └── schedule_changes.json
├── logs/                          # Logs (not in git)
│   ├── cron.log
│   └── change_monitor.log
└── README.md
```

## Development

### Requirements
```bash
pip install requests pandas python-dotenv
```

### Testing
```bash
# Set environment variables
export OUTPUT_DIR=/tmp/test
export DAYS_AHEAD=14
export VENUE_FILTER="Amherst Stadium"

# Run scraper
python3 ccmha_complete_scraper.py
```

## Documentation

- **COMPLETE_SETUP_GUIDE.md** - Detailed setup and troubleshooting
- **README.md** - This file

## License

MIT License

## Support

For detailed setup instructions and troubleshooting, see COMPLETE_SETUP_GUIDE.md

## Credits

Built for Cumberland County Minor Hockey Association (CCMHA) using the GrayJay Leagues platform API.

---

**Status:** ✅ Production Ready
**Last Updated:** November 2, 2025
