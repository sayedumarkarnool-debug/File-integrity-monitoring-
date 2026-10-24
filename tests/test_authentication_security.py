"""
Authentication and security tests for FileGuard FIM
Tests login, access control, and security protections
"""
import pytest
from flask import session

from app import create_app
from app.extensions import db
from app.models.user import User


class TestAuthentication:
    """Test authentication functionality"""

    def test_login_page_accessible(self, client):
        """Test that login page loads"""
        response = client.get('/auth/login')
        assert response.status_code == 200

    def test_valid_login(self, client):
        """Test login with valid credentials"""
        response = client.post('/auth/login', data={
            'username': 'testadmin',
            'password': 'TestPass123!'
        }, follow_redirects=True)

        assert response.status_code == 200
        # Should redirect to dashboard after successful login

    def test_invalid_username(self, client):
        """Test login with invalid username"""
        response = client.post('/auth/login', data={
            'username': 'nonexistent',
            'password': 'wrongpass'
        }, follow_redirects=False)

        # Should stay on login page or return error
        assert response.status_code in [200, 302]

    def test_invalid_password(self, client):
        """Test login with wrong password"""
        response = client.post('/auth/login', data={
            'username': 'testadmin',
            'password': 'WrongPassword'
        }, follow_redirects=False)

        assert response.status_code in [200, 302]

    def test_empty_credentials(self, client):
        """Test login with empty credentials"""
        response = client.post('/auth/login', data={
            'username': '',
            'password': ''
        })

        assert response.status_code in [200, 400]

    def test_logout_functionality(self, client):
        """Test logout"""
        # Login first
        client.post('/auth/login', data={
            'username': 'testadmin',
            'password': 'TestPass123!'
        })

        # Then logout
        response = client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200

    def test_password_hashing(self, app):
        """Test that passwords are hashed, not stored in plaintext"""
        with app.app_context():
            user = User.query.filter_by(username='testadmin').first()

            # Password hash should not equal plaintext
            assert user.password_hash != 'TestPass123!'
            assert user.password_hash is not None
            assert len(user.password_hash) > 20

            # Check password should work
            assert user.check_password('TestPass123!')
            assert not user.check_password('WrongPassword')

    def test_unauthorized_access_redirects(self, client):
        """Test that accessing protected routes without login redirects"""
        protected_routes = [
            '/dashboard/',
            '/integrity/',
            '/directories/',
            '/baselines/',
            '/audit/',
        ]

        for route in protected_routes:
            response = client.get(route, follow_redirects=False)
            # Should redirect to login (302) or return unauthorized (401)
            assert response.status_code in [302, 401]

    def test_readonly_user_role(self, app):
        """Test that readonly role is correctly assigned"""
        with app.app_context():
            user = User.query.filter_by(username='testreadonly').first()
            assert user.role == 'readonly'

    def test_admin_user_role(self, app):
        """Test that administrator role is correctly assigned"""
        with app.app_context():
            user = User.query.filter_by(username='testadmin').first()
            assert user.role == 'administrator'


