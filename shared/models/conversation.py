from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole
    content: str
    image_url: Optional[str] = None
    image_data: Optional[str] = None  # Base64 encoded
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SessionContext(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None
    known_conditions: List[str] = Field(default_factory=list)
    current_medications: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    language: str = "en"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    messages: List[Message] = Field(default_factory=list)
    context: Optional[SessionContext] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def add_message(self, role: MessageRole, content: str, **kwargs) -> Message:
        msg = Message(role=role, content=content, **kwargs)
        self.messages.append(msg)
        self.updated_at = datetime.utcnow()
        return msg

    def get_history_text(self, max_messages: int = 10) -> str:
        recent = self.messages[-max_messages:]
        lines = []
        for msg in recent:
            lines.append(f"{msg.role.value.upper()}: {msg.content}")
        return "\n".join(lines)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    image_data: Optional[str] = None  # Base64 encoded image
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    triage_level: Optional[str] = None
    doctor_recommendation: Optional[Dict[str, Any]] = None
    sources: List[str] = Field(default_factory=list)
    conversation_id: str
    disclaimer: str = (
        "⚠️ MEDICAL DISCLAIMER: This information is for educational purposes only "
        "and does not constitute medical advice. Always consult a qualified healthcare "
        "professional for medical decisions. In case of emergency, call emergency services immediately."
    )
