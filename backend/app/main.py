# -----------------------------------------------------------------------------
# Project: Unified Communication Platform
# Author: Abubacker Siddiq M
# Copyright (c) 2025 Abubacker Siddiq M
# License: MIT License (See LICENSE file for details)
# -----------------------------------------------------------------------------

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    flash,
    redirect,
    url_for,
)
from flask_login import login_required, current_user
from .models import User, Call, Chat, Message, Voicemail, Contact, db
from . import socketio
from datetime import datetime, timedelta
import uuid

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@main_bp.route("/dashboard")
@login_required
def dashboard():
    """Main dashboard with overview of calls, chats, and voicemails"""
    # Get recent calls
    recent_calls = (
        Call.query.filter(
            (Call.caller_id == current_user.id)
            | (
                (Call.callee_id == current_user.id)
                & (Call.callee_id.isnot(None))
            )
        )
        .order_by(Call.created_at.desc())
        .limit(10)
        .all()
    )

    # Get recent chats
    user_chats = (
        Chat.query.join(Chat.participants)
        .filter(Chat.participants.any(id=current_user.id))
        .order_by(Chat.updated_at.desc())
        .limit(5)
        .all()
    )

    # Get unread voicemails
    unread_voicemails = (
        Voicemail.query.filter_by(recipient_id=current_user.id, is_read=False)
        .order_by(Voicemail.created_at.desc())
        .all()
    )

    # Get online users - only show users who have been active in the last 5 minutes
    five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
    online_users = (
        User.query.filter(
            User.is_active,
            User.last_seen >= five_minutes_ago,
            User.id != current_user.id,  # Exclude current user
        )
        .limit(10)
        .all()
    )

    return render_template(
        "main/dashboard.html",
        recent_calls=recent_calls,
        user_chats=user_chats,
        unread_voicemails=unread_voicemails,
        online_users=online_users,
    )


@main_bp.route("/phone")
@login_required
def phone():
    """Web-based phone dialer interface"""
    contacts = Contact.query.filter_by(owner_id=current_user.id).all()
    # Get the number parameter if passed from contacts
    number = request.args.get("number", "")
    return render_template(
        "main/phone.html", contacts=contacts, prefill_number=number
    )


@main_bp.route("/chat")
@login_required
def chat():
    """Chat interface"""
    user_chats = (
        Chat.query.join(Chat.participants)
        .filter(Chat.participants.any(id=current_user.id))
        .order_by(Chat.updated_at.desc())
        .all()
    )

    users = User.query.filter(User.id != current_user.id, User.is_active).all()

    # Get the number parameter if passed from contacts
    number = request.args.get("number", "")
    return render_template(
        "main/chat.html", chats=user_chats, users=users, prefill_number=number
    )


@main_bp.route("/voicemail")
@login_required
def voicemail():
    """Voicemail management"""
    voicemails = (
        Voicemail.query.filter_by(recipient_id=current_user.id)
        .order_by(Voicemail.created_at.desc())
        .all()
    )
    return render_template("main/voicemail.html", voicemails=voicemails)


@main_bp.route("/contacts")
@login_required
def contacts():
    """Contact management"""
    contacts = (
        Contact.query.filter_by(owner_id=current_user.id)
        .order_by(Contact.first_name, Contact.last_name)
        .all()
    )
    return render_template("main/contacts.html", contacts=contacts)


# API endpoints for real-time functionality


@main_bp.route("/api/update-status", methods=["POST"])
@login_required
def update_status():
    """Update user status"""
    data = request.get_json()
    status = data.get("status")

    if status in ["Available", "Away", "DND", "Busy"]:
        current_user.status = status
        current_user.last_seen = datetime.utcnow()
        db.session.commit()

        # Emit status update to all connected clients
        socketio.emit(
            "user_status_update",
            {
                "user_id": current_user.id,
                "status": status,
                "username": current_user.username,
            },
        )  # type: ignore[call-arg]

        return jsonify({"success": True, "status": status})

    return jsonify({"error": "Invalid status"}), 400


@main_bp.route("/api/initiate-call", methods=["POST"])
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


