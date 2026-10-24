#!/usr/bin/env python
"""FileGuard FIM - File Integrity Monitoring System"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app import create_app

app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    from app.services.scheduler import scheduler
    # In debug mode with reloader, only start scheduler in the runner process
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.config.get('DEBUG'):
        scheduler.init_app(app)
        scheduler.start()
    app.run(host='127.0.0.1', port=5000, debug=True)