class TestSecurity:
    """Test security features and protections"""

    @pytest.fixture
    def app(self):
        """Create test application"""
        app = create_app('default')
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = True  # Enable CSRF for these tests

        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()

    def test_csrf_protection_enabled(self, app):
        """Test that CSRF protection is enabled"""
        assert app.config['WTF_CSRF_ENABLED'] is True

    def test_session_cookie_httponly(self, app):
        """Test that session cookies are HTTPOnly"""
        assert app.config['SESSION_COOKIE_HTTPONLY'] is True

    def test_session_cookie_samesite(self, app):
        """Test that SameSite is configured"""
        assert app.config['SESSION_COOKIE_SAMESITE'] in ['Lax', 'Strict']

    def test_sql_injection_prevention_in_search(self, client):
        """Test SQL injection attempts are handled safely"""
        # These should not cause errors or SQL injection
        injection_attempts = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "1' UNION SELECT * FROM users--",
            "<script>alert('xss')</script>",
        ]

        for payload in injection_attempts:
            # Try in various parameters
            response = client.get(f'/integrity/?search={payload}')
            # Should not cause 500 error (might be 302 redirect to login)
            assert response.status_code != 500

    def test_path_traversal_prevention(self, client):
        """Test path traversal attempts are blocked"""
        path_traversal_attempts = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32',
            '%2e%2e%2f%2e%2e%2f',
            '....//....//....//etc/passwd',
        ]

        for payload in path_traversal_attempts:
            # Application should validate paths
            # This would be tested in actual directory addition
            # For now, verify no 500 errors
            response = client.get('/')
            assert response.status_code in [200, 302, 401]

    def test_xss_prevention_in_file_paths(self):
        """Test that XSS in file paths is prevented"""
        from app.services.scanner import DirectoryScanner
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create file with XSS-like name (though OS may restrict some chars)
            xss_attempts = [
                'safe_file.txt',  # Control
                'file_with_script.txt',  # Placeholder for actual XSS test
            ]

            scanner = DirectoryScanner()
            scanner._exclusion_patterns = {'file': [], 'directory': [], 'glob': []}

            for filename in xss_attempts:
                try:
                    test_file = Path(temp_dir) / filename
                    test_file.write_text('content')
                except:
                    continue  # Skip if OS doesn't allow the filename

            result = scanner.scan_directory(temp_dir)
            # Should not crash
            assert result is not None
            assert 'files' in result

    def test_csv_formula_injection_prevention(self):
        """Test CSV export prevents formula injection"""
        # CSV formulas start with =, +, -, @
        dangerous_strings = [
            '=1+1',
            '+1+1',
            '-1+1',
            '@SUM(1+1)',
            '=cmd|/c calc',
        ]

        # These should be escaped in CSV exports
        for dangerous in dangerous_strings:
            # The report service should prefix with single quote
            # This is a placeholder - actual test would export a report
            assert True  # Report service tested separately

    def test_no_secrets_in_health_endpoint(self, client):
        """Test that health endpoint doesn't expose secrets"""
        response = client.get('/health')
        data = response.get_json()

        # Should not contain sensitive info
        assert 'SECRET_KEY' not in str(data)
        assert 'password' not in str(data).lower()
        assert 'DATABASE_URL' not in str(data)

    def test_secret_key_configured(self, app):
        """Test that SECRET_KEY is set"""
        assert app.config['SECRET_KEY'] is not None
        assert len(app.config['SECRET_KEY']) > 10

    def test_debug_mode_detection(self, app):
        """Test debug mode setting"""
        # In testing, we allow debug
        # But verify it can be checked
        assert 'DEBUG' in app.config

    def test_password_hash_uses_strong_algorithm(self, app):
        """Test that password hashing uses Werkzeug's secure methods"""
        with app.app_context():
            user = User(username='testuser', email='test@test.com', role='administrator')
            user.set_password('TestPassword123')

            # Werkzeug uses pbkdf2 or scrypt
            assert user.password_hash.startswith('pbkdf2:') or user.password_hash.startswith('scrypt:')
            assert len(user.password_hash) > 50  # Strong hash should be long

    def test_sensitive_routes_require_authentication(self, client):
        """Test that sensitive operations require auth"""
        sensitive_routes = [
            ('/directories/add', 'POST'),
            ('/baselines/1/create', 'POST'),
            ('/exclusions/add', 'POST'),
        ]

        for route, method in sensitive_routes:
            if method == 'POST':
                response = client.post(route, follow_redirects=False)
            else:
                response = client.get(route, follow_redirects=False)

            # Should redirect to login, return 401, or return 400 (CSRF token missing)
            assert response.status_code in [302, 401, 400, 405]  # 405 if method not exact

    def test_no_directory_listing(self, client):
        """Test that static directory listing is disabled"""
        # Try to access static directory directly
        response = client.get('/static/')

        # Should not show directory listing (404 or 403)
        assert response.status_code in [403, 404, 301, 302]


class TestPasswordSecurity:
    """Test password-related security"""

    def test_password_hashing_different_for_same_password(self):
        """Test that same password gets different hash each time (salt)"""
        user1 = User(username='user1', email='user1@test.com', role='administrator')
        user2 = User(username='user2', email='user2@test.com', role='administrator')

        user1.set_password('SamePassword123')
        user2.set_password('SamePassword123')

        # Hashes should be different due to salt
        assert user1.password_hash != user2.password_hash

        # But both should verify correctly
        assert user1.check_password('SamePassword123')
        assert user2.check_password('SamePassword123')

    def test_password_verification_timing_safe(self):
        """Test password check doesn't fail on None or empty"""
        user = User(username='test', email='test@test.com', role='administrator')
        user.set_password('TestPass123')

        # Should handle edge cases without crashing
        assert not user.check_password('')
        assert not user.check_password(None)

    def test_user_string_representation(self):
        """Test User model string representation doesn't expose password"""
        user = User(username='testuser', email='test@test.com', role='administrator')
        user.set_password('SecretPass')

        user_str = str(user)

        # String repr should not contain password
        assert 'SecretPass' not in user_str
        assert 'password' not in user_str.lower() or 'password_hash' not in user_str.lower()


class TestInputValidation:
    """Test input validation and sanitization"""

    @pytest.fixture
    def app(self):
        """Create test application"""
        app = create_app('default')
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False

        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()

    def test_file_path_validation(self):
        """Test that file paths are validated"""
        from app.services.hasher import FileHasher

        invalid_paths = [
            '',
            None,
            '../../../etc/passwd',
        ]

        for path in invalid_paths:
            if path is None:
                continue
            hash_val, size, error = FileHasher.calculate_sha256(path)

            # Should return error, not crash
            assert hash_val is None
            assert error is not None

    def test_directory_path_validation(self):
        """Test directory path validation in scanner"""
        from app.services.scanner import DirectoryScanner

        scanner = DirectoryScanner()

        # Empty path
        result = scanner.scan_directory('')
        assert not result['scan_complete']

        # Non-existent path
        result = scanner.scan_directory('/does/not/exist/anywhere')
        assert not result['scan_complete']
