from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from groq import Groq
from datetime import datetime
import sys
import os
 
sys.path.append(os.path.dirname(__file__))

from utils.langchain_chromadb_memory import TravelLangChainMemory

 
load_dotenv()

app = FastAPI(title="Travel RAG Assistant", version="1.0.0")

 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

 
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

 
frontend_path = "frontend"
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
    print(f"✅ Frontend mounted from: {os.path.abspath(frontend_path)}")
else:
    print(f"❌ Frontend directory not found: {os.path.abspath(frontend_path)}")

 
memory_managers = {}
 
class ChatMessage(BaseModel):
    message: str
    user_id: Optional[str] = "default_user"

class ChatResponse(BaseModel):
    response: str
    context_used: Optional[List[str]] = []
    sources: Optional[List[str]] = []

@app.get("/")
async def root():
    
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
        
        
        if user_id not in memory_managers:
            memory_managers[user_id] = TravelLangChainMemory(groq_client, user_id)
        
        memory_manager = memory_managers[user_id]
        
       
        context_prompt = memory_manager.generate_context_prompt(user_message)
        
      
        context = memory_manager.get_conversation_context(user_message)
        recent_messages = context.get("recent_history", [])

       
        messages = [{"role": "system", "content": context_prompt}]
 
        for msg in recent_messages[-6:]:
            if hasattr(msg, 'type'):
                if msg.type == "human":
                    messages.append({"role": "user", "content": msg.content})
                elif msg.type == "ai":
                    messages.append({"role": "assistant", "content": msg.content})

    
        messages.append({"role": "user", "content": user_message})

        response = groq_client.chat.completions.create(
            messages=messages,
            model="llama-3.1-8b-instant",
            max_tokens=1200,
            temperature=0.8,
            top_p=0.9
        )
        
        ai_response = response.choices[0].message.content
       
        memory_manager.add_conversation(user_message, ai_response)
        
     
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
@app.post("/api/suggestions")
async def get_smart_suggestions(chat_message: ChatMessage):
    """Generate smart follow-up suggestions based on conversation"""
    try:
        user_id = chat_message.user_id
        last_message = chat_message.message
        
         
        if user_id in memory_managers:
            memory_manager = memory_managers[user_id]
            context = memory_manager.get_conversation_context(last_message)
            recent_history = context.get("recent_history", [])
            
           
            context_text = ""
            for msg in recent_history[-4:]:
                if hasattr(msg, 'type'):
                    if msg.type == "human":
                        context_text += f"User: {msg.content}\n"
                    elif msg.type == "ai":
                        context_text += f"Bot: {msg.content[:200]}\n"
        else:
            context_text = f"User: {last_message}"
        
        
        prompt = f"""Based on this travel conversation, suggest 3 short follow-up questions the user might ask next.

Conversation:
{context_text}

Generate 3 relevant follow-up questions (each max 6 words). Format as simple list:
1. [question]
2. [question]
3. [question]

Be specific to the destinations/topics discussed."""

        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            max_tokens=150,
            temperature=0.7
        )
        
        suggestions_text = response.choices[0].message.content.strip()
        
         
        suggestions = []
        for line in suggestions_text.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                
                suggestion = line.split('.', 1)[-1].strip()
                suggestion = suggestion.lstrip('- ').strip()
                if suggestion:
                    suggestions.append(suggestion)
        
        return {"suggestions": suggestions[:3]}
        
    except Exception as e:
        print(f"Suggestion error: {e}")
     
        return {"suggestions": ["Tell me more", "What about hotels?", "Budget tips?"]}
    
@app.get("/api/conversations/{user_id}")
async def get_conversation_history(user_id: str):
    """Get list of past conversations for sidebar"""
    try:
        if user_id in memory_managers:
            memory_manager = memory_managers[user_id]
            context = memory_manager.get_conversation_context("")
            recent_messages = context.get("recent_history", [])
            
            conversations = []
            if len(recent_messages) >= 2:
               
                for i, msg in enumerate(recent_messages):
                    if hasattr(msg, 'type') and msg.type == "human":
                        title = msg.content[:40] + "..." if len(msg.content) > 40 else msg.content
                        conversations.append({
                            "id": i,
                            "title": title,
                            "timestamp": datetime.now().isoformat(),
                            "message_count": len(recent_messages)
                        })
                        break
            
            return {"conversations": conversations[:5]}  
        
        return {"conversations": []}
        
    except Exception as e:
        print(f"History error: {e}")
        return {"conversations": []}
        
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