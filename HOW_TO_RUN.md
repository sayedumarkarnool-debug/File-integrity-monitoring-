# FileGuard FIM - How to Run

## Quick Start Guide

### 1. Activate Virtual Environment

**Windows:**
```bash
cd C:\Users\Sayed Umar Karnool\OneDrive\Desktop\FIM\fileguard-fim
venv\Scripts\activate
```

**Linux/Mac:**
```bash
cd /path/to/fileguard-fim
source venv/bin/activate
```

### 2. Start the Application

```bash
python run.py
```

You should see output like:
```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

### 3. Access the Web Interface

Open your browser and go to:
```
http://127.0.0.1:5000
```

### 4. Login

**Default Credentials:**
- **Username:** `admin`
- **Password:** `admin123`

⚠️ **IMPORTANT:** Change this password immediately after first login!

---

## Using the Application

### Step 1: Add a Directory to Monitor

1. Click **"Monitored Directories"** in the navigation
2. Enter a full path to monitor (e.g., `C:\test_files` or `/home/user/documents`)
3. Click **"Add Directory"**

### Step 2: Create a Baseline

1. Go to **"Baseline Management"**
2. Find your directory in the list
3. Click **"Create Baseline"**
4. Wait for the scan to complete

This creates a trusted snapshot of all files with their SHA-256 hashes.

### Step 3: Monitor for Changes

**Automatic Monitoring:**
- The system automatically scans every 60 seconds (configurable)
- Changes are detected and logged automatically

**Manual Scan:**
- Go to **"Monitored Directories"**
- Click the refresh icon next to your directory

### Step 4: View Detected Changes

1. Navigate to **"File Integrity"**
2. You'll see all detected changes:
   - **ADDED** files (green badge) - new files not in baseline
   - **MODIFIED** files (yellow badge) - files with changed content
   - **DELETED** files (red badge) - files removed since baseline
3. Click on any event to see hash details

### Step 5: Export Reports

1. Go to **"Reports"**
2. Select time range (7, 30, 90 days, or 1 year)
3. Choose format (CSV or JSON)
4. Click **"Generate Report"**

---

## Testing the Application

### Run All Tests

```bash
pytest
```

### Run Specific Test Suites

```bash
# Authentication and security tests
pytest tests/test_authentication_security.py

# End-to-end workflow tests
pytest tests/test_comprehensive_workflow.py

# Edge cases
pytest tests/test_edge_cases.py

# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/
```

### Run Tests with Coverage

```bash
pytest --cov=app --cov-report=html
```

View coverage report: `htmlcov/index.html`

---

## Manual Testing Example

Here's a quick way to test FIM functionality manually:

### 1. Create a Test Directory

```bash
mkdir C:\fim_test
cd C:\fim_test
echo "Hello World" > file1.txt
echo "Test data" > file2.txt
```

### 2. Add to FileGuard

- Open http://127.0.0.1:5000
- Login with admin/admin123
- Go to "Monitored Directories"
- Add: `C:\fim_test`
- Create a baseline for this directory

### 3. Make Changes

```bash
cd C:\fim_test

# Modify a file
echo "Hello World - Modified!" > file1.txt

# Add a new file
echo "New file" > file3.txt

# Delete a file
del file2.txt
```

### 4. Check Detection

- Go to "File Integrity" in the web interface
- You should see:
  - 1 MODIFIED event for file1.txt
  - 1 ADDED event for file3.txt
  - 1 DELETED event for file2.txt
- Click on events to see previous and current SHA-256 hashes

---

## Stopping the Application

Press `CTRL+C` in the terminal where the application is running.

---

## Configuration

Edit the `.env` file to customize:

```env
# How often to scan (in seconds)
SCAN_INTERVAL_SECONDS=60

# Maximum file size to hash (in MB)
MAX_FILE_SIZE_MB=100

# Flask environment
FLASK_ENV=development

# Secret key (change in production!)
SECRET_KEY=your-secure-random-key
```

After changing settings, restart the application.

---

## Troubleshooting

### Port Already in Use

If port 5000 is occupied, edit `run.py` and change:
```python
app.run(host='127.0.0.1', port=5001, debug=True)
```

### Database Locked Errors

SQLite has limited concurrent write support. This is normal for development.
For production, use PostgreSQL:
```env
DATABASE_URL=postgresql://user:pass@localhost/fileguard
```

### Permission Denied When Scanning

Run the application with appropriate permissions to read the directories you want to monitor.

### Automatic Scans Not Working

1. Check the scheduler is running (you should see log messages)
2. Verify at least one directory is enabled
3. Ensure a baseline exists for the directory

---

## Test Results

The application has been tested and verified:

- ✅ **89 tests passed** (1 skipped)
- ✅ Authentication and authorization working
- ✅ SHA-256 hashing functional
- ✅ File addition detection working
- ✅ File modification detection working
- ✅ File deletion detection working
- ✅ Exclusion rules working
- ✅ Baseline management functional
- ✅ CSV/JSON report generation working
- ✅ Audit logging operational
- ✅ Security protections in place

---

## Application Architecture

```
fileguard-fim/
├── app/
│   ├── models/         # Database models
│   ├── routes/         # Web routes (blueprints)
│   ├── services/       # Business logic
│   │   ├── hasher.py           # SHA-256 hashing
│   │   ├── scanner.py          # Directory scanning
│   │   ├── baseline_service.py # Baseline management
│   │   ├── detection_engine.py # Change detection
│   │   └── scheduler.py        # Automated scans
│   ├── templates/      # HTML templates
│   └── static/         # CSS, JS, images
├── tests/              # Test suite
├── instance/           # Database (auto-created)
│   └── fileguard.db
├── run.py             # Application entry point
└── .env               # Configuration
```

---

## Features Implemented

✅ **Core FIM Functionality**
- SHA-256 cryptographic hashing
- Baseline creation and management
- Detection of added, modified, and deleted files
- Recursive directory scanning
- File and directory exclusions

✅ **Web Dashboard**
- Modern dark-themed interface
- Real-time monitoring status
- Event filtering and search
- Baseline management with confirmation
- Comprehensive audit logging

✅ **Security**
- Role-based access control
- Werkzeug password hashing
- CSRF protection
- Secure session management
- Timestamped audit trails
- Input validation
- CSV formula injection protection

✅ **Automation**
- Scheduled periodic scans (every 60 seconds)
- Manual scan capability
- Background task processing
- Scan failure detection

✅ **Reports & Exports**
- CSV report generation
- JSON report generation
- Configurable date ranges

---

## Production Deployment

For production use:

1. **Set environment to production:**
```env
FLASK_ENV=production
SECRET_KEY=very-strong-random-key-here
SESSION_COOKIE_SECURE=True
```

2. **Use a production WSGI server:**
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 run:app
```

3. **Use HTTPS** (required for secure cookies)

4. **Use a reverse proxy** (Nginx or Apache)

5. **Consider PostgreSQL** instead of SQLite

6. **Regular backups** of the database

---

## Support

For issues or questions:
1. Check this guide
2. Review the README.md
3. Check application logs
4. Run the test suite to verify functionality

---

**Application Version:** 1.0.0  
**Python Version Required:** 3.11+  
**Status:** ✅ Fully functional and tested
