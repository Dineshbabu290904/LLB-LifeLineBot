from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from service import (
    create_conversation,
    get_conversation,
    add_message,
    get_by_session,
    delete_conversation,
    list_conversations,
)

router = APIRouter()


class CreateConversationRequest(BaseModel):
    session_id: str = Field(..., description="Session identifier linking this conversation to a user session")
    user_id: Optional[str] = Field(None, description="Optional authenticated user ID")
    metadata: Optional[dict] = Field(None, description="Arbitrary metadata (e.g. language, channel)")


class MessageRequest(BaseModel):
    role: str = Field(..., description="Message author role: user | assistant | system | tool")
    content: str = Field(..., description="Message text content")
    metadata: Optional[dict] = Field(None, description="Optional per-message metadata")


@router.post("/conversations", status_code=201)
async def create(req: CreateConversationRequest):
    """Create a new conversation record."""
    result = await create_conversation(req.session_id, req.user_id, req.metadata)
    return result


@router.get("/conversations")
async def list_all(
    limit: int = Query(50, ge=1, le=500),
    skip: int = Query(0, ge=0),
):
    """List recent conversations (messages excluded for brevity)."""
    return await list_conversations(limit=limit, skip=skip)


@router.get("/conversations/session/{session_id}")
async def by_session(session_id: str):
    """Return all conversations belonging to a session."""
    results = await get_by_session(session_id)
    return {"session_id": session_id, "count": len(results), "conversations": results}


@router.get("/conversations/{conversation_id}")
async def get(conversation_id: str):
    """Retrieve a single conversation with its full message history."""
    doc = await get_conversation(conversation_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")
    return doc


@router.put("/conversations/{conversation_id}/messages", status_code=200)
async def append_message(conversation_id: str, msg: MessageRequest):
    """Append a message to an existing conversation."""
    updated = await add_message(
        conversation_id,
        {"role": msg.role, "content": msg.content, "metadata": msg.metadata or {}},
    )
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")
    return updated


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete(conversation_id: str):
    """Permanently delete a conversation."""
    success = await delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")
