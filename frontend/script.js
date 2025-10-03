// Global variables
let userId = 'user_' + Math.random().toString(36).substr(2, 9);
let isTyping = false;

// DOM elements
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const typingIndicator = document.getElementById('typingIndicator');
const connectionStatus = document.getElementById('connectionStatus');
const contextPanel = document.getElementById('contextPanel');
const contextContent = document.getElementById('contextContent');
const quickSuggestions = document.getElementById('quickSuggestions');

// API base URL
const API_BASE = window.location.origin;

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    checkApiStatus();
});

function initializeApp() {
    // Enable send button when input has text
    messageInput.addEventListener('input', function() {
        sendButton.disabled = this.value.trim() === '';
        updateCharCounter();
    });
    
    // Send message on Enter key
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey && !sendButton.disabled) {
            e.preventDefault();
            sendMessage();
        }
    });
}

function setupEventListeners() {
    // Character counter
    messageInput.addEventListener('input', updateCharCounter);
    
    // Focus input on page load
    messageInput.focus();
}

function updateCharCounter() {
    const charCounter = document.querySelector('.char-counter');
    if (charCounter) {
        const currentLength = messageInput.value.length;
        charCounter.textContent = `${currentLength}/500`;
        
        if (currentLength > 450) {
            charCounter.style.color = '#ff9800';
        } else if (currentLength > 400) {
            charCounter.style.color = '#f44336';
        } else {
            charCounter.style.color = '#666';
        }
    }
}

