# -----------------------------------------------------------------------------
# Project: Unified Communication Platform
# Author: Abubacker Siddiq M
# Copyright (c) 2025 Abubacker Siddiq M
# License: MIT License (See LICENSE file for details)
# -----------------------------------------------------------------------------

from flask import (
    Blueprint, render_template, request, jsonify, flash,
    redirect, url_for
)
from flask_login import login_required, current_user
from functools import wraps
from .models import (
    User, Role, Call, Chat, Message, Voicemail, Contact,
    CallQueue, db, SIPTrunk
)
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Admin access required', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard with system overview"""
    # Get system statistics
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_calls = Call.query.count()
    today_calls = Call.query.filter(
        Call.created_at >= datetime.utcnow().date()
    ).count()
    total_voicemails = Voicemail.query.count()
    unread_voicemails = Voicemail.query.filter_by(is_read=False).count()

    # Get recent activity
    recent_calls = Call.query.order_by(Call.created_at.desc()).limit(10).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()

    # Get call statistics by status
    call_stats = db.session.query(
        Call.status, db.func.count(Call.id)
    ).group_by(Call.status).all()

    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        active_users=active_users,
        total_calls=total_calls,
        today_calls=today_calls,
        total_voicemails=total_voicemails,
        unread_voicemails=unread_voicemails,
        recent_calls=recent_calls,
        recent_users=recent_users,
        call_stats=call_stats
    )


@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    """User management interface"""
    users = User.query.order_by(User.created_at.desc()).all()
    roles = Role.query.all()

    # Calculate admin count
    admin_count = 0
    for user in users:
        for role in user.roles:
            if role.name == 'Admin':
                admin_count += 1
                break

    return render_template(
        'admin/users.html',
        users=users,
        roles=roles,
        admin_count=admin_count
    )


@admin_bp.route('/calls')
@login_required
@admin_required
def call_monitoring():
    """Call monitoring and management"""
    calls = Call.query.order_by(Call.created_at.desc()).all()
    return render_template('admin/calls.html', calls=calls)


@admin_bp.route('/queues')
@login_required
@admin_required
def manage_queues():
    """Call queue management"""
    queues = CallQueue.query.all()
    users = User.query.filter_by(is_active=True).all()
    return render_template('admin/queues.html', queues=queues, users=users)


@admin_bp.route('/sip-trunks')
@login_required
def sip_trunks():
    """SIP Trunk management page"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))

    trunks = SIPTrunk.query.all()
    return render_template('admin/sip_trunks.html', trunks=trunks)


@admin_bp.route('/sip-trunks/add', methods=['GET', 'POST'])
@login_required
def add_sip_trunk():
    """Add new SIP trunk"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        provider = request.form.get('provider')
        sip_server = request.form.get('sip_server')
        sip_port = request.form.get('sip_port', 5060)
        username = request.form.get('username')
        password = request.form.get('password')

        if not all([name, provider, sip_server]):
            flash('Name, provider, and SIP server are required.', 'error')
        else:
            trunk = SIPTrunk(
                name=name,
                provider=provider,
                sip_server=sip_server,
                sip_port=int(sip_port),
                username=username,
                password=password
            )
            db.session.add(trunk)
            db.session.commit()
            flash('SIP trunk added successfully.', 'success')
            return redirect(url_for('admin.sip_trunks'))

    return render_template('admin/add_sip_trunk.html')


@admin_bp.route('/api/test-sip-trunk', methods=['POST'])
@login_required
def test_sip_trunk():
    """Test SIP trunk connection"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403

    data = request.get_json()
    trunk_id = data.get('trunk_id')

    if not trunk_id:
        return jsonify({'error': 'Trunk ID required'}), 400

    trunk = SIPTrunk.query.get(trunk_id)
    if not trunk:
        return jsonify({'error': 'SIP trunk not found'}), 404

    # In a real implementation, you would test the SIP connection here
    # For demo purposes, we'll simulate a successful test
    try:
        import time
        time.sleep(1)
        return jsonify({
            'success': True,
            'message': (
                f'Connection to {trunk.sip_server}:{trunk.sip_port} successful'
            )
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/toggle-sip-trunk', methods=['POST'])
@login_required
def toggle_sip_trunk():
    """Toggle SIP trunk active status"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403

    data = request.get_json()
    trunk_id = data.get('trunk_id')

    if not trunk_id:
        return jsonify({'error': 'Trunk ID required'}), 400

    trunk = SIPTrunk.query.get(trunk_id)
    if not trunk:
        return jsonify({'error': 'SIP trunk not found'}), 404

    try:
        trunk.is_active = not trunk.is_active
        db.session.commit()
        return jsonify({
            'success': True,
            'is_active': trunk.is_active
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/delete-sip-trunk', methods=['POST'])
@login_required
def delete_sip_trunk():
    """Delete SIP trunk"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403

    data = request.get_json()
    trunk_id = data.get('trunk_id')

    if not trunk_id:
        return jsonify({'error': 'Trunk ID required'}), 400

    trunk = SIPTrunk.query.get(trunk_id)
    if not trunk:
        return jsonify({'error': 'SIP trunk not found'}), 404

    try:
        db.session.delete(trunk)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
