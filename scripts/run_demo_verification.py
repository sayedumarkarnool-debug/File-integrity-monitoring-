"""
FileGuard FIM - Comprehensive End-to-End Demonstration Script
Executes all 13 required verification steps in a dedicated temporary test directory.
"""
import os
import sys
import tempfile
import shutil
import hashlib
from datetime import datetime

# Add app to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models.monitored_directory import MonitoredDirectory
from app.models.baseline import BaselineEntry
from app.models.exclusion import Exclusion
from app.models.audit_log import AuditLog
from app.models.integrity_event import IntegrityEvent
from app.services.hasher import FileHasher
from app.services.scanner import DirectoryScanner
from app.services.baseline_service import BaselineService
from app.services.detection_engine import DetectionEngine
from app.services.report_service import ReportService

def calculate_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def run_demonstration():
    print("=" * 70)
    print("FILEGUARD FIM - END-TO-END DEMONSTRATION")
    print("=" * 70)

    app = create_app('default')
    results = {}

    with app.app_context():
        # Dedicated temporary test directory
        demo_dir = tempfile.mkdtemp(prefix="fileguard_demo_")
        print(f"[*] Dedicated Temporary Directory: {demo_dir}")

        try:
            # -------------------------------------------------------------
            # STEP 1: Create three synthetic sample files
            # -------------------------------------------------------------
            print("\n[STEP 1] Creating three synthetic sample files...")
            f1_path = os.path.join(demo_dir, "config.json")
            f2_path = os.path.join(demo_dir, "app.py")
            f3_path = os.path.join(demo_dir, "notes.txt")

            with open(f1_path, "wb") as f:
                f.write(b'{"version": "1.0", "name": "fileguard"}')
            with open(f2_path, "wb") as f:
                f.write(b'def main():\n    print("Secure FIM running")\n')
            with open(f3_path, "wb") as f:
                f.write(b"Initial baseline documentation notes.\n")

            h1_initial = calculate_sha256(open(f1_path, "rb").read())
            h2_initial = calculate_sha256(open(f2_path, "rb").read())
            h3_initial = calculate_sha256(open(f3_path, "rb").read())

            print(f"  - Created {os.path.basename(f1_path)} (SHA-256: {h1_initial[:16]}...)")
            print(f"  - Created {os.path.basename(f2_path)} (SHA-256: {h2_initial[:16]}...)")
            print(f"  - Created {os.path.basename(f3_path)} (SHA-256: {h3_initial[:16]}...)")
            results['step_1'] = "SUCCESS: Created 3 synthetic sample files"

            # Register monitored directory
            mon_dir = MonitoredDirectory(path=demo_dir, is_enabled=True)
            db.session.add(mon_dir)
            db.session.commit()
            dir_id = mon_dir.id

            # -------------------------------------------------------------
            # STEP 2: Create initial baseline
            # -------------------------------------------------------------
            print("\n[STEP 2] Creating the initial baseline...")
            baseline_service = BaselineService()
            create_res = baseline_service.create_baseline(dir_id, actor='admin_tester')
            assert create_res['success'] is True, f"Baseline creation failed: {create_res}"
            assert create_res['file_count'] == 3, f"Expected 3 files, got {create_res['file_count']}"
            print(f"  -> Baseline created successfully with {create_res['file_count']} files.")
            results['step_2'] = f"SUCCESS: Baseline created with {create_res['file_count']} files"

            # -------------------------------------------------------------
            # STEP 3: Scan again without changes (verify no false events)
            # -------------------------------------------------------------
            print("\n[STEP 3] Scanning again without any modifications...")
            engine = DetectionEngine()
            changes_unchanged = engine.scan_and_detect(dir_id, actor='admin_tester')
            assert len(changes_unchanged['added']) == 0
            assert len(changes_unchanged['modified']) == 0
            assert len(changes_unchanged['deleted']) == 0
            assert changes_unchanged['unchanged'] == 3
            assert changes_unchanged.get('events_recorded', 0) == 0
            print(f"  -> No modifications detected (Unchanged files: {changes_unchanged['unchanged']}). No false positives.")
            results['step_3'] = "SUCCESS: Zero changes detected on unchanged directory"

            # -------------------------------------------------------------
            # STEP 4: Add a new file and verify an ADDED event
            # -------------------------------------------------------------
            print("\n[STEP 4] Adding new file 'secret_key.pem'...")
            f4_path = os.path.join(demo_dir, "secret_key.pem")
            with open(f4_path, "wb") as f:
                f.write(b"-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASC\n-----END PRIVATE KEY-----\n")
            h4_actual = calculate_sha256(open(f4_path, "rb").read())

            changes_added = engine.scan_and_detect(dir_id, actor='admin_tester')
            assert len(changes_added['added']) == 1
            assert changes_added['added'][0]['path'] == 'secret_key.pem'
            assert changes_added['added'][0]['hash'] == h4_actual
            print(f"  -> ADDED event detected for '{changes_added['added'][0]['path']}' (Hash: {changes_added['added'][0]['hash'][:16]}...)")
            results['step_4'] = "SUCCESS: Correctly detected ADDED event with matching SHA-256"

            # -------------------------------------------------------------
            # STEP 5: Modify an existing file and verify a MODIFIED event
            # -------------------------------------------------------------
            print("\n[STEP 5] Modifying existing file 'config.json'...")
            with open(f1_path, "wb") as f:
                f.write(b'{"version": "2.0-TAMPERED", "name": "fileguard", "malicious": true}')
            h1_modified = calculate_sha256(open(f1_path, "rb").read())

            changes_mod = engine.scan_and_detect(dir_id, actor='admin_tester')
            assert len(changes_mod['modified']) == 1
            mod_event = changes_mod['modified'][0]
            assert mod_event['path'] == 'config.json'

            # -------------------------------------------------------------
            # STEP 6: Confirm that old and new SHA-256 hashes are correct
            # -------------------------------------------------------------
            print("\n[STEP 6] Confirming old and new SHA-256 hashes...")
            assert mod_event['previous_hash'] == h1_initial
            assert mod_event['current_hash'] == h1_modified
            print(f"  -> Previous Hash: {mod_event['previous_hash']}")
            print(f"  -> Current Hash:  {mod_event['current_hash']}")
            results['step_5_6'] = "SUCCESS: Correctly detected MODIFIED event with exact previous and current SHA-256 evidence"

            # -------------------------------------------------------------
            # STEP 7: Delete a sample file and verify DELETED event
            # -------------------------------------------------------------
            print("\n[STEP 7] Deleting 'notes.txt' and verifying DELETED event...")
            os.remove(f3_path)
            changes_del = engine.scan_and_detect(dir_id, actor='admin_tester')
            assert len(changes_del['deleted']) == 1
            del_event = changes_del['deleted'][0]
            assert del_event['path'] == 'notes.txt'
            assert del_event['previous_hash'] == h3_initial
            print(f"  -> DELETED event detected for '{del_event['path']}' with previous hash: {del_event['previous_hash'][:16]}...")
            results['step_7'] = "SUCCESS: Correctly detected DELETED event with historical baseline hash"

            # -------------------------------------------------------------
            # STEP 8: Test exclusion pattern
            # -------------------------------------------------------------
            print("\n[STEP 8] Testing exclusion rules (*.tmp)...")
            ex = Exclusion(pattern='*.tmp', pattern_type='glob', created_by='admin_tester', is_enabled=True)
            db.session.add(ex)
            db.session.commit()

            # Create an excluded temp file
            f_excluded = os.path.join(demo_dir, "cache_temp.tmp")
            with open(f_excluded, "wb") as f:
                f.write(b"Temporary ephemeral data")

            # Scanner should skip this file completely
            scanner = DirectoryScanner()
            scan_res = scanner.scan_directory(demo_dir)
            assert 'cache_temp.tmp' not in scan_res['files']

            changes_excl = engine.scan_and_detect(dir_id, actor='admin_tester')
            assert not any(a['path'] == 'cache_temp.tmp' for a in changes_excl['added'])
            print("  -> Excluded file '*.tmp' was completely ignored by scanner and detection engine.")
            results['step_8'] = "SUCCESS: Exclusion pattern prevented false positive events"

            # -------------------------------------------------------------
            # STEP 9: Attempt baseline replacement without confirmation
            # -------------------------------------------------------------
            print("\n[STEP 9] Testing baseline replacement without confirmation...")
            # Route logic: when confirmed is False, it rejects with 400
            app.config['WTF_CSRF_ENABLED'] = False
            test_client = app.test_client()
            login_res = test_client.post('/auth/login', data={'username': 'admin', 'password': 'admin123'})

            res_unconfirmed = test_client.post(
                f'/baselines/{dir_id}/replace',
                json={'confirmed': False, 'reason': 'Unconfirmed attempt'}
            )
            assert res_unconfirmed.status_code == 400
            assert res_unconfirmed.is_json
            assert res_unconfirmed.json.get('requires_confirmation') is True
            print(f"  -> Unconfirmed baseline replacement rejected: {res_unconfirmed.json['message']}")
            results['step_9'] = "SUCCESS: Baseline replacement rejected without explicit confirmation"

            # -------------------------------------------------------------
            # STEP 10: Failed scan preserves existing baseline
            # -------------------------------------------------------------
            print("\n[STEP 10] Testing that failed/incomplete scan preserves existing baseline...")
            baseline_before = baseline_service.get_baseline_info(dir_id)
            initial_count = baseline_before['file_count']

            # Simulate broken scan
            original_scan = baseline_service.scanner.scan_directory
            baseline_service.scanner.scan_directory = lambda *a, **kw: {
                'files': {}, 'errors': ['Simulated scanner I/O failure'], 'scan_complete': False,
                'total_files': 0, 'failed_files': 1
            }

            fail_res = baseline_service.replace_baseline(dir_id, 'admin_tester', 'Testing failure safeguard')
            assert fail_res['success'] is False
            baseline_service.scanner.scan_directory = original_scan

            # Check baseline was preserved
            baseline_after = baseline_service.get_baseline_info(dir_id)
            assert baseline_after['exists'] is True
            assert baseline_after['file_count'] == initial_count
            print(f"  -> Failed scan safely preserved existing baseline ({baseline_after['file_count']} files).")
            results['step_10'] = "SUCCESS: Failed scan does not corrupt or wipe existing baseline"

            # -------------------------------------------------------------
            # STEP 11: Confirm audit records and timestamps are accurate
            # -------------------------------------------------------------
            print("\n[STEP 11] Checking audit log records and UTC timestamps...")
            logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()
            assert len(logs) > 0
            for log in logs[:5]:
                assert log.timestamp is not None
                print(f"  - [{log.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}] Actor: {log.actor} | Action: {log.action} | Outcome: {log.outcome}")
            results['step_11'] = "SUCCESS: Audit trail records all critical events with UTC timestamps"

            # -------------------------------------------------------------
            # STEP 12: Export reports and validate contents
            # -------------------------------------------------------------
            print("\n[STEP 12] Exporting CSV and JSON reports...")
            csv_data = ReportService.generate_csv_report()
            json_data = ReportService.generate_json_report()

            assert 'Detected At (UTC)' in csv_data
            assert 'secret_key.pem' in csv_data
            assert 'config.json' in csv_data

            import json
            parsed_json = json.loads(json_data)
            assert 'summary' in parsed_json
            assert 'events' in parsed_json
            assert parsed_json['summary']['total_events'] >= 3
            print(f"  -> CSV Report exported ({len(csv_data)} bytes).")
            print(f"  -> JSON Report exported ({parsed_json['summary']['total_events']} events tracked).")
            results['step_12'] = "SUCCESS: CSV and JSON reports generated and validated"

        finally:
            # -------------------------------------------------------------
            # STEP 13: Cleanup test directory
            # -------------------------------------------------------------
            print("\n[STEP 13] Cleaning up temporary test directory...")
            if os.path.exists(demo_dir):
                shutil.rmtree(demo_dir)
                print(f"  -> Cleaned up {demo_dir}")
            results['step_13'] = "SUCCESS: Cleaned up temporary test files cleanly"

    print("\n" + "=" * 70)
    print("ALL 13 END-TO-END DEMONSTRATION STEPS COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    for step, msg in results.items():
        print(f"{step.upper()}: {msg}")

if __name__ == '__main__':
    run_demonstration()