async function checkApiStatus() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();
        
        if (data.status === 'healthy') {
            connectionStatus.textContent = '🟢 Connected';
            connectionStatus.style.background = 'rgba(76, 175, 80, 0.2)';
        } else {
            connectionStatus.textContent = '🟡 Partial';
            connectionStatus.style.background = 'rgba(255, 152, 0, 0.2)';
        }
    } catch (error) {
        connectionStatus.textContent = '🔴 Offline';
        connectionStatus.style.background = 'rgba(244, 67, 54, 0.2)';
        console.error('API Status check failed:', error);
    }
}

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message || isTyping) return;
    
    // Disable input and show user message
    setInputEnabled(false);
    addMessage(message, 'user');
    messageInput.value = '';
    updateCharCounter();
    
    // Show typing indicator
    showTypingIndicator();
    
    try {
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                user_id: userId
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Hide typing indicator and show response
hideTypingIndicator();
addMessage(data.response, 'assistant', data.context_used, data.sources);

// Add smart suggestions after bot response
addSmartSuggestions(data.response);

// Update memory stats in sidebar
updateMemoryStats();
updateChatHistory();
        
    } catch (error) {
        console.error('Error sending message:', error);
        hideTypingIndicator();
        addMessage(
            'I encountered an error while processing your request. Please try again.',
            'assistant'
        );
    } finally {
        setInputEnabled(true);
        messageInput.focus();
    }
}
// AI-Powered Smart Suggestions
async function addSmartSuggestions(lastBotMessage) {
    // Remove old suggestions
    const oldSuggestions = document.querySelector('.smart-suggestions');
    if (oldSuggestions) oldSuggestions.remove();
    
    try {
        // Get AI-generated suggestions from backend
        const response = await fetch(`${API_BASE}/api/suggestions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: lastBotMessage,
                user_id: userId
            })
        });
        
        const data = await response.json();
        const suggestions = data.suggestions || [];
        
        if (suggestions.length > 0) {
            const suggestionsDiv = document.createElement('div');
            suggestionsDiv.className = 'smart-suggestions';
            suggestionsDiv.innerHTML = '<p class="suggestion-label">💡 You might want to ask:</p>';
            
            const buttonsContainer = document.createElement('div');
            buttonsContainer.className = 'suggestion-buttons-container';
            
            suggestions.forEach(suggestion => {
                const btn = document.createElement('button');
                btn.className = 'suggestion-btn-smart';
                btn.textContent = suggestion;
                btn.onclick = () => {
                    messageInput.value = suggestion;
                    sendMessage();
                };
                buttonsContainer.appendChild(btn);
            });
            
            suggestionsDiv.appendChild(buttonsContainer);
            chatMessages.appendChild(suggestionsDiv);
            scrollToBottom();
        }
    } catch (error) {
        console.error('Error getting suggestions:', error);
    }
}

async function updateMemoryStats() {
    try {
        const response = await fetch(`${API_BASE}/api/memory/${userId}`);
        const data = await response.json();
        
        // Update conversation count
        const conversationCount = document.getElementById('conversationCount');
        if (conversationCount) {
            conversationCount.textContent = data.stats.total_conversations || 0;
        }
        
        // Update context count
        const contextCount = document.getElementById('contextCount');
        if (contextCount) {
            contextCount.textContent = data.stats.preferences_tracked || 0;
        }
        
        // Update context items
        const contextItems = document.getElementById('contextItems');
        if (contextItems && data.travel_preferences) {
            updateContextItems(data.travel_preferences, data.recent_topics);
        }
        
    } catch (error) {
        console.error('Error updating memory stats:', error);
    }
}
async function updateChatHistory() {
    try {
        const response = await fetch(`${API_BASE}/api/conversations/${userId}`);
        const data = await response.json();
        
        const chatHistory = document.getElementById('chatHistory');
        if (!chatHistory) return;
        
        const conversations = data.conversations || [];
        
        if (conversations.length === 0) {
            chatHistory.innerHTML = '<p class="no-context">No previous chats</p>';
            return;
        }
        
        let html = '';
        conversations.forEach(conv => {
            const date = new Date(conv.timestamp);
            const timeStr = date.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
            
            html += `
                <div class="chat-history-item" onclick="loadConversation('${conv.id}')">
                    <div class="chat-title">${conv.title}</div>
                    <div class="chat-meta">
                        <span>💬 ${conv.message_count} messages</span>
                        <span>${timeStr}</span>
                    </div>
                </div>
            `;
        });
        
        chatHistory.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading chat history:', error);
    }
}

function loadConversation(convId) {
    // For now just scroll to top to show existing conversation
    chatMessages.scrollTop = 0;
    // In future, you could load specific conversation from database
}

function updateContextItems(preferences, recentTopics) {
    const contextItems = document.getElementById('contextItems');
    if (!contextItems) return;
    
    let html = '';
    
    // Show travel preferences
    if (preferences.destinations_mentioned && preferences.destinations_mentioned.length > 0) {
        html += `<div class="context-item">
            <h5>Destinations Discussed</h5>
            <p>${preferences.destinations_mentioned.join(', ')}</p>
        </div>`;
    }
    
    if (preferences.budget_preferences && preferences.budget_preferences.length > 0) {
        html += `<div class="context-item">
            <h5>Budget Preferences</h5>
            <p>${preferences.budget_preferences.join(', ')}</p>
        </div>`;
    }
    
    if (preferences.travel_style && preferences.travel_style.length > 0) {
        html += `<div class="context-item">
            <h5>Travel Style</h5>
            <p>${preferences.travel_style.join(', ')}</p>
        </div>`;
    }
    
    // Show recent topics
    if (recentTopics && recentTopics.length > 0) {
        html += `<div class="context-item">
            <h5>Recent Topics</h5>`;
        recentTopics.forEach(topic => {
            html += `<p class="topic-item">${topic}</p>`;
        });
        html += `</div>`;
    }
    
    if (html === '') {
        html = '<p class="no-context">Start a conversation to see context</p>';
    }
    
    contextItems.innerHTML = html;
}

async function clearConversation() {
    try {
        const response = await fetch(`${API_BASE}/api/memory/${userId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            // Clear the chat messages (keep welcome message)
            const messages = chatMessages.querySelectorAll('.message');
            messages.forEach((msg, index) => {
                if (index > 0) { // Keep first welcome message
                    msg.remove();
                }
            });
            
            // Reset memory stats
            updateMemoryStats();
            
            // Show confirmation
            addMessage('Conversation history and memory cleared successfully.', 'assistant');
        }
    } catch (error) {
        console.error('Error clearing conversation:', error);
        addMessage('Failed to clear conversation history.', 'assistant');
    }
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
       sidebar.classList.toggle('visible');
    }
}

// Initialize memory stats on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    checkApiStatus();
    updateMemoryStats(); // Load initial memory stats
    updateChatHistory(); 
});

