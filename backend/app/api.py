# -----------------------------------------------------------------------------
# Project: Unified Communication Platform
# Author: Abubacker Siddiq M
# Copyright (c) 2025 Abubacker Siddiq M
# License: MIT License (See LICENSE file for details)
# -----------------------------------------------------------------------------

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from .models import (
    User,
    Role,
    Call,
    Chat,
    Message,
    Voicemail,
    Contact,
    db,
    InternationalRate,
    SIPTrunk,
)
from . import socketio
from datetime import datetime
import uuid
import csv
from io import StringIO
from werkzeug.security import generate_password_hash

api_bp = Blueprint("api", __name__)


# User Management API endpoints
@api_bp.route("/user/<int:user_id>", methods=["GET"])
@login_required
def get_user(user_id):
    """Get user information"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Get the first role (assuming single role per user for now)
    user_role = user.roles[0] if user.roles else None

    return jsonify(
        {
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "phone_number": user.phone_number,
                "status": user.status,
                "is_active": user.is_active,
                "roles": [
                    {"id": role.id, "name": role.name} for role in user.roles
                ],
                "role": (
                    {"id": user_role.id, "name": user_role.name}
                    if user_role
                    else None
                ),
                "created_at": (
                    user.created_at.isoformat() if user.created_at else None
                ),
                "last_seen": (
                    user.last_seen.isoformat() if user.last_seen else None
                ),
            },
        }
    )


@api_bp.route("/user/<int:user_id>/details", methods=["GET"])
@login_required
def get_user_details(user_id):
    """Get detailed user information with statistics"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Get user statistics
    total_calls = Call.query.filter(
        (Call.caller_id == user_id) | (Call.callee_id == user_id)
    ).count()

    total_messages = Message.query.filter_by(sender_id=user_id).count()

    voicemails = Voicemail.query.filter_by(recipient_id=user_id).count()

    contacts = Contact.query.filter_by(owner_id=user_id).count()

    # Get the first role (assuming single role per user for now)
    user_role = user.roles[0] if user.roles else None

    return jsonify(
        {
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "phone_number": user.phone_number,
                "status": user.status,
                "is_active": user.is_active,
                "roles": [
                    {"id": role.id, "name": role.name} for role in user.roles
                ],
                "role": (
                    {"id": user_role.id, "name": user_role.name}
                    if user_role
                    else None
                ),
                "created_at": (
                    user.created_at.isoformat() if user.created_at else None
                ),
                "last_seen": (
                    user.last_seen.isoformat() if user.last_seen else None
                ),
            },
            "stats": {
                "total_calls": total_calls,
                "total_messages": total_messages,
                "voicemails": voicemails,
                "contacts": contacts,
            },
        }
    )


