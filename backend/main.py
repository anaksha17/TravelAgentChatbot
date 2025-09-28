from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from groq import Groq

import sys
import os
# Add current directory to Python path
sys.path.append(os.path.dirname(__file__))

from utils.langchain_chromadb_memory import TravelLangChainMemory

# Load environment variables
load_dotenv()

app = FastAPI(title="Travel RAG Assistant", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Groq
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Check if frontend directory exists and mount static files
frontend_path = "frontend"
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
    print(f"✅ Frontend mounted from: {os.path.abspath(frontend_path)}")
else:
    print(f"❌ Frontend directory not found: {os.path.abspath(frontend_path)}")

# LangChain + ChromaDB memory managers for each user
memory_managers = {}

# Request/Response models
class ChatMessage(BaseModel):
    message: str
    user_id: Optional[str] = "default_user"

class ChatResponse(BaseModel):
    response: str
    context_used: Optional[List[str]] = []
    sources: Optional[List[str]] = []

@app.get("/")
async def root():
    # Try to serve index.html if it exists
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {
            "message": "Travel RAG Assistant API is running!", 
            "frontend_available": os.path.exists(frontend_path),
            "frontend_path": os.path.abspath(frontend_path),
            "memory_system": "LangChain + ChromaDB"
        }

@app.get("/health")
async def health_check():
    try:
        # Test Groq connection
        test_response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": "Hi"}],
            model="llama-3.1-8b-instant",
            max_tokens=5
        )
        groq_working = True
    except:
        groq_working = False
    
    return {
        "status": "healthy",
        "groq_connected": groq_working,
        "frontend_available": os.path.exists(frontend_path),
        "memory_system": "LangChain + ChromaDB",
        "active_users": len(memory_managers)
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(chat_message: ChatMessage):
    try:
        user_id = chat_message.user_id
        user_message = chat_message.message
        
        # Get or create LangChain memory manager for user
        if user_id not in memory_managers:
            memory_managers[user_id] = TravelLangChainMemory(groq_client, user_id)
        
        memory_manager = memory_managers[user_id]
        
        # Generate context-aware prompt using LangChain + ChromaDB
        context_prompt = memory_manager.generate_context_prompt(user_message)
        
        # Get AI response with professional formatting
        messages = [
            {"role": "system", "content": context_prompt},
            {"role": "user", "content": user_message}
        ]
        
        response = groq_client.chat.completions.create(
            messages=messages,
            model="llama-3.1-8b-instant",
            max_tokens=1200,
            temperature=0.8,
            top_p=0.9
        )
        
        ai_response = response.choices[0].message.content
        
        # Add to LangChain memory system
        memory_manager.add_conversation(user_message, ai_response)
        
        # Get memory stats for frontend
        context = memory_manager.get_conversation_context(user_message)
        memory_stats = context.get("memory_stats", {})
        
        return ChatResponse(
            response=ai_response,
            context_used=[
                f"langchain_memory:{memory_stats.get('buffer_messages', 0)}",
                f"vector_search:{memory_stats.get('vector_documents', 0)}",
                f"preferences:{memory_stats.get('destinations_discussed', 0)}"
            ],
            sources=["llama-3.1-8b", "langchain", "chromadb", "sentence-transformers"]
        )
        
    except Exception as e:
        print(f"Chat error: {e}")
        # Fallback to simple response if memory fails
        try:
            simple_response = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a helpful travel assistant. Format responses clearly with proper spacing and use bullet points for lists."},
                    {"role": "user", "content": user_message}
                ],
                model="llama-3.1-8b-instant",
                max_tokens=1200,
                temperature=0.8
            )
            return ChatResponse(
                response=simple_response.choices[0].message.content,
                context_used=["fallback_mode"],
                sources=["llama-3.1-8b"]
            )
        except Exception as fallback_error:
            raise HTTPException(status_code=500, detail=f"Chat system error: {str(fallback_error)}")

@app.get("/api/memory/{user_id}")
async def get_memory_stats(user_id: str):
    """Get LangChain memory statistics for a user"""
    try:
        if user_id in memory_managers:
            memory_manager = memory_managers[user_id]
            context = memory_manager.get_conversation_context("")
            
            return {
                "stats": context.get("memory_stats", {}),
                "user_preferences": context.get("user_preferences", {}),
                "has_conversation_summary": bool(context.get("conversation_summary", "").strip()),
                "recent_messages": len(context.get("recent_history", [])),
                "memory_type": "langchain_chromadb"
            }
        else:
            return {
                "stats": {"buffer_messages": 0, "vector_documents": 0, "destinations_discussed": 0},
                "user_preferences": {},
                "memory_type": "none"
            }
    except Exception as e:
        return {"error": f"Memory stats error: {str(e)}"}

@app.delete("/api/memory/{user_id}")
async def clear_user_memory(user_id: str):
    """Clear LangChain memory for a user"""
    try:
        if user_id in memory_managers:
            memory_managers[user_id].clear_memory()
            del memory_managers[user_id]
        
        return {"message": f"LangChain memory cleared for user {user_id}"}
    except Exception as e:
        return {"error": f"Memory clear error: {str(e)}"}

@app.get("/api/stats")
async def get_api_stats():
    """Get overall API statistics"""
    total_users = len(memory_managers)
    
    memory_stats = {}
    for user_id, manager in memory_managers.items():
        try:
            context = manager.get_conversation_context("")
            memory_stats[user_id] = context.get("memory_stats", {})
        except:
            pass
    
    return {
        "total_active_users": total_users,
        "memory_system": "LangChain + ChromaDB",
        "per_user_stats": memory_stats
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Travel RAG Assistant with LangChain + ChromaDB...")
    print("📍 API will be available at: http://localhost:8003")
    print("🌐 Frontend will be available at: http://localhost:8003/")
    print("📁 Frontend directory exists:", os.path.exists("frontend"))
    print("🧠 Memory system: LangChain + ChromaDB")
    print("🔗 Vector database: ChromaDB (free)")
    print("🤖 Embeddings: SentenceTransformers (free)")
    
    uvicorn.run(app, host="127.0.0.1", port=8003, reload=False)