@main_bp.route("/api/answer-call", methods=["POST"])
@login_required
def answer_call():
    """Answer an incoming call"""
    data = request.get_json()
    call_id = data.get("call_id")

    call = Call.query.filter_by(
        call_id=call_id, callee_id=current_user.id
    ).first()
    if not call:
        return jsonify({"error": "Call not found"}), 404

    call.status = "answered"
    call.start_time = datetime.utcnow()
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

    return jsonify({"success": True, "call_id": call_id})


@main_bp.route("/api/end-call", methods=["POST"])
@login_required
def end_call():
    """End a call"""
    data = request.get_json()
    call_id = data.get("call_id")

    call = (
        Call.query.filter_by(call_id=call_id)
        .filter(
            (Call.caller_id == current_user.id)
            | (
                (Call.callee_id == current_user.id)
                & (Call.callee_id.isnot(None))
            )
        )
        .first()
    )

    if not call:
        return jsonify({"error": "Call not found"}), 404

    call.status = "ended"
    call.end_time = datetime.utcnow()
    if call.start_time:
        call.duration = int((call.end_time - call.start_time).total_seconds())

    db.session.commit()

    # Emit call ended event (only for internal calls with callee_id)
    if call.callee_id is not None:
        other_user_id = (
            call.callee_id
            if call.caller_id == current_user.id
            else call.caller_id
        )
        socketio.emit(
            "call_ended",
            {"call_id": call_id, "duration": call.duration},
            room=f"user_{other_user_id}",
        )  # type: ignore[call-arg]

    return jsonify({"success": True, "call_id": call_id})


@main_bp.route("/api/make-external-call", methods=["POST"])
@login_required
def make_external_call():
    """Make an external call through SIP trunk"""
    print("DEBUG: make_external_call function started")
    try:
        data = request.get_json()
        print(f"DEBUG: Request data: {data}")
        phone_number = data.get("phone_number")
        call_type = data.get("call_type", "voice")

        if not phone_number:
            return jsonify({"error": "Phone number required"}), 400

        # Clean the phone number (remove spaces, dashes, etc.)
        phone_number = "".join(filter(str.isdigit, phone_number))

        if not phone_number:
            return jsonify({"error": "Invalid phone number"}), 400

        # Check if user has a phone number set
        if not current_user.phone_number:
            return (
                jsonify(
                    {
                        "error": "Please set your phone number in profile settings"
                    }
                ),
                400,
            )

        print(f"DEBUG: Creating call for {phone_number}")

        # Create new external call
        call = Call(
            call_id=str(uuid.uuid4()),
            caller_id=current_user.id,
            callee_id=None,  # External call
            call_type=call_type,
            status="initiated",
            destination_number=phone_number,
            is_international=phone_number.startswith("+")
            or len(phone_number) > 10,
        )

        print(f"DEBUG: Call object created: {call.call_id}")

        db.session.add(call)
        db.session.commit()

        print("DEBUG: Call saved to database")

        # In a real implementation, you would:
        # 1. Connect to your SIP trunk provider
        # 2. Send the call request
        # 3. Handle the response

        # For demo purposes, we'll simulate the call
        try:
            # Simulate SIP trunk connection
            import time

            time.sleep(2)  # Simulate network delay

            # Update call status to ringing
            call.status = "ringing"
            db.session.commit()

            print("DEBUG: Call simulation completed")

            return jsonify(
                {
                    "success": True,
                    "call_id": call.call_id,
                    "message": f"Initiating call to {phone_number} through SIP trunk",
                    "call": {
                        "id": call.id,
                        "call_id": call.call_id,
                        "destination": phone_number,
                        "status": call.status,
                        "caller_id": current_user.phone_number,
                    },
                }
            )

        except Exception as e:
            print(f"DEBUG: Error in call simulation: {e}")
            call.status = "failed"
            db.session.commit()
            return jsonify({"error": f"Call failed: {str(e)}"}), 500

    except Exception as e:
        print(f"DEBUG: Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@main_bp.route("/api/validate-phone-number", methods=["POST"])
@login_required
def validate_phone_number():
    """Validate phone number format"""
    data = request.get_json()
    phone_number = data.get("phone_number")

    if not phone_number:
        return jsonify({"valid": False, "error": "Phone number required"}), 400

    # Clean the phone number
    clean_number = "".join(filter(str.isdigit, phone_number))

    # Basic validation
    if len(clean_number) < 7 or len(clean_number) > 15:
        return (
            jsonify({"valid": False, "error": "Invalid phone number length"}),
            400,
        )

    # Check if it's a valid format
    if phone_number.startswith("+"):
        # International number
        if len(clean_number) < 10:
            return (
                jsonify(
                    {"valid": False, "error": "Invalid international number"}
                ),
                400,
            )

    return jsonify(
        {
            "valid": True,
            "clean_number": clean_number,
            "formatted_number": format_phone_number(clean_number),
        }
    )


def format_phone_number(number):
    """Format phone number for display"""
    if len(number) == 10:
        return f"({number[:3]}) {number[3:6]}-{number[6:]}"
    elif len(number) == 11 and number.startswith("1"):
        return f"+1 ({number[1:4]}) {number[4:7]}-{number[7:]}"
    else:
        return number


@main_bp.route("/api/create-chat", methods=["POST"])
@login_required
def create_chat():
    """Create a new chat"""
    data = request.get_json()
    participant_ids = data.get("participant_ids", [])
    chat_type = data.get("chat_type", "direct")
    name = data.get("name", "")

    if chat_type == "direct" and len(participant_ids) != 1:
        return (
            jsonify({"error": "Direct chat requires exactly one participant"}),
            400,
        )

    # Create chat
    chat = Chat(name=name, chat_type=chat_type, created_by=current_user.id)

    # Add participants
    participants = [current_user]
    for user_id in participant_ids:
        user = User.query.get(user_id)
        if user:
            participants.append(user)

    chat.participants = participants  # type: ignore
    db.session.add(chat)
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "chat": {
                "id": chat.id,
                "name": chat.name,
                "chat_type": chat.chat_type,
                "participants": [
                    {"id": p.id, "name": p.full_name} for p in participants
                ],
            },
        }
    )


