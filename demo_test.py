#!/usr/bin/env python
"""
End-to-End demonstration of FileGuard FIM functionality
"""
import os
import json
import shutil
from app import create_app
from app.extensions import db
from app.models.monitored_directory import MonitoredDirectory
from app.services.baseline_service import BaselineService
from app.services.detection_engine import DetectionEngine
from app.models.integrity_event import IntegrityEvent
from app.models.audit_log import AuditLog

def cleanup_test_dir(test_dir):
    """Clean up test directory"""
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

def main():
    app = create_app()

    with app.app_context():
        test_dir = os.path.abspath('fim_demo_test')

        print('=' * 60)
        print('FileGuard FIM - End-to-End Demonstration')
        print('=' * 60)
        print(f'Test Directory: {test_dir}')
        print()

        # Clean up and create fresh test directory
        cleanup_test_dir(test_dir)
        os.makedirs(test_dir, exist_ok=True)

        # Step 1: Create sample files
        print('Step 1: Creating sample files...')
        file1 = os.path.join(test_dir, 'document1.txt')
        file2 = os.path.join(test_dir, 'config.ini')
        file3 = os.path.join(test_dir, 'data.json')

        with open(file1, 'w') as f:
            f.write('This is the original content of document 1.')
        with open(file2, 'w') as f:
            f.write('[settings]\nversion=1.0\ndebug=false')
        with open(file3, 'w') as f:
            json.dump({'key': 'value', 'count': 42}, f)

        print(f'  - Created: document1.txt')
        print(f'  - Created: config.ini')
        print(f'  - Created: data.json')
        print()

        # Step 2: Register directory
        print('Step 2: Registering monitored directory...')
        monitored_dir = MonitoredDirectory(path=test_dir, is_enabled=True)
        db.session.add(monitored_dir)
        db.session.commit()
        print(f'  - Directory ID: {monitored_dir.id}')
        print(f'  - Path: {monitored_dir.path}')
        print()

        # Step 3: Create initial baseline
        print('Step 3: Creating initial baseline...')
        baseline_service = BaselineService()
        result = baseline_service.create_baseline(monitored_dir.id)

        if result['success']:
            print(f'  [OK] Baseline created successfully')
            print(f'  - Files in baseline: {result["file_count"]}')
        else:
            print(f'  [ERROR] Failed: {result["message"]}')
            return
        print()

        # Step 4: Scan without changes
        print('Step 4: Scanning without changes (should detect nothing)...')
        detection_engine = DetectionEngine()
        changes = detection_engine.detect_changes(monitored_dir.id)

        total_changes = len(changes['added']) + len(changes['modified']) + len(changes['deleted'])
        if total_changes == 0:
            print(f'  [OK] No changes detected (correct)')
            print(f'  - Unchanged files: {changes["unchanged"]}')
        else:
            print(f'  [ERROR] False positive: {total_changes} changes detected')
            print(f'  - Added: {len(changes["added"])}, Modified: {len(changes["modified"])}, Deleted: {len(changes["deleted"])}')
        print()

        # Step 5: Add a new file
        print('Step 5: Adding a new file...')
        file4 = os.path.join(test_dir, 'newfile.txt')
        with open(file4, 'w') as f:
            f.write('This is a new file added after baseline.')
        print(f'  - Added: newfile.txt')

        changes = detection_engine.detect_changes(monitored_dir.id)
        if len(changes['added']) == 1:
            print(f'  [OK] ADDED event detected correctly')
            print(f'  - File: {os.path.basename(changes["added"][0]["path"])}')
            print(f'  - Current hash: {changes["added"][0]["hash"][:16]}...')
        else:
            print(f'  [ERROR] Expected 1 ADDED file, got {len(changes["added"])}')
        print()

        # Step 6: Modify an existing file
        print('Step 6: Modifying an existing file...')
        with open(file1, 'w') as f:
            f.write('This is the MODIFIED content of document 1.')
        print(f'  - Modified: document1.txt')

        changes = detection_engine.detect_changes(monitored_dir.id)
        if len(changes['modified']) == 1:
            print(f'  [OK] MODIFIED event detected correctly')
            print(f'  - File: {os.path.basename(changes["modified"][0]["path"])}')
            print(f'  - Previous hash: {changes["modified"][0]["previous_hash"][:16]}...')
            print(f'  - Current hash: {changes["modified"][0]["current_hash"][:16]}...')

            if changes['modified'][0]['previous_hash'] != changes['modified'][0]['current_hash']:
                print(f'  [OK] Hashes are different (correct)')
            else:
                print(f'  [ERROR] Hashes are identical (should be different)')
        else:
            print(f'  [ERROR] Expected 1 MODIFIED file, got {len(changes["modified"])}')
        print()

        # Step 7: Delete a file
        print('Step 7: Deleting a file...')
        os.remove(file3)
        print(f'  - Deleted: data.json')

        changes = detection_engine.detect_changes(monitored_dir.id)
        if len(changes['deleted']) == 1:
            print(f'  [OK] DELETED event detected correctly')
            print(f'  - File: {os.path.basename(changes["deleted"][0]["path"])}')
            print(f'  - Previous hash: {changes["deleted"][0]["previous_hash"][:16]}...')
        else:
            print(f'  [ERROR] Expected 1 DELETED file, got {len(changes["deleted"])}')
        print()

        # Step 8: Record events to database
        print('Step 8: Recording events to database...')
        events_recorded = detection_engine.record_events(monitored_dir.id, changes, actor='demo')
        print(f'  - Events recorded: {events_recorded}')
        print()

        # Step 9: Check audit trail
        print('Step 9: Checking audit trail...')
        audit_count = AuditLog.query.filter_by(action_type='baseline_created').count()
        print(f'  - Baseline creation audit entries: {audit_count}')
        print()

        # Step 10: Summary
        print('=' * 60)
        print('Demonstration Summary')
        print('=' * 60)
        total_events = IntegrityEvent.query.count()
        print(f'Total integrity events in database: {total_events}')
        files_in_dir = len([f for f in os.listdir(test_dir) if os.path.isfile(os.path.join(test_dir, f))])
        print(f'Files currently in test directory: {files_in_dir}')
        print()
        print('[SUCCESS] End-to-End Demonstration Complete!')
        print()
        print('=' * 60)
        print('How to Access the Application')
        print('=' * 60)
        print('1. Web application URL: http://127.0.0.1:5000')
        print('2. Login credentials:')
        print('   Username: admin')
        print('   Password: admin123')
        print('3. IMPORTANT: Change the default password after first login!')
        print()
        print('Test directory location:')
        print(f'   {test_dir}')
        print()

if __name__ == '__main__':
    main()
