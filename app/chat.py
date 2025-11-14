import google.generativeai as genai
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Chat:
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.system_prompt = """You are a helpful assistant."""
    
    def generate_response(
        self, 
        message: str, 
        conversation_history: List[Dict[str, str]] = None,
        context: Optional[str] = None
    ) -> str:
        """Generate a response using Gemini API with optional RAG context"""
        try:
            # Build conversation context with system prompt and history
            full_context = self.system_prompt + "\n\n"
            
            # Add RAG context if provided
            if context:
                full_context += f"Context from documents:\n{context}\n\n"
                full_context += "Please use the above context to answer the user's question when relevant.\n\n"
            
            if conversation_history:
                for msg in conversation_history:
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    if role == "user":
                        full_context += f"User: {content}\n"
                    elif role == "assistant":
                        full_context += f"Assistant: {content}\n"
            
            # Add current message
            full_prompt = full_context + f"User: {message}\nAssistant:"
            
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=1000,
                    temperature=0.7
                )
            )
            
            return response.text
            
        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}. Please try again."
    
    def get_conversation_context(self, messages: List[Dict[str, str]], max_messages: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation context for API calls"""
        return messages[-max_messages:] if len(messages) > max_messages else messages