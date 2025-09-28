import os
import asyncio
from typing import List, Dict, Optional
from groq import Groq
import json

class GroqClient:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.client = Groq(api_key=self.api_key)
        
        # Available models - you can switch these based on needs
        self.models = {
            "fast": "llama-3.1-8b-instant",      # Faster responses
            "smart": "llama-3.1-70b-versatile",  # Better quality
            "default": "llama-3.1-70b-versatile"
        }
        
        self.default_model = self.models["default"]
        
    def test_connection(self) -> bool:
        """Test if Groq API is accessible"""
        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": "Hello"}],
                model=self.models["fast"],
                max_tokens=10
            )
            return True
        except Exception as e:
            print(f"Groq connection test failed: {e}")
            return False
    
    async def get_chat_response(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> str:
        """
        Get chat response from Groq API
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (fast/smart/default)
            max_tokens: Maximum tokens in response
            temperature: Response randomness (0-1)
        """
        try:
            # Use default model if none specified
            selected_model = self.models.get(model, self.default_model)
            
            # Make API call
            response = self.client.chat.completions.create(
                messages=messages,
                model=selected_model,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
                stream=False
            )
            
            # Extract response content
            ai_response = response.choices[0].message.content.strip()
            
            return ai_response
            
        except Exception as e:
            print(f"Groq API error: {e}")
            return f"I'm having trouble connecting to my AI brain right now. Error: {str(e)}"
    
    async def get_streaming_response(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None
    ):
        """
        Get streaming response from Groq (for real-time chat)
        This will be useful for better user experience
        """
        try:
            selected_model = self.models.get(model, self.default_model)
            
            stream = self.client.chat.completions.create(
                messages=messages,
                model=selected_model,
                max_tokens=1024,
                temperature=0.7,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"Streaming error: {str(e)}"
    
    def get_available_models(self) -> Dict[str, str]:
        """Return available models"""
        return self.models
    
    def set_default_model(self, model_key: str):
        """Set default model"""
        if model_key in self.models:
            self.default_model = self.models[model_key]
        else:
            raise ValueError(f"Model {model_key} not available. Use: {list(self.models.keys())}")

# Test function
async def test_groq_client():
    """Test the Groq client functionality"""
    try:
        client = GroqClient()
        
        # Test basic connection
        print("Testing connection...")
        connected = client.test_connection()
        print(f"Connection: {'✅ Success' if connected else '❌ Failed'}")
        
        if connected:
            # Test chat response
            print("Testing chat response...")
            messages = [
                {"role": "system", "content": "You are a helpful travel assistant."},
                {"role": "user", "content": "Tell me about Paris in one sentence."}
            ]
            
            response = await client.get_chat_response(messages)
            print(f"Response: {response}")
            
    except Exception as e:
        print(f"Test failed: {e}")

# Run test if script is executed directly
if __name__ == "__main__":
    asyncio.run(test_groq_client())