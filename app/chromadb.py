import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import hashlib
import os
from pathlib import Path
import PyPDF2
import docx
from io import BytesIO

class ChromaService:
    def __init__(self, persist_directory: str = "./chroma_db"):
        """Initialize ChromaDB client and collection"""
        self.persist_directory = persist_directory
        
        # Create persistent ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
    
    def _generate_doc_id(self, content: str, filename: str) -> str:
        """Generate unique document ID based on content and filename"""
        hash_input = f"{filename}:{content[:1000]}"
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    def _extract_text_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF file"""
        pdf_file = BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    
    def _extract_text_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX file"""
        doc_file = BytesIO(file_content)
        doc = docx.Document(doc_file)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    
    def _extract_text_from_txt(self, file_content: bytes) -> str:
        """Extract text from TXT file"""
        return file_content.decode('utf-8', errors='ignore').strip()
    
    def extract_text(self, file_content: bytes, filename: str) -> str:
        """Extract text based on file type"""
        file_extension = Path(filename).suffix.lower()
        
        if file_extension == '.pdf':
            return self._extract_text_from_pdf(file_content)
        elif file_extension == '.docx':
            return self._extract_text_from_docx(file_content)
        elif file_extension == '.txt':
            return self._extract_text_from_txt(file_content)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
    
    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap
        
        return chunks
    
    def add_document(
        self, 
        file_content: bytes, 
        filename: str, 
        user_id: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Process and add document to ChromaDB"""
        try:
            # Extract text from document
            text = self.extract_text(file_content, filename)
            
            if not text:
                raise ValueError("No text could be extracted from the document")
            
            # Generate document ID
            doc_id = self._generate_doc_id(text, filename)
            
            # Check if document already exists
            existing = self.collection.get(ids=[doc_id])
            if existing['ids']:
                raise ValueError("Document already exists in the database")
            
            # Chunk the text
            chunks = self._chunk_text(text)
            
            # Prepare data for ChromaDB
            chunk_ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
            chunk_metadata = []
            
            for i, chunk in enumerate(chunks):
                meta = {
                    "filename": filename,
                    "user_id": user_id,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "doc_id": doc_id,
                    "file_type": Path(filename).suffix.lower()
                }
                if metadata:
                    meta.update(metadata)
                chunk_metadata.append(meta)
            
            # Add to ChromaDB
            self.collection.add(
                ids=chunk_ids,
                documents=chunks,
                metadatas=chunk_metadata
            )
            
            return {
                "doc_id": doc_id,
                "filename": filename,
                "chunks": len(chunks),
                "total_characters": len(text),
                "status": "success"
            }
            
        except Exception as e:
            raise Exception(f"Error processing document: {str(e)}")
    
    def delete_document(self, doc_id: str, user_id: Optional[str] = None) -> Dict:
        """Delete document and all its chunks from ChromaDB"""
        try:
            # Get all chunks for this document
            results = self.collection.get(
                where={"doc_id": doc_id}
            )
            
            if not results['ids']:
                raise ValueError("Document not found")
            
            # Verify user ownership if user_id provided
            if user_id:
                chunk_user_id = results['metadatas'][0].get('user_id')
                if chunk_user_id != user_id:
                    raise PermissionError("You don't have permission to delete this document")
            
            # Delete all chunks
            self.collection.delete(
                ids=results['ids']
            )
            
            return {
                "doc_id": doc_id,
                "chunks_deleted": len(results['ids']),
                "status": "success"
            }
            
        except Exception as e:
            raise Exception(f"Error deleting document: {str(e)}")
    
    def search_documents(
        self, 
        query: str, 
        user_id: Optional[str] = None,
        n_results: int = 5
    ) -> List[Dict]:
        """Search for relevant document chunks"""
        try:
            where_filter = {"user_id": user_id} if user_id else None
            
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter
            )
            
            if not results['documents'][0]:
                return []
            
            # Format results
            formatted_results = []
            for i, doc in enumerate(results['documents'][0]):
                formatted_results.append({
                    "content": doc,
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None
                })
            
            return formatted_results
            
        except Exception as e:
            raise Exception(f"Error searching documents: {str(e)}")
    
    def list_documents(self, user_id: Optional[str] = None) -> List[Dict]:
        """List all documents for a user"""
        try:
            where_filter = {"user_id": user_id} if user_id else None
            
            results = self.collection.get(
                where=where_filter
            )
            
            # Group by doc_id to get unique documents
            documents = {}
            for i, metadata in enumerate(results['metadatas']):
                doc_id = metadata.get('doc_id')
                if doc_id not in documents:
                    documents[doc_id] = {
                        "doc_id": doc_id,
                        "filename": metadata.get('filename'),
                        "user_id": metadata.get('user_id'),
                        "file_type": metadata.get('file_type'),
                        "total_chunks": metadata.get('total_chunks', 0)
                    }
            
            return list(documents.values())
            
        except Exception as e:
            raise Exception(f"Error listing documents: {str(e)}")
    
    def get_context_for_query(
        self, 
        query: str, 
        user_id: Optional[str] = None,
        n_results: int = 3
    ) -> str:
        """Get relevant context for a query to use in RAG"""
        results = self.search_documents(query, user_id, n_results)
        
        if not results:
            return ""
        
        context = "Relevant information from your documents:\n\n"
        for i, result in enumerate(results, 1):
            context += f"[Source {i}: {result['metadata']['filename']}]\n"
            context += f"{result['content']}\n\n"
        
        return context
