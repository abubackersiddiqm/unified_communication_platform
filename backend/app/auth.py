# -----------------------------------------------------------------------------
# Project: Unified Communication Platform
# Author: Abubacker Siddiq M
# Copyright (c) 2025 Abubacker Siddiq M
# License: MIT License (See LICENSE file for details)
# -----------------------------------------------------------------------------

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    jsonify,
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from .models import User, Role, db
from . import bcrypt
import qrcode
import io
import base64
import secrets
import string
from datetime import datetime
from urllib.parse import urlparse

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        remember = request.form.get("remember", False)

        if not username or not password:
            flash("Please enter both username and password.", "error")
            return render_template("auth/login.html")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash(
                    "Your account has been deactivated.\
                    Please contact administrator.",
                    "error",
                )
                return render_template("auth/login.html")

            # Update user's last seen and status
            user.last_seen = datetime.utcnow()
            user.status = "Available"
            db.session.commit()

            login_user(user, remember=remember)

            # Get the next page from args or default to dashboard
            next_page = request.args.get("next")
            if not next_page or urlparse(next_page).netloc != "":
                next_page = url_for("main.dashboard")

            flash(
                f"Welcome back, {user.full_name or user.username}!", "success"
            )
            return redirect(next_page)
        else:
            flash("Invalid username or password.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # Validation
        if not all(
            [
                username,
                email,
                first_name,
                last_name,
                password,
                confirm_password,
            ]
        ):
            flash("Please fill in all fields.", "error")
            return render_template("auth/register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("auth/register.html")

        if len(password) < 6:  # type: ignore[arg-type]
            flash("Password must be at least 6 characters long.", "error")
            return render_template("auth/register.html")

        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash("Email already registered", "error")
            return render_template("auth/register.html")

        if User.query.filter_by(username=username).first():
            flash("Username already taken", "error")
            return render_template("auth/register.html")

        # Create new user
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        user.set_password(password)

        # Assign default role (User)
        user_role = Role.query.filter_by(name="User").first()
        if user_role:
            user.roles.append(user_role)

        db.session.add(user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Logout user and update last seen"""
    # Update user's last seen timestamp
    current_user.last_seen = datetime.utcnow()
    current_user.status = "Offline"
    db.session.commit()

    # Logout the user
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/profile")
@login_required
def profile():
    return render_template("auth/profile.html")


@auth_bp.route("/qr-code")
@login_required
def generate_qr_code():
    """Generate QR code for mobile app provisioning"""
    # Create a unique token for mobile app authentication
    token = "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(32)
    )

    # Store token in user's session or database (for demo, we'll use a simple approach)
    qr_data = {
        "user_id": current_user.id,
        "email": current_user.email,
        "token": token,
        "platform": "ucp_mobile",
        "generated_at": datetime.now(),
    }

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(str(qr_data))
    qr.make(fit=True)

    # Create QR code image
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64 for display
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")  # type: ignore[call-arg]
    qr_image = base64.b64encode(buffer.getvalue()).decode()

    return render_template(
        "auth/qr_code.html", qr_image=qr_image, qr_data=qr_data
    )


@auth_bp.route("/api/login", methods=["POST"])
def api_login():
    """API endpoint for mobile app login"""
    data = request.get_json()

    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password required"}), 400

    user = User.query.filter_by(email=data["email"]).first()
    if user and user.check_password(data["password"]):
        # In a real app, you'd generate a JWT token here
        return jsonify(
            {
                "success": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "status": user.status,
                },
            }
        )
    else:
        return jsonify({"error": "Invalid credentials"}), 401


@auth_bp.route("/api/update-profile", methods=["POST"])
@login_required
def update_profile():
    """API endpoint for updating profile fields"""
    data = request.get_json()

    if not data or not data.get("field") or not data.get("value"):
        return jsonify({"error": "Field and value required"}), 400

    field = data["field"]
    value = data["value"].strip()

    # Validate field name
    allowed_fields = ["phone_number", "extension"]
    if field not in allowed_fields:
        return jsonify({"error": "Invalid field"}), 400

    try:
        # Update the field
        setattr(current_user, field, value)
        db.session.commit()

        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/api/update-status", methods=["POST"])
@login_required
def update_status():
    """API endpoint for updating user status"""
    data = request.get_json()

    if not data or not data.get("status"):
        return jsonify({"error": "Status required"}), 400

    status = data["status"]

    # Validate status
    allowed_statuses = ["Available", "Away", "Busy", "DND"]
    if status not in allowed_statuses:
        return jsonify({"error": "Invalid status"}), 400

    try:
        current_user.status = status
        db.session.commit()

        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