@api_bp.route("/add-user", methods=["POST"])
@login_required
def add_user():
    """Add a new user"""
    data = request.get_json()

    # Validate required fields
    required_fields = ["username", "email", "full_name", "password", "role"]
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    # Check if username already exists
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username already exists"}), 400

    # Check if email already exists
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already exists"}), 400

    # Get role
    role = Role.query.filter_by(name=data["role"]).first()
    if not role:
        return jsonify({"error": "Invalid role"}), 400

    # Create new user
    user = User(
        username=data["username"],
        email=data["email"],
        first_name=data["full_name"].split()[0] if data["full_name"] else "",
        last_name=(
            " ".join(data["full_name"].split()[1:])
            if data["full_name"] and len(data["full_name"].split()) > 1
            else ""
        ),
        phone_number=data.get("phone"),
        status="Available",
        is_active=True,
    )
    user.set_password(data["password"])

    # Add role to user
    user.roles.append(role)

    try:
        db.session.add(user)
        db.session.commit()
        return jsonify({"success": True, "user_id": user.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/update-user", methods=["POST"])
@login_required
def update_user():
    """Update user information"""
    data = request.get_json()

    if not data.get("id"):
        return jsonify({"error": "User ID is required"}), 400

    user = User.query.get(data["id"])
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Update fields
    if data.get("username") and data["username"] != user.username:
        if User.query.filter_by(username=data["username"]).first():
            return jsonify({"error": "Username already exists"}), 400
        user.username = data["username"]

    if data.get("email") and data["email"] != user.email:
        if User.query.filter_by(email=data["email"]).first():
            return jsonify({"error": "Email already exists"}), 400
        user.email = data["email"]

    if data.get("full_name"):
        user.first_name = (
            data["full_name"].split()[0] if data["full_name"] else ""
        )
        user.last_name = (
            " ".join(data["full_name"].split()[1:])
            if data["full_name"] and len(data["full_name"].split()) > 1
            else ""
        )

    if data.get("phone"):
        user.phone_number = data["phone"]

    if data.get("status"):
        user.status = data["status"]

    if data.get("role"):
        role = Role.query.filter_by(name=data["role"]).first()
        if role:
            # Clear existing roles and add the new one
            user.roles.clear()
            user.roles.append(role)

    try:
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/toggle-user-status", methods=["POST"])
@login_required
def toggle_user_status():
    """Toggle user active status"""
    data = request.get_json()
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.is_active = not user.is_active

    try:
        db.session.commit()
        return jsonify({"success": True, "is_active": user.is_active})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/delete-user", methods=["POST"])
@login_required
def delete_user():
    """Delete a user"""
    data = request.get_json()
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.id == current_user.id:
        return jsonify({"error": "Cannot delete yourself"}), 400

    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/export-users", methods=["GET"])
@login_required
def export_users():
    """Export users to CSV"""
    users = User.query.all()

    output = StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(
        [
            "ID",
            "Username",
            "Email",
            "Full Name",
            "Phone",
            "Role",
            "Status",
            "Active",
            "Created",
        ]
    )

    # Write data
    for user in users:
        user_role = user.roles[0] if user.roles else None
        writer.writerow(
            [
                user.id,
                user.username,
                user.email,
                user.full_name or "",
                user.phone_number or "",
                user_role.name if user_role else "",
                user.status,
                "Yes" if user.is_active else "No",
                (
                    user.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    if user.created_at
                    else ""
                ),
            ]
        )

    output.seek(0)

    from flask import make_response

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = (
        "attachment; filename=users_export.csv"
    )

    return response


# WebRTC signaling endpoints
@api_bp.route("/webrtc/offer", methods=["POST"])
@login_required
def webrtc_offer():
    """Handle WebRTC offer from caller"""
    data = request.get_json()
    callee_id = data.get("callee_id")
    offer = data.get("offer")
    call_type = data.get("call_type", "voice")

    if not callee_id or not offer:
        return jsonify({"error": "Missing required parameters"}), 400

    # Create call record
    call = Call(
        call_id=str(uuid.uuid4()),
        caller_id=current_user.id,
        callee_id=callee_id,
        call_type=call_type,
        status="initiated",
    )

    db.session.add(call)
    db.session.commit()

    # Forward offer to callee
    socketio.emit(
        "webrtc_offer",
        {
            "call_id": call.call_id,
            "offer": offer,
            "caller": {
                "id": current_user.id,
                "name": current_user.full_name,
                "username": current_user.username,
            },
            "call_type": call_type,
        },
        room=f"user_{callee_id}",
    )  # type: ignore[call-arg]

    return jsonify({"success": True, "call_id": call.call_id})


@api_bp.route("/webrtc/answer", methods=["POST"])
@login_required
def webrtc_answer():
    """Handle WebRTC answer from callee"""
    data = request.get_json()
    call_id = data.get("call_id")
    answer = data.get("answer")

    if not call_id or not answer:
        return jsonify({"error": "Missing required parameters"}), 400

    call = Call.query.filter_by(call_id=call_id).first()
    if not call:
        return jsonify({"error": "Call not found"}), 404

    # Forward answer to caller
    socketio.emit(
        "webrtc_answer",
        {"call_id": call_id, "answer": answer},
        room=f"user_{call.caller_id}",
    )  # type: ignore[call-arg]

    return jsonify({"success": True})


@api_bp.route("/webrtc/ice-candidate", methods=["POST"])
@login_required
def webrtc_ice_candidate():
    """Handle ICE candidate exchange"""
    data = request.get_json()
    call_id = data.get("call_id")
    candidate = data.get("candidate")
    target_user_id = data.get("target_user_id")

    if not call_id or not candidate or not target_user_id:
        return jsonify({"error": "Missing required parameters"}), 400

    # Forward ICE candidate to target user
    socketio.emit(
        "webrtc_ice_candidate",
        {"call_id": call_id, "candidate": candidate},
        room=f"user_{target_user_id}",
    )  # type: ignore[call-arg]

    return jsonify({"success": True})


# Call management endpoints
@api_bp.route("/initiate-call", methods=["POST"])
@login_required
def initiate_call():
    """Initiate a new call"""
    data = request.get_json()
    callee_id = data.get("callee_id")
    call_type = data.get("call_type", "voice")

    if not callee_id:
        return jsonify({"error": "Callee ID required"}), 400

    callee = User.query.get(callee_id)
    if not callee:
        return jsonify({"error": "User not found"}), 404

    # Create new call
    call = Call(
        call_id=str(uuid.uuid4()),
        caller_id=current_user.id,
        callee_id=callee_id,
        call_type=call_type,
        status="initiated",
    )

    db.session.add(call)
    db.session.commit()

    # Emit call initiation event
    socketio.emit(
        "incoming_call",
        {
            "call_id": call.call_id,
            "caller": {
                "id": current_user.id,
                "name": current_user.full_name,
                "username": current_user.username,
            },
            "call_type": call_type,
        },
        room=f"user_{callee_id}",
    )  # type: ignore[call-arg]

    return jsonify(
        {
            "success": True,
            "call_id": call.call_id,
            "call": {
                "id": call.id,
                "call_id": call.call_id,
                "caller": current_user.full_name,
                "callee": callee.full_name,
                "status": call.status,
            },
        }
    )


@api_bp.route("/answer-call", methods=["POST"])
@login_required
def answer_call():
    """Answer an incoming call"""
    data = request.get_json()
    call_id = data.get("call_id")

    call = Call.query.filter_by(call_id=call_id).first()
    if not call:
        return jsonify({"error": "Call not found"}), 404

    if call.callee_id != current_user.id:
        return jsonify({"error": "Not authorized to answer this call"}), 403

    call.status = "answered"
    call.answered_at = datetime.utcnow()
    db.session.commit()

    # Emit call answered event
    socketio.emit(
        "call_answered",
        {
            "call_id": call_id,
            "callee": {"id": current_user.id, "name": current_user.full_name},
        },
        room=f"user_{call.caller_id}",
    )  # type: ignore[call-arg]

    return jsonify({"success": True})


@api_bp.route("/end-call", methods=["POST"])
@login_required
def end_call():
    """End a call"""
    data = request.get_json()
    call_id = data.get("call_id")

    call = Call.query.filter_by(call_id=call_id).first()
    if not call:
        return jsonify({"error": "Call not found"}), 404

    if call.caller_id != current_user.id and call.callee_id != current_user.id:
        return jsonify({"error": "Not authorized to end this call"}), 403

    call.status = "ended"
    call.ended_at = datetime.utcnow()
    if call.answered_at:
        call.duration = int((call.ended_at - call.answered_at).total_seconds())
    db.session.commit()

    # Emit call ended event
    other_user_id = (
        call.callee_id if call.caller_id == current_user.id else call.caller_id
    )
    socketio.emit(
        "call_ended",
        {"call_id": call_id, "duration": call.duration},
        room=f"user_{other_user_id}",
    )  # type: ignore[call-arg]

    return jsonify({"success": True})


# Message endpoints
@api_bp.route("/send-message", methods=["POST"])
@login_required
def send_message():
    """Send a message"""
    data = request.get_json()
    chat_id = data.get("chat_id")
    content = data.get("content")

    if not chat_id or not content:
        return jsonify({"error": "Chat ID and content required"}), 400

    chat = Chat.query.get(chat_id)
    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    # Check if user is participant in chat
    if current_user not in chat.participants:
        return (
            jsonify({"error": "Not authorized to send message to this chat"}),
            403,
        )

    message = Message(
        chat_id=chat_id, sender_id=current_user.id, content=content
    )

    db.session.add(message)
    chat.updated_at = datetime.utcnow()
    db.session.commit()

    # Emit new message event to all chat participants
    for participant in chat.participants:
        if participant.id != current_user.id:
            socketio.emit(
                "new_message",
                {
                    "chat_id": chat_id,
                    "message": {
                        "id": message.id,
                        "content": message.content,
                        "sender": current_user.full_name,
                        "timestamp": message.created_at.isoformat(),
                    },
                },
                room=f"user_{participant.id}",
            )  # type: ignore[call-arg]

    return jsonify({"success": True, "message_id": message.id})


# Voicemail endpoints
@api_bp.route("/voicemails", methods=["GET"])
@login_required
def get_voicemails():
    """Get user's voicemails"""
    voicemails = (
        Voicemail.query.filter_by(recipient_id=current_user.id)
        .order_by(Voicemail.created_at.desc())
        .all()
    )

    return jsonify(
        {
            "success": True,
            "voicemails": [
                {
                    "id": vm.id,
                    "caller_name": vm.caller_name,
                    "caller_number": vm.caller_number,
                    "duration": vm.duration,
                    "is_read": vm.is_read,
                    "created_at": (
                        vm.created_at.isoformat() if vm.created_at else None
                    ),
                }
                for vm in voicemails
            ],
        }
    )


@api_bp.route("/mark-voicemail-read", methods=["POST"])
@login_required
def mark_voicemail_read():
    """Mark voicemail as read"""
    data = request.get_json()
    voicemail_id = data.get("voicemail_id")

    voicemail = Voicemail.query.get(voicemail_id)
    if not voicemail or voicemail.recipient_id != current_user.id:
        return jsonify({"error": "Voicemail not found"}), 404

    voicemail.is_read = True
    db.session.commit()

    return jsonify({"success": True})


@api_bp.route("/delete-voicemail", methods=["POST"])
@login_required
def delete_voicemail():
    """Delete a voicemail"""
    data = request.get_json()
    voicemail_id = data.get("voicemail_id")

    voicemail = Voicemail.query.get(voicemail_id)
    if not voicemail or voicemail.recipient_id != current_user.id:
        return jsonify({"error": "Voicemail not found"}), 404

    db.session.delete(voicemail)
    db.session.commit()

    return jsonify({"success": True})


# Contact endpoints
@api_bp.route("/contacts", methods=["GET"])
@login_required
def get_contacts():
    """Get user's contacts"""
    contacts = (
        Contact.query.filter_by(owner_id=current_user.id)
        .order_by(Contact.first_name)
        .all()
    )

    return jsonify(
        {
            "success": True,
            "contacts": [
                {
                    "id": contact.id,
                    "name": contact.full_name,
                    "phone": contact.phone_number,
                    "email": contact.email,
                    "company": contact.company,
                    "notes": contact.notes,
                }
                for contact in contacts
            ],
        }
    )


@api_bp.route("/add-contact", methods=["POST"])
@login_required
def add_contact():
    """Add a new contact"""
    data = request.get_json()

    if not data.get("name") or not data.get("phone"):
        return jsonify({"error": "Name and phone are required"}), 400

    # Split name into first and last name
    name_parts = data["name"].split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    contact = Contact(
        owner_id=current_user.id,
        first_name=first_name,
        last_name=last_name,
        phone_number=data["phone"],
        email=data.get("email"),
        company=data.get("company"),
        notes=data.get("notes"),
    )

    try:
        db.session.add(contact)
        db.session.commit()
        return jsonify({"success": True, "contact_id": contact.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/update-contact", methods=["POST"])
@login_required
def update_contact():
    """Update a contact"""
    data = request.get_json()
    contact_id = data.get("contact_id")

    contact = Contact.query.get(contact_id)
    if not contact or contact.owner_id != current_user.id:
        return jsonify({"error": "Contact not found"}), 404

    # Split name into first and last name
    if data.get("name"):
        name_parts = data["name"].split(" ", 1)
        contact.first_name = name_parts[0]
        contact.last_name = name_parts[1] if len(name_parts) > 1 else ""

    if data.get("phone"):
        contact.phone_number = data["phone"]
    if data.get("email"):
        contact.email = data["email"]
    if data.get("company"):
        contact.company = data["company"]
    if data.get("notes"):
        contact.notes = data["notes"]

    try:
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/delete-contact", methods=["POST"])
@login_required
def delete_contact():
    """Delete a contact"""
    data = request.get_json()
    contact_id = data.get("contact_id")

    contact = Contact.query.get(contact_id)
    if not contact or contact.owner_id != current_user.id:
        return jsonify({"error": "Contact not found"}), 404

    try:
        db.session.delete(contact)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# International calling endpoints
@api_bp.route("/international-rates", methods=["GET"])
@login_required
def get_international_rates():
    """Get international calling rates"""
    rates = InternationalRate.query.all()

    return jsonify(
        {
            "success": True,
            "rates": [
                {
                    "id": rate.id,
                    "country_code": rate.country_code,
                    "country_name": rate.country_name,
                    "rate_per_minute": float(rate.rate_per_minute),
                }
                for rate in rates
            ],
        }
    )


@api_bp.route("/make-international-call", methods=["POST"])
@login_required
def make_international_call():
    """Make an international call"""
    data = request.get_json()
    destination = data.get("destination")

    if not destination:
        return jsonify({"error": "Destination number required"}), 400

    # Extract country code from destination
    country_code = None
    if destination.startswith("+"):
        # Find the country code
        for rate in InternationalRate.query.all():
            if destination.startswith(rate.country_code):
                country_code = rate.country_code
                break

    if not country_code:
        return jsonify({"error": "Unsupported country code"}), 400

    # Create call record
    call = Call(
        call_id=str(uuid.uuid4()),
        caller_id=current_user.id,
        destination=destination,
        is_international=True,
        destination_country=country_code,
        call_type="voice",
        status="initiated",
    )

    db.session.add(call)
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "call_id": call.call_id,
            "call": {
                "id": call.id,
                "destination": destination,
                "country_code": country_code,
                "status": call.status,
            },
        }
    )


# SIP Trunk endpoints
@api_bp.route("/sip-trunks", methods=["GET"])
@login_required
def get_sip_trunks():
    """Get SIP trunks"""
    trunks = SIPTrunk.query.all()

    return jsonify(
        {
            "success": True,
            "trunks": [
                {
                    "id": trunk.id,
                    "name": trunk.name,
                    "provider": trunk.provider,
                    "host": trunk.host,
                    "port": trunk.port,
                    "username": trunk.username,
                    "is_active": trunk.is_active,
                }
                for trunk in trunks
            ],
        }
    )


@api_bp.route("/test-sip-trunk", methods=["POST"])
@login_required
def test_sip_trunk():
    """Test SIP trunk connection"""
    data = request.get_json()
    trunk_id = data.get("trunk_id")

    trunk = SIPTrunk.query.get(trunk_id)
    if not trunk:
        return jsonify({"error": "SIP trunk not found"}), 404

    # Simulate SIP trunk test
    import random

    success = random.choice([True, False])

    if success:
        return jsonify(
            {"success": True, "message": "SIP trunk connection successful"}
        )
    else:
        return jsonify({"error": "SIP trunk connection failed"}), 500


# Admin endpoints
@api_bp.route("/update-user-status", methods=["POST"])
@login_required
def update_user_status():
    """Update user status (admin function)"""
    data = request.get_json()
    user_id = data.get("user_id")
    status = data.get("status")

    if not user_id or not status:
        return jsonify({"error": "User ID and status required"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if status not in ["Available", "Away", "DND", "Busy"]:
        return jsonify({"error": "Invalid status"}), 400

    user.status = status
    user.last_seen = datetime.utcnow()
    db.session.commit()

    # Emit status update
    socketio.emit(
        "user_status_update",
        {"user_id": user.id, "status": status, "username": user.username},
    )  # type: ignore[call-arg]

    return jsonify({"success": True, "status": status})


@api_bp.route("/delete-call", methods=["POST"])
@login_required
def delete_call():
    """Delete a call record (admin function)"""
    data = request.get_json()
    call_id = data.get("call_id")

    call = Call.query.get(call_id)
    if not call:
        return jsonify({"error": "Call not found"}), 404

    db.session.delete(call)
    db.session.commit()

    return jsonify({"success": True})


@api_bp.route("/export-contacts", methods=["GET"])
@login_required
def export_contacts():
    """Export contacts to CSV"""
    contacts = (
        Contact.query.filter_by(owner_id=current_user.id)
        .order_by(Contact.first_name)
        .all()
    )

    output = StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(["Name", "Phone", "Email", "Company", "Notes"])

    # Write data
    for contact in contacts:
        writer.writerow(
            [
                contact.full_name,
                contact.phone_number,
                contact.email or "",
                contact.company or "",
                contact.notes or "",
            ]
        )

    output.seek(0)

    from flask import make_response

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = (
        "attachment; filename=contacts_export.csv"
    )

    return response


@api_bp.route("/import-contacts", methods=["POST"])
@login_required
def import_contacts():
    """Import contacts from CSV file"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.endswith(".csv"):
        return jsonify({"error": "Please upload a CSV file"}), 400

    skip_duplicates = (
        request.form.get("skip_duplicates", "false").lower() == "true"
    )

    try:
        # Read CSV file
        content = file.read().decode("utf-8")
        csv_reader = csv.DictReader(StringIO(content))

        imported_count = 0
        skipped_count = 0

        for row in csv_reader:
            name = row.get("Name", "").strip()
            phone = row.get("Phone", "").strip()
            email = row.get("Email", "").strip()
            company = row.get("Company", "").strip()
            notes = row.get("Notes", "").strip()

            if not name or not phone:
                continue

            # Split name into first and last name
            name_parts = name.split(" ", 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            # Check for duplicates if skip_duplicates is True
            if skip_duplicates:
                existing = Contact.query.filter_by(
                    owner_id=current_user.id, phone_number=phone
                ).first()
                if existing:
                    skipped_count += 1
                    continue

            contact = Contact(
                owner_id=current_user.id,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone,
                email=email if email else None,
                company=company if company else None,
                notes=notes if notes else None,
            )

            db.session.add(contact)
            imported_count += 1

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "imported_count": imported_count,
                "skipped_count": skipped_count,
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error importing contacts: {str(e)}"}), 500


@api_bp.route("/voicemail-settings", methods=["POST"])
@login_required
def save_voicemail_settings():
    """Save voicemail settings"""
    data = request.get_json()

    # In a real implementation, you would save these settings to the database
    # For now, we'll just return success
    return jsonify(
        {"success": True, "message": "Voicemail settings saved successfully"}
    )