@main_bp.route("/api/send-message", methods=["POST"])
@login_required
def send_message():
    """Send a message in a chat"""
    data = request.get_json()
    chat_id = data.get("chat_id")
    content = data.get("content")
    message_type = data.get("message_type", "text")

    if not content:
        return jsonify({"error": "Message content required"}), 400

    # Verify user is participant in chat
    chat = (
        Chat.query.join(Chat.participants)
        .filter(Chat.id == chat_id, Chat.participants.any(id=current_user.id))
        .first()
    )

    if not chat:
        return jsonify({"error": "Chat not found or access denied"}), 404

    # Create message
    message = Message(
        chat_id=chat_id,
        sender_id=current_user.id,
        content=content,
        message_type=message_type,
    )

    db.session.add(message)
    db.session.commit()

    # Emit message to chat participants
    message_data = {
        "id": message.id,
        "content": message.content,
        "message_type": message.message_type,
        "sender": {
            "id": current_user.id,
            "name": current_user.full_name,
            "username": current_user.username,
        },
        "created_at": message.created_at.isoformat(),
    }

    for participant in chat.participants:
        if participant.id != current_user.id:
            socketio.emit(
                "new_message", message_data, room=f"user_{participant.id}"
            )  # type: ignore[call-arg]

    return jsonify({"success": True, "message": message_data})


@main_bp.route("/api/mark-voicemail-read", methods=["POST"])
@login_required
def mark_voicemail_read():
    """Mark voicemail as read"""
    data = request.get_json()
    voicemail_id = data.get("voicemail_id")

    voicemail = Voicemail.query.filter_by(
        id=voicemail_id, recipient_id=current_user.id
    ).first()

    if not voicemail:
        return jsonify({"error": "Voicemail not found"}), 404

    voicemail.is_read = True
    db.session.commit()

    return jsonify({"success": True})


@main_bp.route("/api/send-sms", methods=["POST"])
@login_required
def send_sms():
    """Send SMS to external number"""
    data = request.get_json()
    phone_number = data.get("phone_number")
    message = data.get("message")

    if not phone_number or not message:
        return jsonify({"error": "Phone number and message required"}), 400

    # Clean the phone number
    phone_number = "".join(filter(str.isdigit, phone_number))

    if not phone_number:
        return jsonify({"error": "Invalid phone number"}), 400

    # In a real implementation, you would:
    # 1. Connect to your SMS gateway provider
    # 2. Send the SMS
    # 3. Handle the response

    # For demo purposes, we'll simulate SMS sending
    try:
        # Simulate SMS gateway connection
        import time

        time.sleep(1)  # Simulate network delay

        # Create a message record for tracking
        # Note: This would typically be stored in a separate SMS model
        # For now, we'll just return success

        return jsonify(
            {
                "success": True,
                "message": f"SMS sent to {phone_number}",
                "sms_id": str(uuid.uuid4()),
            }
        )

    except Exception as e:
        return jsonify({"error": f"SMS failed: {str(e)}"}), 500


