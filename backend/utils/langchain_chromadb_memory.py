from langchain.memory import ConversationBufferWindowMemory, ConversationSummaryBufferMemory
from langchain.memory.vectorstore import VectorStoreRetrieverMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.llms.base import LLM
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
import os
import json
from datetime import datetime

class GroqLangChainLLM(LLM):
    """LangChain wrapper for Groq API"""
    
    def __init__(self, groq_client, model_name: str = "llama-3.1-8b-instant"):
        super().__init__()
        self.groq_client = groq_client
        self.model_name = model_name
    
    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        try:
            response = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model_name,
                max_tokens=200,  # Short responses for summaries
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Summary generation failed: {e}"
    
    @property
    def _llm_type(self) -> str:
        return "groq_langchain"

class TravelLangChainMemory:
    """
    Professional travel memory system using LangChain + ChromaDB
    - Industry standard LangChain framework
    - Free ChromaDB vector database
    - Persistent cross-session memory
    - Semantic conversation search
    """
    
    def __init__(self, groq_client, user_id: str):
        self.user_id = user_id
        self.groq_client = groq_client
        
        print(f"🚀 Initializing LangChain + ChromaDB memory for {user_id}")
        
        # Initialize LangChain LLM wrapper
        self.llm = GroqLangChainLLM(groq_client)
        
        # Initialize free embedding model
        try:
            self.embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
            print("✅ SentenceTransformer embeddings loaded")
        except Exception as e:
            print(f"❌ Error loading embeddings: {e}")
            self.embeddings = None
            return
        
        # Setup ChromaDB persistent storage
        self.persist_directory = f"./chroma_db_{user_id}"
        self.collection_name = f"travel_memory_{user_id}"
        
        try:
            # Initialize ChromaDB client
            self.chroma_client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Create Chroma vector store for LangChain
            self.vectorstore = Chroma(
                client=self.chroma_client,
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
            
            print("✅ ChromaDB vector store initialized")
            
        except Exception as e:
            print(f"❌ Error initializing ChromaDB: {e}")
            self.vectorstore = None
            return
        
        # Initialize LangChain memory types
        self._init_langchain_memories()
        
        # Load existing conversation history
        self._load_existing_conversations()
        
        # User preferences
        self.preferences_file = f"preferences_{user_id}.json"
        self.user_preferences = self._load_preferences()
        
        print("✅ LangChain memory system ready!")
    
    def _init_langchain_memories(self):
        """Initialize different LangChain memory types"""
        
        # 1. Buffer Window Memory - keeps last N exchanges
        self.buffer_memory = ConversationBufferWindowMemory(
            k=6,  # Keep last 6 messages (3 exchanges)
            return_messages=True,
            memory_key="chat_history"
        )
        
        # 2. Summary Buffer Memory - summarizes old conversations
        self.summary_memory = ConversationSummaryBufferMemory(
            llm=self.llm,
            max_token_limit=800,  # Summarize when context gets too long
            return_messages=True,
            memory_key="summary"
        )
        
        # 3. Vector Store Retriever Memory - semantic search through all conversations
        if self.vectorstore:
            self.vector_memory = VectorStoreRetrieverMemory(
                vectorstore=self.vectorstore,
                memory_key="relevant_history",
                return_docs=True
            )
        else:
            self.vector_memory = None
            print("⚠️ Vector memory not available - ChromaDB initialization failed")
    
    def add_conversation(self, user_message: str, ai_response: str):
        """Add conversation to all LangChain memory types"""
        
        try:
            # Add to buffer memory
            self.buffer_memory.chat_memory.add_user_message(user_message)
            self.buffer_memory.chat_memory.add_ai_message(ai_response)
            
            # Add to summary memory
            self.summary_memory.chat_memory.add_user_message(user_message)
            self.summary_memory.chat_memory.add_ai_message(ai_response)
            
            # Add to vector memory for semantic search
            if self.vector_memory:
                conversation_text = f"User: {user_message}\nAssistant: {ai_response}"
                self.vector_memory.save_context(
                    {"input": user_message},
                    {"output": ai_response}
                )
            
            # Extract and update travel preferences
            self._update_travel_preferences(user_message, ai_response)
            
            print(f"💾 Saved conversation to LangChain memories")
            
        except Exception as e:
            print(f"❌ Error saving conversation: {e}")
    
    def get_conversation_context(self, current_message: str) -> Dict[str, Any]:
        """Get comprehensive context using LangChain memories"""
        
        context = {}
        
        try:
            # Get recent conversation from buffer memory
            buffer_vars = self.buffer_memory.load_memory_variables({})
            context["recent_history"] = buffer_vars.get("chat_history", [])
            
            # Get conversation summary
            summary_vars = self.summary_memory.load_memory_variables({})
            context["conversation_summary"] = summary_vars.get("summary", "")
            
            # Get semantically similar past conversations
            if self.vector_memory:
                try:
                    vector_vars = self.vector_memory.load_memory_variables({"prompt": current_message})
                    context["relevant_history"] = vector_vars.get("relevant_history", "")
                except Exception as e:
                    print(f"⚠️ Vector search failed: {e}")
                    context["relevant_history"] = ""
            
            # Add user preferences
            context["user_preferences"] = self.user_preferences
            
            # Add memory stats
            context["memory_stats"] = self._get_memory_stats()
            
        except Exception as e:
            print(f"❌ Error getting context: {e}")
            context = {"error": str(e)}
        
        return context
    
    def generate_context_prompt(self, current_message: str) -> str:
        """Generate context-aware prompt using LangChain memory"""
        
        context = self.get_conversation_context(current_message)
        
        prompt = """You are a professional travel assistant with access to conversation history and user preferences.

RESPONSE FORMATTING:
- Use clear paragraphs with proper spacing
- Use bullet points for lists and recommendations
- Bold important information with **text**
- Structure responses logically (overview → details → recommendations)
- Be conversational but professional
- Use line breaks between different topics

TRAVEL EXPERTISE:
- Provide detailed trip planning with specific recommendations
- Include practical information (costs, timing, logistics)
- Consider user's budget, style, and preferences
- Offer alternatives and options"""
        
        # Add user preferences if available
        preferences = context.get("user_preferences", {})
        if preferences.get("destinations_interested"):
            prompt += f"\n\nUSER'S TRAVEL PROFILE:"
            prompt += f"\n• Previously discussed destinations: {', '.join(preferences['destinations_interested'][:5])}"
            
            if preferences.get("budget_preference"):
                prompt += f"\n• Budget preference: {preferences['budget_preference']}"
            
            if preferences.get("travel_style"):
                prompt += f"\n• Travel style: {preferences['travel_style']}"
        
        # Add conversation summary if available
        summary = context.get("conversation_summary", "")
        if summary and len(summary.strip()) > 10:
            prompt += f"\n\nCONVERSATION SUMMARY:\n{summary}"
        
        # Add recent conversation history
        recent_history = context.get("recent_history", [])
        if recent_history and len(recent_history) > 0:
            prompt += f"\n\nRECENT CONVERSATION:"
            for msg in recent_history[-4:]:  # Last 4 messages
                if isinstance(msg, HumanMessage):
                    prompt += f"\nUser: {msg.content}"
                elif isinstance(msg, AIMessage):
                    prompt += f"\nAssistant: {msg.content[:150]}..."
        
        # Add relevant past conversations if available
        relevant_history = context.get("relevant_history", "")
        if relevant_history and len(str(relevant_history).strip()) > 10:
            prompt += f"\n\nRELEVANT PAST DISCUSSIONS:\n{relevant_history}"
        
        prompt += f"\n\nCURRENT REQUEST: {current_message}\n\nProvide a helpful, well-formatted response considering the user's history and preferences:"
        
        return prompt
    
    def _update_travel_preferences(self, user_message: str, ai_response: str):
        """Extract and update travel preferences from conversation"""
        
        combined_text = f"{user_message} {ai_response}".lower()
        
        # Extract destinations
        destinations = []
        destination_keywords = [
            "paris", "london", "tokyo", "new york", "rome", "barcelona", "amsterdam",
            "thailand", "japan", "italy", "spain", "france", "germany", "australia",
            "india", "china", "brazil", "mexico", "canada", "dubai", "singapore"
        ]
        
        for dest in destination_keywords:
            if dest in combined_text:
                formatted_dest = dest.title()
                if formatted_dest not in self.user_preferences["destinations_interested"]:
                    self.user_preferences["destinations_interested"].append(formatted_dest)
        
        # Extract budget preference
        if any(word in combined_text for word in ["budget", "cheap", "affordable"]):
            self.user_preferences["budget_preference"] = "budget"
        elif any(word in combined_text for word in ["luxury", "premium", "expensive"]):
            self.user_preferences["budget_preference"] = "luxury"
        elif any(word in combined_text for word in ["mid-range", "moderate"]):
            self.user_preferences["budget_preference"] = "mid-range"
        
        # Extract travel style
        if any(word in combined_text for word in ["solo", "alone"]):
            self.user_preferences["travel_style"] = "solo"
        elif any(word in combined_text for word in ["family", "kids", "children"]):
            self.user_preferences["travel_style"] = "family"
        elif any(word in combined_text for word in ["couple", "romantic"]):
            self.user_preferences["travel_style"] = "couple"
        elif any(word in combined_text for word in ["adventure", "hiking", "trekking"]):
            self.user_preferences["travel_style"] = "adventure"
        
        # Update timestamp
        self.user_preferences["last_updated"] = datetime.now().isoformat()
        
        # Save preferences
        self._save_preferences()
    
    def _load_preferences(self) -> Dict[str, Any]:
        """Load user preferences"""
        default_prefs = {
            "destinations_interested": [],
            "budget_preference": "",
            "travel_style": "",
            "last_updated": datetime.now().isoformat(),
            "total_conversations": 0
        }
        
        try:
            if os.path.exists(self.preferences_file):
                with open(self.preferences_file, 'r', encoding='utf-8') as f:
                    prefs = json.load(f)
                    default_prefs.update(prefs)
        except Exception as e:
            print(f"⚠️ Error loading preferences: {e}")
        
        return default_prefs
    
    def _save_preferences(self):
        """Save user preferences"""
        try:
            with open(self.preferences_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_preferences, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Error saving preferences: {e}")
    
    def _load_existing_conversations(self):
        """Load any existing conversations into memory"""
        try:
            # Check if we have existing data in ChromaDB
            if self.vectorstore:
                docs = self.vectorstore.similarity_search("travel", k=1)
                if docs:
                    print(f"✅ Found {len(docs)} existing conversations in ChromaDB")
        except Exception as e:
            print(f"⚠️ Could not load existing conversations: {e}")
    
    def _get_memory_stats(self) -> Dict[str, int]:
        """Get memory statistics"""
        stats = {
            "buffer_messages": len(self.buffer_memory.chat_memory.messages),
            "destinations_discussed": len(self.user_preferences["destinations_interested"]),
            "vector_documents": 0
        }
        
        try:
            if self.vectorstore:
                # Try to get count of documents in vector store
                docs = self.vectorstore.similarity_search("", k=100)
                stats["vector_documents"] = len(docs)
        except:
            pass
        
        return stats
    
    def clear_memory(self):
        """Clear all memory"""
        try:
            # Clear LangChain memories
            self.buffer_memory.clear()
            self.summary_memory.clear()
            
            # Clear vector store
            if self.vectorstore:
                # Delete the collection and recreate
                try:
                    self.chroma_client.delete_collection(self.collection_name)
                    # Recreate collection
                    self.vectorstore = Chroma(
                        client=self.chroma_client,
                        collection_name=self.collection_name,
                        embedding_function=self.embeddings,
                        persist_directory=self.persist_directory
                    )
                except Exception as e:
                    print(f"⚠️ Error clearing vector store: {e}")
            
            # Clear preferences
            self.user_preferences = {
                "destinations_interested": [],
                "budget_preference": "",
                "travel_style": "",
                "last_updated": datetime.now().isoformat(),
                "total_conversations": 0
            }
            self._save_preferences()
            
            print("🗑️ Cleared all LangChain memory")
            
        except Exception as e:
            print(f"❌ Error clearing memory: {e}")

# Test function
def test_langchain_memory():
    """Test the LangChain + ChromaDB memory system"""
    print("🧪 Testing LangChain + ChromaDB Memory System")
    print("This system provides:")
    print("• ConversationBufferWindowMemory - Recent conversation context")
    print("• ConversationSummaryBufferMemory - Automatic conversation summarization")  
    print("• VectorStoreRetrieverMemory - Semantic search through all conversations")
    print("• ChromaDB - Free persistent vector storage")
    print("• SentenceTransformers - Free embedding generation")
    print("• Cross-session memory - Remember conversations from previous days")

if __name__ == "__main__":
    test_langchain_memory()