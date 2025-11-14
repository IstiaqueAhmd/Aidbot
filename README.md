# simple chatbot with memory

# Document Management API with RAG

This API provides document upload, storage, and retrieval functionality using ChromaDB for Retrieval-Augmented Generation (RAG).

## Features

- **Document Upload**: Upload PDF, DOCX, or TXT files
- **Text Extraction**: Automatic text extraction from uploaded documents
- **Text Chunking**: Smart text chunking with overlap for better context
- **Vector Storage**: Store document chunks in ChromaDB with embeddings
- **Document Search**: Semantic search across uploaded documents
- **RAG Integration**: Automatically use document context in chat responses
- **Document Management**: List and delete documents

## API Endpoints

### 1. Upload Document

**Endpoint**: `POST /documents/upload`

**Description**: Upload and process a document for RAG. The document will be:
- Text extracted based on file type
- Split into chunks with overlap
- Stored in ChromaDB with embeddings
- Associated with a user ID

**Request**:
```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/document.pdf" \
  -F "user_id=user123"
```

**Response**:
```json
{
  "doc_id": "abc123...",
  "filename": "document.pdf",
  "chunks": 15,
  "total_characters": 12500,
  "status": "success",
  "message": "Document uploaded and processed successfully"
}
```

**Supported File Types**:
- `.pdf` - PDF documents
- `.docx` - Microsoft Word documents
- `.txt` - Plain text files

### 2. Delete Document

**Endpoint**: `DELETE /documents/{doc_id}`

**Description**: Delete a document and all its chunks from the database.

**Request**:
```bash
curl -X DELETE "http://localhost:8000/documents/abc123?user_id=user123"
```

**Response**:
```json
{
  "doc_id": "abc123...",
  "chunks_deleted": 15,
  "status": "success",
  "message": "Document deleted successfully"
}
```

### 3. List Documents

**Endpoint**: `GET /documents`

**Description**: List all documents, optionally filtered by user.

**Request**:
```bash
# List all documents
curl "http://localhost:8000/documents"

# List documents for a specific user
curl "http://localhost:8000/documents?user_id=user123"
```

**Response**:
```json
{
  "documents": [
    {
      "doc_id": "abc123...",
      "filename": "document.pdf",
      "user_id": "user123",
      "file_type": ".pdf",
      "total_chunks": 15
    }
  ],
  "total": 1
}
```

### 4. Search Documents

**Endpoint**: `POST /documents/search`

**Description**: Search for relevant document chunks based on a query using semantic search.

**Request**:
```bash
curl -X POST "http://localhost:8000/documents/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?",
    "user_id": "user123",
    "n_results": 5
  }'
```

**Response**:
```json
{
  "results": [
    {
      "content": "Machine learning is a subset of artificial intelligence...",
      "metadata": {
        "filename": "ml_intro.pdf",
        "user_id": "user123",
        "chunk_index": 2,
        "total_chunks": 15,
        "doc_id": "abc123...",
        "file_type": ".pdf"
      },
      "distance": 0.234
    }
  ],
  "total": 5
}
```

## RAG Integration with Chat

The chat endpoint automatically integrates with the document store. When you send a message, the system:

1. Searches for relevant document chunks based on your query
2. Retrieves the top 3 most relevant chunks
3. Includes them as context for the AI model
4. Generates a response using both conversation history and document context

**Example Chat with RAG**:
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What does the document say about machine learning?",
    "user_id": "user123",
    "session_id": "session456"
  }'
```

The AI will automatically use relevant content from your uploaded documents to provide more accurate and contextual responses.

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

2. Required packages for document processing:
- `chromadb` - Vector database
- `PyPDF2` - PDF text extraction
- `python-docx` - DOCX text extraction
- `python-multipart` - File upload support

## Configuration

Documents are stored in a local ChromaDB instance. By default, the database is created in `./chroma_db` directory.

## Text Processing

### Chunking Strategy
- **Chunk Size**: 1000 characters
- **Overlap**: 200 characters
- **Purpose**: Maintains context across chunks while keeping manageable sizes

### Supported Operations
- PDF text extraction (including multi-page documents)
- DOCX paragraph extraction
- Plain text file processing
- Automatic encoding detection

## Error Handling

The API provides detailed error messages for:
- Unsupported file types
- Empty files
- Duplicate documents
- Permission errors
- Processing errors

## Security Considerations

1. **User Isolation**: Documents are associated with user IDs
2. **Permission Checks**: Delete operations verify ownership
3. **File Type Validation**: Only allowed file types are processed
4. **Content Validation**: Empty or corrupted files are rejected

## Usage Example

```python
import requests

# Upload a document
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/documents/upload',
        files={'file': f},
        data={'user_id': 'user123'}
    )
    doc_id = response.json()['doc_id']

# Chat with RAG context
response = requests.post(
    'http://localhost:8000/chat',
    json={
        'message': 'Summarize the document',
        'user_id': 'user123'
    }
)
print(response.json()['response'])

# Delete document
requests.delete(
    f'http://localhost:8000/documents/{doc_id}',
    params={'user_id': 'user123'}
)
```

## Performance Notes

- Vector embeddings are generated automatically by ChromaDB
- Search uses cosine similarity for semantic matching
- Documents are persisted to disk for durability
- Chunking is optimized for context preservation

## Future Enhancements

Potential improvements:
- Multiple collection support
- Custom chunking strategies
- OCR for scanned documents
- Image extraction from PDFs
- Metadata filtering in search
- Document versioning