function addMessage(content, sender, contextUsed = [], sources = []) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = sender === 'user' ? '👤' : '🤖';
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    
    // Add message header for assistant messages
    if (sender === 'assistant') {
        const messageHeader = document.createElement('div');
        messageHeader.className = 'message-header';
        messageHeader.innerHTML = `
            <span class="assistant-label">TravelBuddy AI</span>
            <span class="message-time">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
        `;
        messageContent.appendChild(messageHeader);
    }
    
    const messageText = document.createElement('div');
    messageText.className = 'message-text';
    
    // Format the message content with CLEAN formatting
    if (sender === 'assistant' || sender === 'bot') {
        messageText.innerHTML = formatBotMessage(content);
    } else {
        messageText.textContent = content;
        // Add time for user messages
        const messageTime = document.createElement('div');
        messageTime.className = 'message-time';
        messageTime.textContent = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        messageContent.appendChild(messageTime);
    }
    
    messageContent.appendChild(messageText);
    
    // Add context info for bot messages (but make it subtle)
    if ((sender === 'assistant' || sender === 'bot') && (contextUsed.length > 0 || sources.length > 0)) {
        const contextInfo = document.createElement('div');
        contextInfo.className = 'context-info';
        contextInfo.innerHTML = `
            <small style="opacity: 0.6; font-size: 0.7rem; margin-top: 0.5rem; display: block;">
                ${sources.length > 0 ? `Model: ${sources.join(', ')} | ` : ''}
                ${contextUsed.length > 0 ? `Context: ${contextUsed.join(', ')}` : ''}
            </small>
        `;
        messageContent.appendChild(contextInfo);
    }
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(messageContent);
    
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