@main_bp.route("/api/call-external", methods=["POST"])
@login_required
def call_external():
    """Make a call to external number (alias for make-external-call)"""
    return make_external_call()


@main_bp.route("/api/chats/<int:chat_id>/messages", methods=["GET"])
@login_required
def get_chat_messages(chat_id):
    """Get messages for a specific chat"""
    # Verify user is participant in chat
    chat = (
        Chat.query.join(Chat.participants)
        .filter(Chat.id == chat_id, Chat.participants.any(id=current_user.id))
        .first()
    )

    if not chat:
        return jsonify({"error": "Chat not found or access denied"}), 404

    messages = (
        Message.query.filter_by(chat_id=chat_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    return jsonify(
        [
            {
                "id": msg.id,
                "content": msg.content,
                "message_type": msg.message_type,
                "sender": {
                    "id": msg.sender.id,
                    "name": msg.sender.full_name,
                    "username": msg.sender.username,
                },
                "created_at": (
                    msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    if msg.created_at
                    else None
                ),
            }
            for msg in messages
        ]
    )


@main_bp.route("/api/chats", methods=["GET"])
@login_required
def get_user_chats():
    """Get all chats for the current user"""
    user_chats = (
        Chat.query.join(Chat.participants)
        .filter(Chat.participants.any(id=current_user.id))
        .order_by(Chat.updated_at.desc())
        .all()
    )

    return jsonify(
        {
            "success": True,
            "chats": [
                {
                    "id": chat.id,
                    "name": chat.name,
                    "chat_type": chat.chat_type,
                    "updated_at": (
                        chat.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                        if chat.updated_at
                        else None
                    ),
                    "participants": [
                        {
                            "id": p.id,
                            "name": p.full_name,
                            "username": p.username,
                        }
                        for p in chat.participants
                    ],
                    "message_count": len(chat.messages),
                }
                for chat in user_chats
            ],
        }
    )


@main_bp.route("/api/heartbeat", methods=["POST"])
@login_required
def user_heartbeat():
    """Update user's last seen timestamp to keep them online"""
    current_user.last_seen = datetime.utcnow()
    db.session.commit()

    return jsonify(
        {"success": True, "timestamp": current_user.last_seen.isoformat()}
    )


@main_bp.route("/api/online-users", methods=["GET"])
@login_required
def get_online_users():
    """Get list of online users"""
    # Get users who have been active in the last 5 minutes
    five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
    online_users = User.query.filter(
        User.is_active,
        User.last_seen >= five_minutes_ago,
        User.id != current_user.id,
    ).all()

    return jsonify(
        {
            "success": True,
            "online_users": [
                {
                    "id": user.id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "status": user.status,
                    "last_seen": (
                        user.last_seen.isoformat() if user.last_seen else None
                    ),
                }
                for user in online_users
            ],
        }
    )


# Socket.IO event handlers
@socketio.on("connect")
def handle_connect():
    """Handle client connection"""
    if current_user.is_authenticated:
        # Update user's last seen
        current_user.last_seen = datetime.utcnow()
        db.session.commit()

        # Emit user connected event to all clients
        socketio.emit(
            "user_connected",
            {
                "user_id": current_user.id,
                "username": current_user.username,
                "status": current_user.status,
            },
        )  # type: ignore[call-arg]


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection"""
    if current_user.is_authenticated:
        # Update user's last seen
        current_user.last_seen = datetime.utcnow()
        db.session.commit()

        # Emit user disconnected event to all clients
        socketio.emit(
            "user_disconnected",
            {"user_id": current_user.id, "username": current_user.username},
        )  # type: ignore[call-arg]


@socketio.on("join_room")
def handle_join_room(data):
    """Join a room for private messaging"""
    room = data.get("room")
    if room:
        socketio.join_room(room)  # type: ignore[attr-defined]
