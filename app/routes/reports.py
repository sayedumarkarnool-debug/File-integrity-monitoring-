from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for
from flask_login import login_required
from datetime import datetime, timedelta
from io import BytesIO

from app.services.report_service import ReportService

bp = Blueprint('reports', __name__, url_prefix='/reports')
report_service = ReportService()

@bp.route('/')
@login_required
def index():
    """Reports page"""
    return render_template('reports.html')

@bp.route('/generate/csv', methods=['POST'])
@login_required
def generate_csv():
    """Generate and download CSV report"""
    directory_id = request.form.get('directory_id', type=int)
    days = request.form.get('days', 30, type=int)

    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Generate report
    csv_content = report_service.generate_csv_report(
        directory_id=directory_id,
        start_date=start_date,
        end_date=end_date
    )

    # Create file-like object
    output = BytesIO()
    output.write(csv_content.encode('utf-8'))
    output.seek(0)

    filename = f'fileguard_report_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'

    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

@bp.route('/generate/json', methods=['POST'])
@login_required
def generate_json():
    """Generate and download JSON report"""
    directory_id = request.form.get('directory_id', type=int)
    days = request.form.get('days', 30, type=int)

    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Generate report
    json_content = report_service.generate_json_report(
        directory_id=directory_id,
        start_date=start_date,
        end_date=end_date
    )

    # Create file-like object
    output = BytesIO()
    output.write(json_content.encode('utf-8'))
    output.seek(0)

    filename = f'fileguard_report_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json'

    return send_file(
        output,
        mimetype='application/json',
        as_attachment=True,
        download_name=filename
    )
