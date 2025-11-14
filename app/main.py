from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from database import get_db
from schema import (
    ChatRequest, ChatResponse, ChatHistory, SessionList, ChatSession,
    DocumentUploadResponse, DocumentDeleteResponse, DocumentListResponse,
    DocumentSearchRequest, DocumentSearchResponse, TitleUpdateRequest
)
from chat import Chat
from chroma_manager import ChromaService
from utils import (
    create_chat_session, 
    save_message, 
    get_chat_history, 
    get_user_sessions,
    delete_chat_session,
    update_session_title
)

# Create FastAPI app
app = FastAPI(
    title="Aidbot Chat API",
    description="A chat API powered by AI",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize chat service
chat = Chat()

# Initialize document service
document_service = ChromaService()

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Chat API is running!", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    """Send a message and get AI response with optional RAG context"""
    try:
        session_id = request.session_id
        
        # Create new session if none provided
        if not session_id:
            session_id = create_chat_session(db, request.user_id)
        
        # Get conversation history
        history = get_chat_history(db, session_id)
        
        # Save user message
        save_message(db, session_id, "user", request.message)
        
        # Get relevant context from documents if available
        rag_context = None
        try:
            rag_context = document_service.get_context_for_query(
                query=request.message,
                user_id=request.user_id,
                n_results=3
            )
        except:
            # If RAG fails, continue without context
            pass
        
        # Generate AI response with or without RAG context
        ai_response = chat.generate_response(request.message, history, rag_context)
        
        # Save AI response
        save_message(db, session_id, "assistant", ai_response)
        
        return ChatResponse(
            response=ai_response,
            session_id=session_id,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat request: {str(e)}"
        )

@app.post("/sessions", response_model=dict)
async def create_session(user_id: str = "anonymous", title: str = "New Chat", db: Session = Depends(get_db)):
    """Create a new chat session"""
    try:
        session_id = create_chat_session(db, user_id, title)
        return {"session_id": session_id, "message": "Session created successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating session: {str(e)}"
        )

@app.get("/sessions/{user_id}", response_model=SessionList)
async def get_sessions(user_id: str, db: Session = Depends(get_db)):
    """Get all chat sessions for a user"""
    try:
        sessions = get_user_sessions(db, user_id)
        return SessionList(sessions=sessions)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving sessions: {str(e)}"
        )

@app.get("/chat/{session_id}/history", response_model=ChatHistory)
async def get_session_history(session_id: str, db: Session = Depends(get_db)):
    """Get chat history for a specific session"""
    try:
        messages = get_chat_history(db, session_id)
        chat_messages = [
            {"role": msg["role"], "content": msg["content"], "timestamp": datetime.utcnow()}
            for msg in messages
        ]
        return ChatHistory(session_id=session_id, messages=chat_messages)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving chat history: {str(e)}"
        )

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user_id: str, db: Session = Depends(get_db)):
    """Delete a chat session"""
    try:
        success = delete_chat_session(db, session_id, user_id)
        if success:
            return {"message": "Session deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or access denied"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting session: {str(e)}"
        )

@app.put("/sessions/update_title")
async def update_title(request: TitleUpdateRequest, db: Session = Depends(get_db)):
    """Update session title"""
    try:
        success = update_session_title(db, request.session_id, request.user_id, request.title)
        if success:
            return {"message": "Title updated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or access denied"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating title: {str(e)}"
        )

# ==================== Document Management Endpoints ====================

@app.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Form(default="anonymous")
):
    """
    Upload and process a document for RAG.
    Supported formats: PDF, DOCX, TXT
    """
    try:
        # Validate file type
        allowed_extensions = ['.pdf', '.docx', '.txt']
        file_extension = file.filename.split('.')[-1].lower()
        
        if f'.{file_extension}' not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        # Read file content
        file_content = await file.read()
        
        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file provided"
            )
        
        # Process and store document
        result = document_service.add_document(
            file_content=file_content,
            filename=file.filename,
            user_id=user_id
        )
        
        return DocumentUploadResponse(
            doc_id=result['doc_id'],
            filename=result['filename'],
            chunks=result['chunks'],
            total_characters=result['total_characters'],
            status=result['status'],
            message="Document uploaded and processed successfully"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading document: {str(e)}"
        )

@app.delete("/documents/{doc_id}", response_model=DocumentDeleteResponse)
async def delete_document(doc_id: str, user_id: Optional[str] = None):
    """
    Delete a document and all its chunks from the database.
    Optionally verify user ownership by providing user_id.
    """
    try:
        result = document_service.delete_document(doc_id, user_id)
        
        return DocumentDeleteResponse(
            doc_id=result['doc_id'],
            chunks_deleted=result['chunks_deleted'],
            status=result['status'],
            message="Document deleted successfully"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting document: {str(e)}"
        )

@app.get("/documents", response_model=DocumentListResponse)
async def list_documents(user_id: Optional[str] = None):
    """
    List all documents, optionally filtered by user_id.
    """
    try:
        documents = document_service.list_documents(user_id)
        
        return DocumentListResponse(
            documents=documents,
            total=len(documents)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing documents: {str(e)}"
        )

@app.post("/documents/search", response_model=DocumentSearchResponse)
async def search_documents(request: DocumentSearchRequest):
    """
    Search for relevant document chunks based on a query.
    """
    try:
        results = document_service.search_documents(
            query=request.query,
            user_id=request.user_id,
            n_results=request.n_results
        )
        
        return DocumentSearchResponse(
            results=results,
            total=len(results)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching documents: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)