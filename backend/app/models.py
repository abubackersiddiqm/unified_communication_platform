# -----------------------------------------------------------------------------
# Project: Unified Communication Platform
# Author: Abubacker Siddiq M
# Copyright (c) 2025 Abubacker Siddiq M
# License: MIT License (See LICENSE file for details)
# -----------------------------------------------------------------------------

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from . import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash

# Association tables for many-to-many relationships
user_roles = db.Table(
    "user_roles",
    db.Column(
        "user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True
    ),
    db.Column(
        "role_id", db.Integer, db.ForeignKey("role.id"), primary_key=True
    ),
)

chat_participants = db.Table(
    "chat_participants",
    db.Column(
        "chat_id", db.Integer, db.ForeignKey("chat.id"), primary_key=True
    ),
    db.Column(
        "user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True
    ),
)


class Role(db.Model):  # type: ignore[name-defined]
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    users = db.relationship(
        "User", secondary=user_roles, back_populates="roles"
    )


class User(UserMixin, db.Model):  # type: ignore[name-defined]
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone_number = db.Column(db.String(20))
    extension = db.Column(db.String(10), unique=True)
    status = db.Column(
        db.String(20), default="Available"
    )  # Available, Away, DND, Busy
    avatar = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    roles = db.relationship(
        "Role", secondary=user_roles, back_populates="users"
    )
    calls_initiated = db.relationship(
        "Call", foreign_keys="Call.caller_id", back_populates="caller"
    )
    calls_received = db.relationship(
        "Call", foreign_keys="Call.callee_id", back_populates="callee"
    )
    chats_created = db.relationship(
        "Chat", foreign_keys="Chat.created_by", back_populates="creator"
    )
    chat_participations = db.relationship(
        "Chat", secondary=chat_participants, back_populates="participants"
    )
    messages = db.relationship("Message", back_populates="sender")
    voicemails = db.relationship("Voicemail", back_populates="recipient")
    contacts = db.relationship("Contact", back_populates="owner")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, role_name):
        return any(role.name == role_name for role in self.roles)  # type: ignore

    def is_admin(self):
        return self.has_role("Admin")

    def is_agent(self):
        return self.has_role("Agent")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class SIPTrunk(db.Model):  # type: ignore[name-defined]
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    provider = db.Column(db.String(100), nullable=False)
    sip_server = db.Column(db.String(100), nullable=False)
    sip_port = db.Column(db.Integer, default=5060)
    username = db.Column(db.String(100))
    password = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    calls = db.relationship("Call", back_populates="sip_trunk")


class InternationalRate(db.Model):  # type: ignore[name-defined]
    id = db.Column(db.Integer, primary_key=True)
    country_code = db.Column(
        db.String(10), nullable=False
    )  # e.g., +91 for India
    country_name = db.Column(db.String(100), nullable=False)
    rate_per_minute = db.Column(
        db.Numeric(10, 4), nullable=False
    )  # Rate in USD
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Call(db.Model):  # type: ignore[name-defined]
    id = db.Column(db.Integer, primary_key=True)
    call_id = db.Column(db.String(100), unique=True, nullable=False)
    caller_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    callee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    call_type = db.Column(db.String(20), default="voice")  # voice, video
    status = db.Column(
        db.String(20), default="initiated"
    )  # initiated, ringing, answered, ended, missed
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    duration = db.Column(db.Integer)  # in seconds
    recording_url = db.Column(db.String(255))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # International calling fields
    is_international = db.Column(db.Boolean, default=False)
    destination_country = db.Column(db.String(10))  # Country code
    destination_number = db.Column(db.String(20))  # Full international number
    sip_trunk_id = db.Column(db.Integer, db.ForeignKey("sip_trunk.id"))
    cost = db.Column(db.Numeric(10, 4))  # Call cost in USD

    # Relationships
    caller = db.relationship(
        "User", foreign_keys=[caller_id], back_populates="calls_initiated"
    )
    callee = db.relationship(
        "User", foreign_keys=[callee_id], back_populates="calls_received"
    )
    sip_trunk = db.relationship("SIPTrunk", back_populates="calls")


class Chat(db.Model):  # type: ignore[name-defined]
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    chat_type = db.Column(db.String(20), default="direct")  # direct, group
    created_by = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    creator = db.relationship(
        "User", foreign_keys=[created_by], back_populates="chats_created"
    )
    participants = db.relationship(
        "User",
        secondary=chat_participants,
        back_populates="chat_participations",
    )
    messages = db.relationship("Message", back_populates="chat")


class Message(db.Model):  # type: ignore[name-defined]
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey("chat.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(
        db.String(20), default="text"
    )  # text, file, image, audio
    file_url = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    chat = db.relationship("Chat", back_populates="messages")
    sender = db.relationship("User", back_populates="messages")


class Voicemail(db.Model):  # type: ignore[name-defined]
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )
    caller_number = db.Column(db.String(20))
    caller_name = db.Column(db.String(100))
    audio_url = db.Column(db.String(255), nullable=False)
    duration = db.Column(db.Integer)  # in seconds
    is_read = db.Column(db.Boolean, default=False)
    is_archived = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    recipient = db.relationship("User", back_populates="voicemails")


class Contact(db.Model):  # type: ignore[name-defined]
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50))
    email = db.Column(db.String(120))
    phone_number = db.Column(db.String(20))
    company = db.Column(db.String(100))
    position = db.Column(db.String(100))
    notes = db.Column(db.Text)
    avatar = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    owner = db.relationship("User", back_populates="contacts")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class CallQueue(db.Model):  # type: ignore[name-defined]
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    strategy = db.Column(
        db.String(20), default="ringall"
    )  # ringall, leastrecent, fewestcalls
    timeout = db.Column(db.Integer, default=30)  # in seconds
    max_calls = db.Column(db.Integer, default=10)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    agents = db.relationship("User", secondary="queue_agents")


# Association table for queue agents
queue_agents = db.Table(
    "queue_agents",
    db.Column(
        "queue_id",
        db.Integer,
        db.ForeignKey("call_queue.id"),
        primary_key=True,
    ),
    db.Column(
        "user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True
    ),
)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
