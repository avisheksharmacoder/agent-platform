from fastapi import APIRouter, Request, HTTPException
from uuid import uuid4
from datetime import datetime
from src.v1.models import (
    UserAIChatSession,
    UserAIChatSessionUpdate,
    UserChatMessage,
    AIChatMessage
)

chats_router = APIRouter(prefix="/chats", tags=["chats"])

@chats_router.post("/", response_model=UserAIChatSession)
async def create_chat_session(session: UserAIChatSession, request: Request):
    db = request.app.state.db
    
    # Generate session_id backend side if not provided or empty
    if not session.session_id or session.session_id.strip() == "":
        session.session_id = f"chat_{uuid4().hex}"
    elif not session.session_id.startswith("chat_"):
        # Enforce prefix for DB scanning if they did provide one
        session.session_id = f"chat_{session.session_id}"
        
    # Generate a default name if not provided
    if not session.name or session.name.strip() == "":
        session.name = f"New Chat {datetime.now().strftime('%b %d, %H:%M')}"
        
    session.created_at = datetime.now()
    session.modified_at = datetime.now()
    
    payload = session.model_dump(mode="json")
    await db.insert(session.session_id, payload)
    
    return session

@chats_router.get("/{session_id}", response_model=UserAIChatSession)
async def get_chat_session(session_id: str, request: Request):
    db = request.app.state.db
    # Enforce prefix
    db_key = session_id if session_id.startswith("chat_") else f"chat_{session_id}"
    
    payload = await db.get(db_key)
    if not payload:
        raise HTTPException(status_code=404, detail="Chat session not found")
        
    return UserAIChatSession(**payload)

@chats_router.get("/user/{user_id}", response_model=list[UserAIChatSession])
async def get_user_chat_sessions(user_id: str, request: Request):
    db = request.app.state.db
    records = await db.scan_prefix("chat_")
    
    # Filter by user_id
    user_sessions = []
    for sid, payload in records:
        if payload.get("user_id") == user_id:
            user_sessions.append(UserAIChatSession(**payload))
            
    # Sort by created_at descending (newest first)
    user_sessions.sort(key=lambda x: x.created_at, reverse=True)
    return user_sessions

@chats_router.put("/{session_id}", response_model=UserAIChatSession)
async def update_chat_session(session_id: str, update_data: UserAIChatSessionUpdate, request: Request):
    db = request.app.state.db
    db_key = session_id if session_id.startswith("chat_") else f"chat_{session_id}"
    
    existing = await db.get(db_key)
    if not existing:
        raise HTTPException(status_code=404, detail="Chat session not found")
        
    update_dict = update_data.model_dump(exclude_unset=True, mode="json")
    
    # Always update modified_at
    update_dict["modified_at"] = datetime.now().isoformat()
    
    existing.update(update_dict)
    
    await db.upsert(db_key, existing)
    return UserAIChatSession(**existing)

@chats_router.delete("/{session_id}")
async def delete_chat_session(session_id: str, request: Request):
    db = request.app.state.db
    db_key = session_id if session_id.startswith("chat_") else f"chat_{session_id}"
    
    existing = await db.get(db_key)
    if not existing:
        raise HTTPException(status_code=404, detail="Chat session not found")
        
    await db.delete(db_key)
    return {"message": "Chat session deleted successfully", "session_id": db_key}
