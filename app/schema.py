from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[datetime] = None

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = "anonymous"

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: datetime

class ChatSession(BaseModel):
    session_id: str
    user_id: str
    title: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatHistory(BaseModel):
    session_id: str
    messages: List[ChatMessage]

class SessionList(BaseModel):
    sessions: List[ChatSession]

class TitleUpdateRequest(BaseModel):
    session_id: str
    title: str
    user_id: str

# Document-related schemas
class DocumentUploadResponse(BaseModel):
    doc_id: str
    filename: str
    chunks: int
    total_characters: int
    status: str
    message: str

class DocumentDeleteResponse(BaseModel):
    doc_id: str
    chunks_deleted: int
    status: str
    message: str

class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    user_id: str
    file_type: str
    total_chunks: int

class DocumentListResponse(BaseModel):
    documents: List[DocumentInfo]
    total: int

class DocumentSearchRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    n_results: int = 5

class DocumentSearchResult(BaseModel):
    content: str
    metadata: Dict[str, Any]
    distance: Optional[float] = None

class DocumentSearchResponse(BaseModel):
    results: List[DocumentSearchResult]
    total: int