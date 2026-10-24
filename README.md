# FileGuard FIM - File Integrity Monitoring System

![FileGuard FIM](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

A complete, professional, web-based File Integrity Monitoring (FIM) system built from scratch with Python and Flask. Detects unauthorized file changes using SHA-256 cryptographic hashing, maintains trusted baselines, and provides a modern web dashboard for monitoring and reporting.

**⚠️ This is an independent implementation. It does not use or depend on Wazuh or any external FIM products.**

## Features

✅ **Complete File Integrity Monitoring**
- SHA-256 cryptographic hash calculation
- Trusted baseline creation and management
- Detection of added, modified, and deleted files
- Recursive directory scanning
- Configurable file and directory exclusions

✅ **Professional Web Dashboard**
- Modern dark-themed cybersecurity interface
- Real-time monitoring status
- Event filtering and search
- Baseline management with explicit confirmation
- Comprehensive audit logging

✅ **Security Features**
- Role-based access control (Administrator & Read-only)
- Werkzeug password hashing
- CSRF protection via Flask-WTF
- Secure session management
- Timestamped audit trails

✅ **Automated Monitoring**
- Scheduled periodic scans
- Manual scan capability
- Background task processing
- Scan failure detection

✅ **Reports & Exports**
- CSV report generation
- JSON report generation
- Configurable date ranges
- CSV formula injection protection

## Screenshots

### Dashboard Overview
The main dashboard displays monitoring statistics, recent events, and system status.

### File Integrity Events
View all detected changes with timestamps, event types, and hash evidence.

### Baseline Management
Manage trusted baselines with explicit confirmation for replacements.

## Technology Stack

**Backend:**
- Python 3.11+
- Flask 3.0
- SQLAlchemy (SQLite database)
- Flask-Login (Authentication)
- Flask-WTF (CSRF protection)
- APScheduler (Background tasks)

**Frontend:**
- HTML5 & CSS3
- Bootstrap 5 (Dark theme)
- Vanilla JavaScript
- Chart.js (Visualizations)

**Security:**
- SHA-256 via Python hashlib
- Werkzeug password hashing
- Secure session cookies
- Environment variable secrets

## Installation

### Prerequisites

- Python 3.11 or higher
- pip package manager
- Virtual environment (recommended)

### Setup Steps

1. **Clone or download the project:**
```bash
cd fileguard-fim
```

2. **Create a virtual environment:**
```bash
python -m venv venv
```

3. **Activate the virtual environment:**

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

4. **Install dependencies:**
```bash
pip install -r requirements.txt
```

5. **Configure environment variables:**
```bash
cp .env.example .env
```

Edit `.env` and set a strong `SECRET_KEY` for production:
```env
SECRET_KEY=your-secure-random-key-here
```

6. **Initialize the database:**
The database will be created automatically on first run. The application creates a default admin user:

- **Username:** `admin`
- **Password:** `admin123`

**⚠️ IMPORTANT: Change this password immediately after first login!**

## Running the Application

### Development Mode

1. **Activate the virtual environment** (if not already activated)

2. **Run the application:**
```bash
python run.py
```

3. **Open your browser:**
```
http://127.0.0.1:5000
```

4. **Login** with the default credentials (admin/admin123)

### Production Considerations

For production deployment:

1. **Set production environment variables:**
```env
FLASK_ENV=production
SECRET_KEY=your-very-strong-secret-key
SESSION_COOKIE_SECURE=True
```

2. **Use a production WSGI server** (e.g., Gunicorn):
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 run:app
```

3. **Use HTTPS** to protect credentials and session cookies

4. **Run behind a reverse proxy** (e.g., Nginx) for additional security

5. **Regular database backups** to preserve baselines and audit logs

## Usage Guide

### 1. Add a Monitored Directory

1. Navigate to **Monitored Directories**
2. Enter the full path to the directory (e.g., `C:\important\files` or `/home/user/documents`)
3. Click **Add Directory**

### 2. Create a Baseline

1. Go to **Baseline Management**
2. Click **Create Baseline** for your directory
3. Wait for the scan to complete
4. The baseline now contains SHA-256 hashes of all files

### 3. Monitor for Changes

**Automatic Monitoring:**
- Scans run automatically every 60 seconds (configurable in `.env`)
- Changes are detected and logged automatically

**Manual Scan:**
- Go to **Monitored Directories**
- Click the refresh icon next to a directory
- View scan results immediately

### 4. Review Detected Events

1. Navigate to **File Integrity**
2. View all detected changes:
   - **Added** files (green badge)
   - **Modified** files (yellow badge)
   - **Deleted** files (red badge)
3. Search and filter events
4. Review hash evidence for each change

### 5. Configure Exclusions

1. Go to **Exclusions**
2. Add patterns to exclude:
   - **Glob patterns:** `*.log`, `temp*`, `**/*.tmp`
   - **Exact files:** `.gitignore`, `README.md`
   - **Directories:** `node_modules`, `.git`, `__pycache__`
3. Enable/disable exclusions as needed

### 6. Replace a Baseline (After Reviewing Changes)

⚠️ **Important:** Only replace baselines after reviewing and accepting legitimate changes.

1. Go to **Baseline Management**
2. Click **Replace Baseline**
3. Enter a reason for replacement
4. Confirm the action
5. A new trusted baseline is created

### 7. Generate Reports

1. Navigate to **Reports**
2. Select time range (7, 30, 90 days, or 1 year)
3. Choose **CSV** or **JSON** format
4. Download the report

### 8. View Audit Logs

1. Go to **Audit Logs**
2. View complete history of:
   - User logins and logouts
   - Baseline operations
   - Directory changes
   - Configuration changes
3. Search and filter audit entries

## Configuration

### Environment Variables (.env)

```env
# Flask
FLASK_ENV=development
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=sqlite:///instance/fileguard.db

# Security
SESSION_COOKIE_SECURE=False  # Set True in production with HTTPS
WTF_CSRF_ENABLED=True

# Monitoring
SCAN_INTERVAL_SECONDS=60  # How often to scan (seconds)
MAX_FILE_SIZE_MB=100      # Maximum file size to hash

# Demo Mode
DEMO_MODE_ENABLED=False
```

### Changing Scan Interval

Edit `.env`:
```env
SCAN_INTERVAL_SECONDS=300  # Scan every 5 minutes
```

Restart the application for changes to take effect.

### User Roles

**Administrator:**
- Full access to all features
- Can add/remove monitored directories
- Can create and replace baselines
- Can manage exclusions
- Can manage users

**Read-only:**
- View dashboard and events
- View audit logs
- Generate reports
- Cannot make configuration changes

## Testing

### Run All Tests

```bash
pytest
```

### Run Specific Test Suite

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific test file
pytest tests/unit/test_hasher.py
```

### Run with Coverage

```bash
pytest --cov=app --cov-report=html
```

View coverage report in `htmlcov/index.html`.

## Architecture

```
fileguard-fim/
├── app/
│   ├── __init__.py           # Application factory
│   ├── config.py             # Configuration
│   ├── extensions.py         # Flask extensions
│   ├── models/               # Database models
│   │   ├── user.py
│   │   ├── monitored_directory.py
│   │   ├── baseline.py
│   │   ├── integrity_event.py
│   │   ├── audit_log.py
│   │   └── exclusion.py
│   ├── routes/               # Flask blueprints
│   │   ├── auth.py
│   │   ├── dashboard.py
│   │   ├── integrity.py
│   │   ├── directories.py
│   │   ├── baselines.py
│   │   ├── audit.py
│   │   ├── exclusions.py
│   │   ├── reports.py
│   │   └── settings.py
│   ├── services/             # Business logic
│   │   ├── hasher.py         # SHA-256 hashing
│   │   ├── scanner.py        # Directory scanning
│   │   ├── baseline_service.py
│   │   ├── detection_engine.py
│   │   ├── audit_service.py
│   │   ├── report_service.py
│   │   └── scheduler.py      # Automated scans
│   ├── templates/            # HTML templates
│   └── static/               # CSS, JS, images
├── tests/                    # Test suite
├── instance/                 # Database (auto-created)
├── requirements.txt          # Python dependencies
├── run.py                    # Application entry point
└── README.md                 # This file
```

## Security Considerations

### Current Implementation

✅ **Implemented:**
- SHA-256 cryptographic hashing
- Password hashing with Werkzeug
- CSRF protection
- Role-based access control
- Secure session management
- Audit logging
- Input validation
- CSV formula injection protection

⚠️ **Limitations:**
- Baseline stored on same system (not tamper-proof against admin with system access)
- Default password must be changed
- Requires HTTPS in production

### Recommended Enhancements for Production

1. **Remote Baseline Storage:**
   - Store baselines on separate system
   - Implement baseline signing
   - Use append-only log storage

2. **Enhanced Authentication:**
   - Multi-factor authentication
   - Password complexity requirements
   - Account lockout after failed attempts
   - Password expiration policies

3. **Network Security:**
   - Deploy behind reverse proxy
   - Use HTTPS/TLS
   - Implement rate limiting
   - Add IP whitelisting

4. **Monitoring & Alerting:**
   - Email/SMS notifications for critical events
   - Integration with SIEM systems
   - Real-time alerting for baseline changes

## Troubleshooting

### Database Issues

**Problem:** Database locked errors

**Solution:** SQLite has limited concurrent write support. For production, consider PostgreSQL:
```env
DATABASE_URL=postgresql://user:pass@localhost/fileguard
```

### Permission Errors

**Problem:** Cannot scan certain directories

**Solution:** 
- Run application with appropriate permissions
- Add exclusions for inaccessible directories
- Check that directories exist and are readable

### Scheduler Not Running

**Problem:** Automatic scans not working

**Solution:**
- Check logs for scheduler errors
- Verify `SCAN_INTERVAL_SECONDS` is set correctly
- Ensure at least one directory is enabled with a baseline

### High CPU Usage

**Problem:** Scans consuming too much CPU

**Solution:**
- Increase `SCAN_INTERVAL_SECONDS`
- Add exclusions for large directories
- Reduce `MAX_FILE_SIZE_MB` for large file handling

## Development

### Adding New Features

1. Create model in `app/models/` if needed
2. Implement service logic in `app/services/`
3. Create routes in `app/routes/`
4. Add templates in `app/templates/`
5. Write tests in `tests/`

### Running in Debug Mode

```bash
export FLASK_ENV=development  # Linux/Mac
set FLASK_ENV=development     # Windows
python run.py
```

## License

This project is provided as-is for educational and professional use.

## Credits

**Built with:**
- Flask - https://flask.palletsprojects.com/
- Bootstrap - https://getbootstrap.com/
- Chart.js - https://www.chartjs.org/

**Created:** 2026-10-23

**Version:** 1.0.0

---

## Support

For issues, questions, or contributions:
1. Check this README
2. Review the code comments
3. Run the test suite
4. Check application logs

## Changelog

### Version 1.0.0 (2026-10-23)
- Initial release
- Complete FIM functionality
- Web dashboard
- Automated monitoring
- Reports and audit logs
- Comprehensive test suite

---

**⚡ Built from scratch with Python **
