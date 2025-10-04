# 🌍 Travel Buddy AI - RAG-Powered Travel Assistant

An intelligent travel planning chatbot featuring multi-layer memory system, context-aware responses, and AI-generated suggestions using Retrieval Augmented Generation (RAG) architecture.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![LangChain](https://img.shields.io/badge/LangChain-0.1+-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

- **🧠 Multi-Layer Memory System**
  - Short-term: LangChain BufferWindowMemory (last 6 messages)
  - Long-term: ChromaDB vector database for semantic search
  - User preferences: JSON-based persistent storage

- **🤖 RAG Architecture**
  - Retrieves relevant conversation context before generating responses
  - Integrates user preferences and conversation history
  - Context-aware responses using Groq's LLaMA 3.1 8B model

- **💡 Smart Suggestions**
  - AI-generated follow-up questions based on conversation context
  - Dynamic and contextually relevant
  - One-click interaction

- **📊 Memory Dashboard**
  - Real-time conversation statistics
  - User preference tracking
  - Chat history sidebar

- **🎨 Modern UI**
  - Responsive design with orange-themed interface
  - Collapsible sidebar
  - Typing indicators and smooth animations

## 🏗️ Architecture

User Query → Frontend → FastAPI Backend → LangChain Memory Manager
↓                                         ↓
Display Response ← Groq API ← Context-Aware Prompt
↓
Smart Suggestions Generation


## 🛠️ Tech Stack

**Backend:** FastAPI, LangChain, Groq API, ChromaDB, SentenceTransformers  
**Frontend:** Vanilla JavaScript, HTML5/CSS3  
**Memory:** ConversationBufferWindowMemory, VectorStoreRetrieverMemory, JSON

## 🚀 Quick Start
```bash
# Clone
git clone https://github.com/yourusername/travel-rag-assistant.git
cd travel-rag-assistant

# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure
echo "GROQ_API_KEY=your_key_here" > .env

# Run
cd backend
python main.py

# Access: http://localhost:8003