// IMPROVED MESSAGE FORMATTING - This is the key fix!
function formatBotMessage(content) {
    // Clean up the content first - remove excessive asterisks and formatting
    let formatted = content
        // Remove multiple asterisks that create messy formatting
        .replace(/\*\*\*([^*]+)\*\*\*/g, '<strong>$1</strong>') // Triple asterisks to bold
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')     // Double asterisks to bold
        .replace(/\*([^*]+)\*/g, '<em>$1</em>')                 // Single asterisks to italic
        
        // Clean up headers - make them proper HTML headers
        .replace(/^### (.+)$/gm, '<h3 style="color: var(--ocean-blue); margin: 1rem 0 0.5rem 0; font-size: 1.1rem;">$1</h3>')
        .replace(/^## (.+)$/gm, '<h2 style="color: var(--ocean-blue); margin: 1rem 0 0.5rem 0; font-size: 1.2rem;">$1</h2>')
        .replace(/^# (.+)$/gm, '<h1 style="color: var(--ocean-blue); margin: 1rem 0 0.5rem 0; font-size: 1.3rem;">$1</h1>')
        
        // Convert bullet points properly
        .replace(/^\* (.+)$/gm, '<li>$1</li>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        
        // Handle line breaks and paragraphs
        .replace(/\n\n+/g, '</p><p>')  // Double line breaks = new paragraph
        .replace(/\n/g, '<br>');       // Single line breaks = <br>
    
    // Wrap lists in proper ul tags
    formatted = formatted.replace(/(<li>.*?<\/li>)/gs, function(match) {
        return '<ul style="margin: 0.5rem 0; padding-left: 1.5rem;">' + match + '</ul>';
    });
    
    // Clean up any remaining asterisks or markdown artifacts
    formatted = formatted
        .replace(/\*+/g, '') // Remove any remaining asterisks
        .replace(/#{1,6}\s*/g, '') // Remove any remaining hash headers
        .replace(/_+/g, ''); // Remove underscores
    
    // Wrap in paragraphs if not already wrapped
    if (!formatted.includes('<p>') && !formatted.includes('<h1>') && !formatted.includes('<h2>') && !formatted.includes('<h3>')) {
        formatted = '<p>' + formatted + '</p>';
    }
    
    // Final cleanup - remove empty paragraphs and fix spacing
    formatted = formatted
        .replace(/<p><\/p>/g, '')
        .replace(/<p>\s*<\/p>/g, '')
        .replace(/(<\/h[1-6]>)<br>/g, '$1')
        .replace(/(<\/ul>)<br>/g, '$1')
        .replace(/<br><br>/g, '<br>');
    
    return formatted;
}

function showTypingIndicator() {
    isTyping = true;
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message assistant-message';
    typingDiv.id = 'typing-indicator-msg';
    typingDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="typing-dots">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    chatMessages.appendChild(typingDiv);
    scrollToBottom();
}

function hideTypingIndicator() {
    isTyping = false;
    const indicator = document.getElementById('typing-indicator-msg');
    if (indicator) indicator.remove();
}

function setInputEnabled(enabled) {
    messageInput.disabled = !enabled;
    sendButton.disabled = !enabled || messageInput.value.trim() === '';
    
    if (enabled) {
        messageInput.placeholder = 'Ask me anything about travel...';
    } else {
        messageInput.placeholder = 'TravelBuddy is thinking...';
    }
}
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('visible');
}

// Auto-close sidebar when user starts typing
messageInput.addEventListener('focus', function() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar.classList.contains('visible')) {
        sidebar.classList.remove('visible');
    }
});

// Close sidebar when clicking outside
document.addEventListener('click', function(event) {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('sidebarToggle');
    
    if (sidebar.classList.contains('visible') && 
        !sidebar.contains(event.target) && 
        !toggleBtn.contains(event.target)) {
        sidebar.classList.remove('visible');
    }
});
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function sendSuggestion(suggestionText) {
    messageInput.value = suggestionText;
    sendMessage();
}

function toggleContextPanel() {
    const isVisible = contextPanel.style.display !== 'none';
    contextPanel.style.display = isVisible ? 'none' : 'block';
}

function updateContextPanel(contextUsed, sources) {
    const contextHtml = `
        <div class="context-item">
            <h5>🧠 AI Model</h5>
            <p>${sources.join(', ') || 'Not specified'}</p>
        </div>
        <div class="context-item">
            <h5>📚 Context Sources</h5>
            <p>${contextUsed.join(', ') || 'No context used'}</p>
        </div>
        <div class="context-item">
            <h5>👤 User ID</h5>
            <p>${userId}</p>
        </div>
        <div class="context-item">
            <h5>⏰ Last Updated</h5>
            <p>${new Date().toLocaleTimeString()}</p>
        </div>
    `;
    
    contextContent.innerHTML = contextHtml;
}

async function clearConversation() {
    try {
        const response = await fetch(`${API_BASE}/api/conversation/${userId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            // Clear the chat messages (keep welcome message)
            const messages = chatMessages.querySelectorAll('.message');
            messages.forEach((msg, index) => {
                if (index > 0) { // Keep first welcome message
                    msg.remove();
                }
            });
            
            // Show quick suggestions again
            if (quickSuggestions) {
                quickSuggestions.style.display = 'block';
            }
            
            // Show confirmation
            addMessage('Conversation history cleared successfully!', 'assistant');
        }
    } catch (error) {
        console.error('Error clearing conversation:', error);
        addMessage('Failed to clear conversation history.', 'assistant');
    }
}

// Utility functions for demo
function showLoadingOverlay(show = true) {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = show ? 'flex' : 'none';
    }
}

// Add some demo data for presentation
function addDemoContext() {
    const demoContexts = [
        'Previous conversation about budget travel',
        'User preferences: Adventure, Europe',
        'Last search: "Best time to visit Italy"'
    ];
    
    updateContextPanel(['conversation_history', 'user_preferences'], ['llama-3.1-8b']);
}
// Add to DOM elements
const recentTrips = document.getElementById('recentTrips');

// Add to DOMContentLoaded event
document.addEventListener('DOMContentLoaded', function() {
    fetchRecentChats();
});

// Add function to fetch and display recent chats
async function fetchRecentChats() {
    try {
        const response = await fetch(`${API_BASE}/api/memory/${userId}`);
        const data = await response.json();
        const recentTripsDiv = document.getElementById('recentTrips');
        recentTripsDiv.innerHTML = ''; // Clear existing content
        const preferences = data.user_preferences || {};
        const destinations = preferences.destinations_interested || [];
        if (destinations.length > 0) {
            destinations.slice(0, 3).forEach(dest => { // Limit to 3 for UI
                const tripItem = document.createElement('div');
                tripItem.className = 'trip-item';
                tripItem.textContent = `Explore ${dest}`;
                tripItem.style.cursor = 'pointer';
                tripItem.style.padding = '0.5rem';
                tripItem.style.margin = '0.2rem 0';
                tripItem.style.background = 'rgba(255, 255, 255, 0.1)';
                tripItem.style.borderRadius = '4px';
                tripItem.onclick = () => sendSuggestion(`Plan a trip to ${dest}`);
                recentTripsDiv.appendChild(tripItem);
            });
        } else {
            recentTripsDiv.innerHTML = '<p class="no-trips">Start chatting to see trip ideas based on your interests!</p>';
        }
    } catch (error) {
        console.error('Error fetching recent chats:', error);
        recentTrips.innerHTML = '<p class="no-trips">Error loading trip ideas.</p>';
    }
}

// Update sendMessage to refresh recent chats
const originalSendMessage = sendMessage;
sendMessage = async function() {
    await originalSendMessage.apply(null, arguments);
    await fetchRecentChats();
};

// Update clearConversation to refresh recent chats
const originalClearConversation = clearConversation;
clearConversation = async function() {
    await originalClearConversation.apply(null, arguments);
    await fetchRecentChats();
};
// Export functions for global access
window.sendSuggestion = sendSuggestion;
window.sendMessage = sendMessage;
window.toggleContextPanel = toggleContextPanel;
window.clearConversation = clearConversation;
window.checkApiStatus = checkApiStatus;
window.toggleSidebar = toggleSidebar;