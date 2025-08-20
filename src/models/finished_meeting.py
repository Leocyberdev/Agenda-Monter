from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import db
from src.utils.timezone_utils import to_brazil_timezone, format_datetime_display

class FinishedMeeting(db.Model):
    __tablename__ = "finished_meetings"

    id = db.Column(db.Integer, primary_key=True)
    original_meeting_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Campos de data/hora com timezone para trabalhar em UTC
    start_datetime = db.Column(db.DateTime(timezone=True), nullable=False)
    end_datetime = db.Column(db.DateTime(timezone=True), nullable=False)
    finished_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    # Foreign keys
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)

    # Campos adicionais
    participants = db.Column(db.Text)
    was_recurring = db.Column(db.Boolean, default=False)
    recurrence_type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)

    # Relacionamentos
    room = relationship("Room", backref="finished_meetings")
    creator = relationship("User", backref="finished_meetings", foreign_keys=[created_by])

    def to_dict(self):
        return {
            'id': self.id,
            'original_meeting_id': self.original_meeting_id,
            'title': self.title,
            'start_datetime': self.start_datetime.isoformat() if self.start_datetime else None,
            'end_datetime': self.end_datetime.isoformat() if self.end_datetime else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'participants': self.participants,
            'room_id': self.room_id,
            'room_name': self.room.name if self.room else None,
            'created_by': self.created_by,
            'creator_name': self.creator.username if self.creator else None,
            'was_recurring': self.was_recurring,
            'recurrence_type': self.recurrence_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def get_participants_list(self):
        if self.participants:
            return [p.strip() for p in self.participants.split(',') if p.strip()]
        return []

    @property
    def start_datetime_brazil(self):
        """Retorna data/hora de início no timezone do Brasil"""
        return to_brazil_timezone(self.start_datetime)

    @property
    def end_datetime_brazil(self):
        """Retorna data/hora de fim no timezone do Brasil"""
        return to_brazil_timezone(self.end_datetime)

    @property
    def finished_at_brazil(self):
        """Retorna data/hora de finalização no timezone do Brasil"""
        return to_brazil_timezone(self.finished_at)

    @property
    def created_at_brazil(self):
        """Retorna data/hora de criação no timezone do Brasil"""
        return to_brazil_timezone(self.created_at)

    @property
    def start_display(self):
        """Retorna data/hora de início formatada para exibição"""
        return format_datetime_display(self.start_datetime)

    @property
    def end_display(self):
        """Retorna data/hora de fim formatada para exibição"""
        return format_datetime_display(self.end_datetime)

    @property
    def finished_display(self):
        """Retorna data/hora de finalização formatada para exibição"""
        return format_datetime_display(self.finished_at)

    @property
    def created_display(self):
        """Retorna data/hora de criação formatada para exibição"""
        return format_datetime_display(self.created_at)

    def __repr__(self):
        return f'<FinishedMeeting {self.title}>'

