from typing import List, Dict, Optional
import json
from datetime import datetime

class TravelPromptManager:
    def __init__(self):
        self.system_prompt = self._create_system_prompt()
        self.travel_knowledge_base = self._load_travel_knowledge()
        
    def _create_system_prompt(self) -> str:
        """Create the core system prompt for travel assistant"""
        return """You are TravelBuddy, an expert AI travel assistant with deep knowledge of global destinations, travel planning, and tourism. Your personality is friendly, enthusiastic, and helpful.

CORE RESPONSIBILITIES:
• Provide personalized travel recommendations and planning advice
• Help with flight bookings, hotel suggestions, and itinerary creation
• Offer destination guides, local tips, and cultural insights
• Assist with budget planning and cost optimization
• Give packing advice and travel safety tips
• Answer visa, weather, and seasonal travel questions

RESPONSE STYLE:
• Be conversational, warm, and enthusiastic about travel
• Provide specific, actionable advice with details
• Include relevant tips and local insights
• Ask follow-up questions to better understand needs
• Use emojis sparingly but effectively (✈️🌍🏨)
• Keep responses concise but comprehensive

CONTEXT AWARENESS:
• Remember previous conversation details
• Build on past discussions and preferences
• Reference earlier recommendations when relevant
• Maintain conversation continuity

Always prioritize user safety, budget consciousness, and practical travel advice."""

    def _load_travel_knowledge(self) -> Dict:
        """Load travel knowledge base (can be expanded)"""
        return {
            "popular_destinations": {
                "europe": ["Paris", "Rome", "Barcelona", "Amsterdam", "Prague"],
                "asia": ["Tokyo", "Bangkok", "Singapore", "Seoul", "Kyoto"],
                "americas": ["New York", "San Francisco", "Toronto", "Mexico City"],
                "africa": ["Cape Town", "Marrakech", "Cairo"],
                "oceania": ["Sydney", "Melbourne", "Auckland"]
            },
            "travel_types": {
                "budget": "backpacking, hostels, local transport, street food",
                "luxury": "5-star hotels, private tours, fine dining, premium experiences",
                "family": "family-friendly activities, safe accommodations, kid-friendly restaurants",
                "solo": "safe destinations, social accommodations, group tours",
                "business": "business hotels, meeting facilities, efficient transport",
                "adventure": "outdoor activities, trekking, extreme sports"
            },
            "seasons": {
                "spring": "March-May, mild weather, fewer crowds, moderate prices",
                "summer": "June-August, peak season, highest prices, hot weather",
                "fall": "September-November, good weather, fewer crowds, moderate prices",
                "winter": "December-February, cold weather, lowest prices, winter activities"
            }
        }
    
    def create_travel_prompt(
        self, 
        user_message: str, 
        conversation_history: Optional[List[Dict]] = None,
        retrieved_context: Optional[List[str]] = None
    ) -> List[Dict[str, str]]:
        """
        Create a complete prompt for the travel assistant
        
        Args:
            user_message: Current user input
            conversation_history: Previous conversation messages
            retrieved_context: RAG-retrieved relevant context (we'll add this later)
        """
        
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Add conversation history for context
        if conversation_history:
            # Only include last few exchanges to manage token limits
            recent_history = conversation_history[-6:]  # Last 3 exchanges
            for msg in recent_history:
                if msg.get("role") in ["user", "assistant"]:
                    messages.append(msg)
        
        # Add retrieved context (RAG will populate this later)
        if retrieved_context:
            context_prompt = "RELEVANT CONTEXT from previous conversations:\n"
            for i, context in enumerate(retrieved_context[:3], 1):  # Max 3 contexts
                context_prompt += f"{i}. {context}\n"
            context_prompt += "\nUse this context to provide more personalized responses.\n"
            
            messages.append({
                "role": "system", 
                "content": context_prompt
            })
        
        # Add current user message
        messages.append({
            "role": "user", 
            "content": user_message
        })
        
        return messages
    
    def enhance_prompt_with_travel_context(self, user_message: str) -> str:
        """Add travel-specific context based on message content"""
        enhanced_message = user_message
        
        # Detect travel intent and add relevant context
        message_lower = user_message.lower()
        
        # Budget travel context
        if any(word in message_lower for word in ["budget", "cheap", "affordable", "backpack"]):
            enhanced_message += "\n\nContext: User is interested in budget-friendly travel options."
        
        # Luxury travel context
        elif any(word in message_lower for word in ["luxury", "premium", "5-star", "expensive"]):
            enhanced_message += "\n\nContext: User is interested in luxury travel experiences."
        
        # Family travel context
        elif any(word in message_lower for word in ["family", "kids", "children", "child"]):
            enhanced_message += "\n\nContext: User is planning family travel with children."
        
        # Solo travel context
        elif any(word in message_lower for word in ["solo", "alone", "single"]):
            enhanced_message += "\n\nContext: User is planning solo travel."
        
        # Adventure travel context
        elif any(word in message_lower for word in ["adventure", "hiking", "trekking", "outdoor"]):
            enhanced_message += "\n\nContext: User is interested in adventure and outdoor activities."
        
        return enhanced_message
    
    def generate_follow_up_questions(self, user_message: str) -> List[str]:
        """Generate relevant follow-up questions based on user input"""
        message_lower = user_message.lower()
        questions = []
        
        if "trip" in message_lower or "travel" in message_lower:
            questions.extend([
                "What's your approximate budget for this trip?",
                "How many days are you planning to travel?",
                "Are you traveling solo, with family, or friends?"
            ])
        
        if any(destination in message_lower for destination in ["paris", "tokyo", "rome", "london"]):
            questions.extend([
                "What time of year are you planning to visit?",
                "What type of experiences interest you most?",
                "Do you have any specific must-see attractions in mind?"
            ])
        
        if "hotel" in message_lower or "accommodation" in message_lower:
            questions.extend([
                "What's your preferred accommodation type?",
                "Which area of the city would you like to stay in?",
                "Any specific amenities you need?"
            ])
        
        return questions[:3]  # Return max 3 questions
    
    def create_travel_summary_prompt(self, conversation_history: List[Dict]) -> str:
        """Create a prompt to summarize travel preferences from conversation"""
        return f"""Based on this conversation history, summarize the user's travel preferences, destinations of interest, budget range, travel style, and any specific requirements mentioned:

Conversation: {json.dumps(conversation_history[-10:], indent=2)}

Provide a concise summary that can be used for future travel recommendations."""

# Test the prompt manager
if __name__ == "__main__":
    prompt_manager = TravelPromptManager()
    
    # Test basic prompt creation
    test_message = "I want to plan a budget trip to Japan for 10 days"
    test_history = [
        {"role": "user", "content": "Hi, I love adventure travel"},
        {"role": "assistant", "content": "Great! Adventure travel offers amazing experiences..."}
    ]
    
    prompt = prompt_manager.create_travel_prompt(test_message, test_history)
    print("Generated prompt:")
    for msg in prompt:
        print(f"{msg['role']}: {msg['content'][:100]}...")
    
    # Test follow-up questions
    questions = prompt_manager.generate_follow_up_questions(test_message)
    print(f"\nFollow-up questions: {questions}")