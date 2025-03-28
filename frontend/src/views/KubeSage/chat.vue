<template>
    <div class="app-container" :class="{ 'dark-mode': isDarkMode }">
        <!-- Sidebar -->
        <div class="sidebar"
            :class="{ 'sidebar-hidden': !isSidebarVisible, 'sidebar-minimized': isMinimized && isSidebarVisible }">
            <!-- Sidebar content when not minimized -->
            <div class="sidebar-content" v-show="!isMinimized">
                <div class="sidebar-header">
                    <div class="logo-container">
                        <!-- <img src="/logo.svg" alt="KubeSage Logo" class="logo" /> -->
                        <!-- <h2>KubeSage</h2> -->
                    </div>
                    <n-button class="new-chat-btn" @click="startNewChat">
                        <span><i class="fas fa-plus"></i> New Chat</span>
                    </n-button>
                </div>
                <div class="chat-history">
                    <h3>Recent Conversations</h3>
                    <!-- In the sidebar-content section, modify the history-item div -->
                    <div class="history-list">
                        <div v-for="(chat, index) in chatSessions" :key="chat.session_id"
                            @click="loadChat(chat.session_id)"
                            :class="['history-item', { active: activeChatSessionId === chat.session_id }]">
                            <div class="history-icon"><i class="fas fa-comment-dots"></i></div>
                            <div class="history-title">{{ getUserQuestion(chat.session_id) || chat.title || `Chat ${index + 1}` }}</div>
                            <div class="history-actions">
                                <button class="action-btn" @click.stop="deleteChat(chat.session_id)">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
               
            </div>

            <!-- Minimized sidebar content -->
            <div class="sidebar-minimized-content" v-show="isMinimized">
                <div class="minimized-icons">
                    <!-- <div class="minimized-logo">
                        <img src="/logo.svg" alt="KubeSage Logo" class="logo" />
                    </div> -->
                    <button class="icon-btn" @click="startNewChat" title="New Chat">
                        <i class="fas fa-plus"></i>
                    </button>
                    <div class="history-icons">
                        <button v-for="(chat, index) in chatSessions" :key="chat.session_id"
                            @click="loadChat(chat.session_id)"
                            :class="['icon-btn', { active: activeChatSessionId === chat.session_id }]"
                            :title="chat.title || `Chat ${index + 1}`">
                            <i class="fas fa-comment-dots"></i>
                        </button>
                    </div>
                   
                </div>
            </div>

            <!-- Minimize/Expand toggle button -->
            <button class="minimize-btn" @click="toggleMinimize" :title="isMinimized ? 'Expand' : 'Minimize'">
                <i :class="isMinimized ? 'fas fa-chevron-right' : 'fas fa-chevron-left'"></i>
            </button>
        </div>

        <!-- Main Chat Section -->
        <div class="main-chat"
            :class="{ 'full-width': !isSidebarVisible, 'with-minimized-sidebar': isMinimized && isSidebarVisible }">
            <!-- Chat Header -->
            <div class="chat-header">
                <h2>{{ activeChat.title || 'ChatOps' }}</h2>
                <!-- <div class="header-actions">
                    
                    <button class="toggle-theme-btn" @click="toggleTheme">
                        <i :class="isDarkMode ? 'fas fa-sun' : 'fas fa-moon'"></i>
                    </button>
                </div> -->
            </div>

            <!-- Welcome Screen (shown when no messages) -->
            <div v-if="activeChat.messages.length === 0" class="welcome-screen">
                <div class="welcome-content">
                    <!-- <img src="/logo-large.svg" alt="KubeSage" class="welcome-logo" /> -->
                    <h1>Welcome to KubeSage</h1>
                    <p>Your intelligent GenAI assistant for seamless Kubernetes operations and troubleshooting</p>

                    <div class="suggestion-grid">
                        <div class="suggestion-card" @click="usePrompt('Explain my cluster health status')">
                            <i class="fas fa-heartbeat"></i>
                            <span>Explain my cluster health status</span>
                        </div>
                        <div class="suggestion-card"
                            @click="usePrompt('Troubleshoot pod crashes in namespace default')">
                            <i class="fas fa-bug"></i>
                            <span>Troubleshoot pod crashes</span>
                        </div>
                        <div class="suggestion-card" @click="usePrompt('Optimize resource usage in my cluster')">
                            <i class="fas fa-tachometer-alt"></i>
                            <span>Optimize resource usage</span>
                        </div>
                        <div class="suggestion-card"
                            @click="usePrompt('Explain best practices for Kubernetes security')">
                            <i class="fas fa-shield-alt"></i>
                            <span>Kubernetes security best practices</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Chat Messages -->
            <div v-else class="chat-messages" ref="chatMessagesContainer">
                <div v-for="(message, index) in activeChat.messages" :key="index"
                    :class="['message-container', message.role]">
                    <div class="message-avatar">
                        <i :class="message.role === 'user' ? 'fas fa-user' : 'fas fa-robot'"></i>
                    </div>
                    <div class="message-bubble">
                        <div class="message-header">
                            <span class="message-sender">{{ message.role === 'user' ? 'You' : 'KubeSage' }}</span>
                            <span class="message-time">{{ formatTime(message.created_at) }}</span>
                        </div>
                        <div class="message-content" v-html="renderMarkdown(message.content)"> </div>
                    </div>
                </div>
                <div v-if="isTyping" class="message-container bot">
                    <div class="message-avatar">
                        <i class="fas fa-robot"></i>
                    </div>
                    <div class="message-bubble">
                        <div class="typing-indicator">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Chat Input -->
            <div class="chat-input-container">
                <div class="chat-input">
                    <textarea v-model="newMessage" @keyup.enter.exact="sendMessage"
                        placeholder="Ask KubeSage about your Kubernetes cluster..." rows="1" ref="textarea"></textarea>
                    <n-button class="send-btn" @click="sendMessage" :disabled="!newMessage.trim()">
                        <i class="fas fa-paper-plane"></i>
                    </n-button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { ref, watch, nextTick, onMounted, computed } from 'vue';
import axios from 'axios';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import { NButton } from 'naive-ui';

export default {
    name: 'ChatApp',
    components: {
        NButton
    },
    setup() {
        const host = 'https://10.0.32.122:8006/chat/';
        const chatSessions = ref([]);
        const activeChatSessionId = ref(null);
        const activeChat = ref({ messages: [], title: '' });
        const newMessage = ref('');
        const textarea = ref(null);
        const chatMessagesContainer = ref(null);
        const isSidebarVisible = ref(true);
        const isMinimized = ref(false);
        // const isDarkMode = ref(localStorage.getItem('darkMode') === 'true');
        const isTyping = ref(false);
        const sessionQuestionsCache = ref({});


        // Add this at the beginning of your setup
        const colorScheme = useStorage('vueuse-color-scheme', 'light');
        const isDarkMode = ref(colorScheme.value === 'dark');


        // Watch for color scheme changes
        watch(colorScheme, (newVal) => {
            isDarkMode.value = newVal === 'dark';
            updateDarkModeClasses();
        });

        // Update dark mode classes
        const updateDarkModeClasses = () => {
            if (isDarkMode.value) {
                document.documentElement.classList.add('dark');
                document.body.style.backgroundColor = 'rgb(24 24 28)';
            } else {
                document.documentElement.classList.remove('dark');
                document.body.style.backgroundColor = '';
            }
        };

        // Add this method to completely hide the sidebar (in addition to minimizing)
        const fullHideSidebar = () => {
            isSidebarVisible.value = false;
            isMinimized.value = false;
        };

        // Initialize Markdown parser with syntax highlighting
        const md = new MarkdownIt({
            highlight: function (str, lang) {
                if (lang && hljs.getLanguage(lang)) {
                    try {
                        return hljs.highlight(str, { language: lang }).value;
                    } catch (__) { }
                }
                return ''; // use external default escaping
            }
        });

        // Format timestamp
        const formatTime = (timestamp) => {
            if (!timestamp) return '';
            const date = new Date(timestamp);
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        };

        // Render Markdown with code highlighting
        const renderMarkdown = (text) => {
            if (!text) return '';
            return md.render(text);
        };

        // Toggle sidebar visibility
        const toggleSidebar = () => {
            isSidebarVisible.value = !isSidebarVisible.value;
            // If we're showing the sidebar again and it was minimized, keep it minimized
            // Otherwise, reset minimized state when hiding sidebar
            if (!isSidebarVisible.value) {
                isMinimized.value = false;
            }
        };

        // Toggle minimized state
        const toggleMinimize = () => {
            isMinimized.value = !isMinimized.value;
            // Ensure sidebar is visible when toggling minimize
            if (!isSidebarVisible.value) {
                isSidebarVisible.value = true;
            }
        };



        // Toggle light/dark mode
        const toggleTheme = () => {
            isDarkMode.value = !isDarkMode.value;
            localStorage.setItem('darkMode', isDarkMode.value);
        };

        // Use a suggested prompt
        const usePrompt = (prompt) => {
            newMessage.value = prompt;
            nextTick(() => {
                if (textarea.value) {
                    textarea.value.focus();
                }
                // Automatically send the message after setting the prompt
                sendMessage();
            });
        };

        // Clear current chat
        const clearChat = () => {
            if (confirm('Are you sure you want to clear this conversation?')) {
                activeChat.value.messages = [];
            }
        };

        // Delete a chat session
        const deleteChat = async (sessionId) => {
            if (confirm('Are you sure you want to delete this chat?')) {
                try {
                    await axios.delete(`${host}sessions/${sessionId}`, {
                        headers: getAuthHeaders()
                    });

                    // Remove from local list
                    chatSessions.value = chatSessions.value.filter(chat => chat.session_id !== sessionId);

                    // If we deleted the active chat, load another one or start fresh
                    if (activeChatSessionId.value === sessionId) {
                        if (chatSessions.value.length > 0) {
                            loadChat(chatSessions.value[0].session_id);
                        } else {
                            startNewChat();
                        }
                    }
                } catch (error) {
                    console.error('Failed to delete chat session:', error);
                }
            }
        };

        // Fetch chat sessions on component mount
        onMounted(async () => {
            // Apply dark mode from localStorage and update classes
            updateDarkModeClasses();
            // Apply dark mode from localStorage
            // if (isDarkMode.value) {
            //     document.body.classList.add('dark-mode');
            // }

            await fetchChatSessions();
            if (chatSessions.value.length > 0) {
                loadChat(chatSessions.value[0].session_id);
            } else {
                startNewChat();
            }
        });

        // Fetch all chat sessions for the user
        const fetchChatSessions = async () => {
            try {
                const response = await axios.get(`${host}sessions`, {
                    headers: getAuthHeaders()
                });
                chatSessions.value = response.data.sessions;
            } catch (error) {
                console.error('Failed to fetch chat sessions:', error);
            }
        };

        // Start a new chat session 
        const startNewChat = async () => {
            try {
                const response = await axios.post(
                    `${host}sessions`,
                    { title: 'New Chat' },
                    {
                        headers: getAuthHeaders()
                    }
                );
                chatSessions.value.unshift(response.data);
                activeChatSessionId.value = response.data.session_id;
                activeChat.value = { messages: [], title: 'New Chat' };
            } catch (error) {
                console.error('Failed to create new chat session:', error);
            }
        };

      

                // Method to get the user question for a chat session
                const getUserQuestion = (sessionId) => {
            // Check if we have this session's first question cached
            if (sessionQuestionsCache.value[sessionId]) {
                return sessionQuestionsCache.value[sessionId];
            }
            
            // If this is the active session, get the first user message
            if (activeChatSessionId.value === sessionId && activeChat.value.messages.length > 0) {
                const userMessages = activeChat.value.messages.filter(msg => msg.role === 'user');
                if (userMessages.length > 0) {
                    const question = userMessages[0].content;
                    // Truncate long questions
                    const truncated = question.length > 30 ? question.substring(0, 30) + '...' : question;
                    // Cache the result
                    sessionQuestionsCache.value[sessionId] = truncated;
                    return truncated;
                }
            }
            
            return null;
        };

        // Modify the loadChat function to cache the first user question
        const loadChat = async (sessionId) => {
            try {
                const response = await axios.get(`${host}history/${sessionId}`, {
                    headers: getAuthHeaders()
                });
                activeChatSessionId.value = sessionId;
                activeChat.value = {
                    messages: response.data.messages,
                    title: response.data.title
                };
                
                // Cache the first user question from this session
                const userMessages = response.data.messages.filter(msg => msg.role === 'user');
                if (userMessages.length > 0) {
                    const question = userMessages[0].content;
                    const truncated = question.length > 30 ? question.substring(0, 30) + '...' : question;
                    sessionQuestionsCache.value[sessionId] = truncated;
                }
            } catch (error) {
                console.error('Failed to load chat history:', error);
            }
        };

        // Also update sendMessage to cache the first question for new chats
        const sendMessage = async () => {
            if (newMessage.value.trim() === '') return;

            try {
                // Add user message to the UI
                activeChat.value.messages.push({
                    role: 'user',
                    content: newMessage.value,
                    created_at: new Date().toISOString()
                });
                const userMessage = newMessage.value;
                newMessage.value = '';

                // If this is the first message, cache it as the question for this session
                if (activeChat.value.messages.length === 1) {
                    const truncated = userMessage.length > 30 ? userMessage.substring(0, 30) + '...' : userMessage;
                    sessionQuestionsCache.value[activeChatSessionId.value] = truncated;
                }

                // Show typing indicator
                isTyping.value = true;

                // Rest of your existing sendMessage code...
            } catch (error) {
                // Your existing error handling...
            }
        };

        // Get auth token from localStorage
        const getAuthHeaders = () => {
            try {
                const token = JSON.parse(localStorage.getItem('accessToken')).value;
                return { Authorization: `Bearer ${token}` };
            } catch (error) {
                console.error('Authentication error. Please login again.');
                return {};
            }
        };

        // Auto-resize textarea
        watch(newMessage, () => {
            nextTick(() => {
                if (textarea.value) {
                    textarea.value.style.height = 'auto';
                    textarea.value.style.height = `${textarea.value.scrollHeight}px`;
                }
            });
        });

        // Auto-scroll to the bottom of the chat messages
        watch(
            () => activeChat.value.messages,
            () => {
                nextTick(() => {
                    if (chatMessagesContainer.value) {
                        chatMessagesContainer.value.scrollTop = chatMessagesContainer.value.scrollHeight;
                    }
                });
            },
            { deep: true }
        );

        // Also scroll when typing indicator changes
        watch(isTyping, () => {
            nextTick(() => {
                if (chatMessagesContainer.value) {
                    chatMessagesContainer.value.scrollTop = chatMessagesContainer.value.scrollHeight;
                }
            });
        });

        return {
            chatSessions,
            activeChatSessionId,
            activeChat,
            newMessage,
            textarea,
            chatMessagesContainer,
            isSidebarVisible,
            isMinimized,
            isDarkMode,
            isTyping,
            sessionQuestionsCache,
            renderMarkdown,
            formatTime,
            toggleSidebar,
            toggleMinimize,
            toggleTheme,
            startNewChat,
            loadChat,
            sendMessage,
            usePrompt,
            clearChat,
            deleteChat,
            getUserQuestion
        };
    },
};
</script>

<style>
/* Import Font Awesome or use a CDN link in your index.html */
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');
/* Import highlight.js styles */
@import url('https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/github.min.css');

/* Dark mode override for highlight.js */
.dark-mode .hljs {
    background: #2d2d2d;
    color: #e6e6e6;
}
</style>

<style scoped>
/* Full App Layout */
.app-container {
    display: flex;
    height: 100vh;
    background-color: #f8f9fa;
    background-image: linear-gradient(to bottom right, #f8f9fa, #e8f5e9);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
}

/* Dark Mode */
.app-container.dark-mode {
    background-color: #1a1a1a;
    background-image: linear-gradient(to bottom right, #1a1a1a, #0d2d0f);
    color: #f0f0f0;
}

/* Sidebar */
.sidebar {
    width: 280px;
    background-color: #ffffff;
    background-image: linear-gradient(135deg, #ffffff, #f5fff7);
    border-right: 1px solid #e0e0e0;
    display: flex;
    flex-direction: column;
    transition: transform 0.3s ease, width 0.3s ease;
    box-shadow: 0 0 20px rgba(16, 188, 59, 0.08);
    z-index: 10;
    position: relative;
}

.app-container.dark-mode .sidebar {
    background-color: #222222;
    background-image: linear-gradient(135deg, #222222, #1a2e1d);
    border-right: 1px solid #333333;
    box-shadow: 0 0 20px rgba(0, 0, 0, 0.2);
}

.sidebar.sidebar-hidden {
    transform: translateX(-100%);
}

.sidebar.sidebar-minimized {
    width: 70px;
}

.sidebar-content {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow-y: auto;
}

/* Minimized sidebar styles */
.sidebar-minimized-content {
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 16px 0;
}

.minimized-icons {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    height: 100%;
}

.minimized-logo {
    margin-bottom: 16px;
}

.minimized-logo .logo {
    width: 40px;
    height: 40px;
}

.icon-btn {
    width: 40px;
    height: 40px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: #3f4440;
    cursor: pointer;
    transition: all 0.2s ease;
}

.icon-btn:hover {
    background-color: rgba(16, 188, 59, 0.1);
    color: #09a431;
    transform: translateY(-2px);
}

.app-container.dark-mode .icon-btn:hover {
    background-color: rgba(16, 188, 59, 0.2);
}

.icon-btn.active {
    background-color: rgba(16, 188, 59, 0.15);
    color: #10BC3B;
    box-shadow: 0 2px 8px rgba(16, 188, 59, 0.2);
}

.app-container.dark-mode .icon-btn.active {
    background-color: rgba(16, 188, 59, 0.25);
    color: #10BC3B;
    box-shadow: 0 2px 8px rgba(16, 188, 59, 0.3);
}

.history-icons {
    display: flex;
    flex-direction: column;
    gap: 8px;
    overflow-y: auto;
    flex: 1;
    align-items: center;
    padding: 8px 0;
}

.minimized-footer {
    margin-top: auto;
    padding-top: 16px;
}

/* Minimize/Expand button */
.minimize-btn {
    position: absolute;
    right: -12px;
    top: 50%;
    transform: translateY(-50%);
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background-color: #10BC3B;
    border: 2px solid #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    z-index: 11;
    box-shadow: 0 2px 8px rgba(16, 188, 59, 0.2);
    transition: all 0.2s ease;
    color: white;
    font-size: 10px;
}

.app-container.dark-mode .minimize-btn {
    background-color: #10BC3B;
    border: 2px solid #222222;
    color: white;
}

.minimize-btn:hover {
    background-color: #09a431;
    transform: translateY(-50%) scale(1.1);
}

.app-container.dark-mode .minimize-btn:hover {
    background-color: #09a431;
}

.sidebar-header {
    padding: 16px;
    border-bottom: 1px solid rgba(16, 188, 59, 0.1);
}

.app-container.dark-mode .sidebar-header {
    border-bottom: 1px solid rgba(16, 188, 59, 0.2);
}

/* Specific styles for clear chat button */
/* Action buttons in header */
.action-btn,
.toggle-theme-btn {
    width: 40px;
    height: 40px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: #10BC3B;
    cursor: pointer;
    transition: all 0.2s ease;
}

.action-btn:hover,
.toggle-theme-btn:hover {
    background-color: rgba(16, 188, 59, 0.1);
    color: #09a431;
}

.app-container.dark-mode .action-btn,
.app-container.dark-mode .toggle-theme-btn {
    color: #10BC3B;
}

.app-container.dark-mode .action-btn:hover,
.app-container.dark-mode .toggle-theme-btn:hover {
    background-color: rgba(16, 188, 59, 0.2);
    color: #10BC3B;
}

/* Specific styles for clear chat button */
.action-btn {
    position: relative;
}

.action-btn:hover {
    color: #ef4444;
    /* Red color on hover for clear action */
}

/* Specific styles for theme toggle button */
.toggle-theme-btn {
    position: relative;
    overflow: hidden;
}

.toggle-theme-btn i {
    font-size: 1.1rem;
    transition: transform 0.3s ease;
}

.toggle-theme-btn:hover i {
    transform: rotate(12deg);
}

/* Add a subtle tooltip on hover */
.action-btn::after,
.toggle-theme-btn::after {
    content: attr(title);
    position: absolute;
    bottom: -30px;
    left: 50%;
    transform: translateX(-50%);
    background-color: #10BC3B;
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    white-space: nowrap;
    opacity: 0;
    visibility: hidden;
    transition: opacity 0.2s ease, visibility 0.2s ease;
    pointer-events: none;
}

.action-btn:hover::after,
.toggle-theme-btn:hover::after {
    opacity: 1;
    visibility: visible;
}

.app-container.dark-mode .action-btn::after,
.app-container.dark-mode .toggle-theme-btn::after {
    background-color: #09a431;
}


.logo-container {
    display: flex;
    align-items: center;
    margin-bottom: 16px;
}

.logo {
    width: 32px;
    height: 32px;
    margin-right: 10px;
}

.logo-container h2 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: #10BC3B;
}

.app-container.dark-mode .logo-container h2 {
    color: #10BC3B;
}

:deep(.new-chat-btn) {
    width: 100%;
    background: linear-gradient(135deg, #10BC3B, #09a431) !important;
    border: none !important;
    color: white !important;
    padding: 12px !important;
    border-radius: 8px !important;
    cursor: pointer !important;
    font-size: 0.95rem !important;
    font-weight: 500 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 12px rgba(16, 188, 59, 0.2) !important;
}

:deep(.new-chat-btn:hover) {
    background: linear-gradient(135deg, #09a431, #078a29) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 16px rgba(16, 188, 59, 0.3) !important;
}

:deep(.new-chat-btn) i {
    margin-right: 8px !important;
}

.chat-history {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
}

.chat-history h3 {
    margin: 0 0 16px;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #10BC3B;
    font-weight: 600;
}

.app-container.dark-mode .chat-history h3 {
    color: #10BC3B;
}

.history-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.history-item {
    display: flex;
    align-items: center;
    padding: 4px 12px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
    border-left: 2px solid transparent;
}

.history-item:hover {
    background-color: rgba(16, 188, 59, 0.05);
    border-left: 2px solid #10BC3B;
    transform: translateX(2px);
}

.app-container.dark-mode .history-item:hover {
    background-color: rgba(16, 188, 59, 0.1);
}

.history-item.active {
    background-color: rgba(16, 188, 59, 0.1);
    border-left: 2px solid #10BC3B;
}

.app-container.dark-mode .history-item.active {
    background-color: rgba(16, 188, 59, 0.15);
}

.history-icon {
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 12px;
    color: #3d423e;
}

.app-container.dark-mode .history-icon {
    color: #3d423e;
}

.history-title {
    flex: 1;
    font-size: 0.95rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: #4a5568;
}

.app-container.dark-mode .history-title {
    color: #a0aec0;
}

.history-actions {
    opacity: 0;
    transition: opacity 0.2s ease;
}

.history-item:hover .history-actions {
    opacity: 1;
}

.action-btn {
    background: transparent;
    border: none;
    color: #10BC3B;
    cursor: pointer;
    padding: 4px;
    border-radius: 4px;
    transition: all 0.2s ease;
}

.action-btn:hover {
    background-color: rgba(239, 68, 68, 0.1);
    color: #ef4444;
}

.app-container.dark-mode .action-btn:hover {
    background-color: rgba(239, 68, 68, 0.2);
}

.sidebar-footer {
    padding: 16px;
    border-top: 1px solid rgba(16, 188, 59, 0.1);
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.app-container.dark-mode .sidebar-footer {
    border-top: 1px solid rgba(16, 188, 59, 0.2);
}

.theme-toggle {
    background: transparent;
    border: none;
    color: #10BC3B;
    cursor: pointer;
    padding: 8px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
    transition: all 0.2s ease;
    font-size: 0.9rem;
}

.theme-toggle:hover {
    background-color: rgba(16, 188, 59, 0.1);
}

.app-container.dark-mode .theme-toggle {
    color: #10BC3B;
}

.app-container.dark-mode .theme-toggle:hover {
    background-color: rgba(16, 188, 59, 0.2);
}

.user-info {
    display: flex;
    align-items: center;
    padding: 8px;
    border-radius: 8px;
    background-color: rgba(16, 188, 59, 0.05);
    border: 1px solid rgba(16, 188, 59, 0.1);
}

.app-container.dark-mode .user-info {
    background-color: rgba(16, 188, 59, 0.1);
    border: 1px solid rgba(16, 188, 59, 0.2);
}

.avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background-color: #10BC3B;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 12px;
}

.username {
    font-size: 0.95rem;
    font-weight: 500;
    color: #4a5568;
}

.app-container.dark-mode .username {
    color: #a0aec0;
}

/* Main Chat Section */
.main-chat {
    flex: 1;
    display: flex;
    flex-direction: column;
    background-color: #ffffff;
    background-image: linear-gradient(135deg, #ffffff, #f9fdf9);
    transition: margin-left 0.3s ease, width 0.3s ease;
    position: relative;
    width: calc(100% - 280px);
    /* Default width with sidebar visible */
}

.main-chat.full-width {
    margin-left: 0;
    width: 100%;
    /* Full width when sidebar is hidden */
}

.main-chat.with-minimized-sidebar {
    /* margin-left: 70px; */
    width: calc(100% - 70px);
    /* Adjusted width with minimized sidebar */
}

.app-container.dark-mode .main-chat {
    background-color: #1a1a1a;
    background-image: linear-gradient(135deg, #1a1a1a, #1a231c);
}

.chat-header {
    padding: 16px 24px;
    background-color: rgba(255, 255, 255, 0.8);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid rgba(16, 188, 59, 0.1);
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: sticky;
    top: 0;
    z-index: 5;
}

.app-container.dark-mode .chat-header {
    background-color: rgba(26, 26, 26, 0.8);
    border-bottom: 1px solid rgba(16, 188, 59, 0.2);
}

.chat-header h2 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
    color: #10BC3B;
    letter-spacing: 0.5px;
}

.app-container.dark-mode .chat-header h2 {
    color: #10BC3B;
}

.toggle-sidebar-btn {
    background: transparent;
    border: none;
    color: #10BC3B;
    cursor: pointer;
    width: 40px;
    height: 40px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
}

.toggle-sidebar-btn:hover {
    background-color: rgba(16, 188, 59, 0.1);
}

.app-container.dark-mode .toggle-sidebar-btn {
    color: #10BC3B;
}

.app-container.dark-mode .toggle-sidebar-btn:hover {
    background-color: rgba(16, 188, 59, 0.2);
}

.header-actions {
    display: flex;
    gap: 8px;
}

/* Welcome Screen */
.welcome-screen {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    overflow-y: auto;
}

.welcome-content {
    max-width: 850px;
    text-align: center;
    padding: 40px 20px;
}

.welcome-logo {
    width: 120px;
    height: 120px;
    margin-bottom: 24px;
}

.welcome-content h1 {
    font-size: 2.5rem;
    font-weight: 700;
    margin-bottom: 16px;
    background: linear-gradient(90deg, #10BC3B, #09a431);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: 0.5px;
}

.welcome-content p {
    font-size: 1.25rem;
    color: #4a5568;
    margin-bottom: 40px;
    line-height: 1.6;
}

.app-container.dark-mode .welcome-content p {
    color: #a0aec0;
}

.suggestion-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 16px;
    margin-top: 32px;
}

.suggestion-card {
    background-color: #f9fafb;
    border: 1px solid rgba(16, 188, 59, 0.1);
    border-radius: 12px;
    padding: 20px;
    cursor: pointer;
    transition: all 0.3s ease;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
}

.app-container.dark-mode .suggestion-card {
    background-color: #2d3748;
    border: 1px solid rgba(16, 188, 59, 0.2);
}

.suggestion-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 25px rgba(16, 188, 59, 0.1);
    border-color: #10BC3B;
}

.suggestion-card i {
    font-size: 24px;
    color: #10BC3B;
}

.suggestion-card span {
    font-size: 0.95rem;
    text-align: center;
    color: #4a5568;
}

.app-container.dark-mode .suggestion-card span {
    color: #a0aec0;
}

/* Chat Messages */
.chat-messages {
    flex: 1;
    padding: 24px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 24px;
}

.message-container {
    display: flex;
    gap: 16px;
    max-width: 90%;
}

.message-container.user {
    align-self: flex-end;
    flex-direction: row-reverse;
}

.message-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

.message-container.user .message-avatar {
    background-color: #10BC3B;
    color: white;
}

.message-container.bot .message-avatar {
    background-color: #0a8aaa;
    color: white;
}

.message-bubble {
    background-color: #f3f4f6;
    border-radius: 16px;
    padding: 16px;
    position: relative;
    max-width: calc(100% - 56px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.app-container.dark-mode .message-bubble {
    background-color: #2d3748;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.message-container.user .message-bubble {
    background-color: #f3f4f6;
    color: #4a5568;
    border-left: 3px solid #0a8aaa;
    border-radius: 16px 16px 0 16px;
    box-shadow: 0 2px 8px rgba(16, 188, 59, 0.2);
}

.app-container.dark-mode .message-container.user .message-bubble {
    
    box-shadow: 0 2px 8px rgba(16, 188, 59, 0.3);
}

.message-container.bot .message-bubble {
    background-color: #f3f4f6;
    color: #4a5568;
    border-radius: 16px 16px 16px 0;
    border-left: 3px solid #0a8aaa;
}

.app-container.dark-mode .message-container.bot .message-bubble {
    background-color: #2d3748;
    color: #a0aec0;
    border-left: 3px solid #0a8aaa;
}

.message-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
    font-size: 0.85rem;
}

.message-sender {
    font-weight: 600;
}

.message-time {
    color: rgba(74, 85, 104, 0.8);
}

.message-container.user .message-time {
    color: rgba(255, 255, 255, 0.8);
}

.app-container.dark-mode .message-time {
    color: rgba(160, 174, 192, 0.8);
}

.message-content {
    font-size: 0.95rem;
    line-height: 1.6;
    overflow-wrap: break-word;
    word-break: break-word;
}

/* Style for code blocks in messages */
.message-content pre {
    background-color: rgba(0, 0, 0, 0.05);
    border-radius: 8px;
    padding: 12px;
    overflow-x: auto;
    margin: 12px 0;
}

.app-container.dark-mode .message-content pre {
    background-color: rgba(0, 0, 0, 0.3);
}

.message-container.user .message-content pre {
    background-color: rgba(0, 0, 0, 0.2);
}

.message-content code {
    font-family: 'Fira Code', monospace;
    font-size: 0.85rem;
}

.message-content p {
    margin: 0 0 12px;
}

.message-content p:last-child {
    margin-bottom: 0;
}

/* Typing indicator */
.typing-indicator {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 8px 0;
}

.typing-indicator span {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #10BC3B;
    display: inline-block;
    animation: typing 1.4s infinite ease-in-out both;
}

.app-container.dark-mode .typing-indicator span {
    background-color: #10BC3B;
}

.typing-indicator span:nth-child(1) {
    animation-delay: 0s;
}

.typing-indicator span:nth-child(2) {
    animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
    animation-delay: 0.4s;
}

@keyframes typing {
    0%,
    100% {
        transform: scale(0.6);
        opacity: 0.6;
    }

    50% {
        transform: scale(1);
        opacity: 1;
    }
}

/* Chat Input */
.chat-input-container {
    padding: 16px 24px;
    background-color: rgba(255, 255, 255, 0.8);
    backdrop-filter: blur(10px);
    border-top: 1px solid rgba(16, 188, 59, 0.1);
    position: sticky;
    bottom: 0;
    z-index: 5;
}

.app-container.dark-mode .chat-input-container {
    background-color: rgba(26, 26, 26, 0.8);
    border-top: 1px solid rgba(16, 188, 59, 0.2);
}

.chat-input {
    display: flex;
    align-items: flex-end;
    gap: 12px;
    background-color: #f9fafb;
    border: 1px solid rgba(16, 188, 59, 0.1);
    border-radius: 12px;
    padding: 12px 16px;
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(16, 188, 59, 0.05);
}

.app-container.dark-mode .chat-input {
    background-color: #2d3748;
    border: 1px solid rgba(16, 188, 59, 0.2);
    box-shadow: 0 2px 8px rgba(16, 188, 59, 0.1);
}

.chat-input:focus-within {
    box-shadow: 0 0 0 2px #10BC3B;
    border-color: #10BC3B;
    transform: translateY(-2px);
}

.chat-input textarea {
    flex: 1;
    background: transparent;
    border: none;
    padding: 0;
    font-size: 0.95rem;
    resize: none;
    max-height: 150px;
    outline: none;
    color: #4a5568;
    font-family: inherit;
    line-height: 1.6;
}

.app-container.dark-mode .chat-input textarea {
    color: #a0aec0;
}

.chat-input textarea::placeholder {
    color: #a0aec0;
}

:deep(.send-btn) {
    background: linear-gradient(135deg, #10BC3B, #09a431) !important;
    border: none !important;
    color: white !important;
    width: 40px !important;
    height: 40px !important;
    border-radius: 8px !important;
    cursor: pointer !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 2px 8px rgba(16, 188, 59, 0.2) !important;
}

:deep(.send-btn:hover) {
    background: linear-gradient(135deg, #09a431, #078a29) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(16, 188, 59, 0.3) !important;
}

:deep(.send-btn:disabled) {
    background: #a0aec0 !important;
    cursor: not-allowed !important;
    transform: none !important;
    box-shadow: none !important;
}

.input-footer {
    display: flex;
    justify-content: center;
    margin-top: 8px;
}

.disclaimer {
    font-size: 0.75rem;
    color: #a0aec0;
}

.app-container.dark-mode .disclaimer {
    color: #718096;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .sidebar {
        position: absolute;
        height: 100%;
        z-index: 20;
    }

    .sidebar-hidden {
        transform: translateX(-100%);
    }

    .sidebar.sidebar-minimized {
        width: 60px;
    }

    .minimize-btn {
        display: none;
        /* Hide on mobile, just use the hamburger toggle */
    }

    .suggestion-grid {
        grid-template-columns: 1fr;
    }

    .message-container {
        max-width: 100%;
    }
    
    .chat-header {
        padding: 12px 16px;
    }
    
    .chat-messages {
        padding: 16px;
    }
    
    .chat-input-container {
        padding: 12px 16px;
    }
    
    .welcome-content h1 {
        font-size: 2rem;
    }
    
    .welcome-content p {
        font-size: 1rem;
    }
}

/* Additional animations */
@keyframes fadeIn {
    from {
        opacity: 0;
    }
    to {
        opacity: 1;
    }
}

.message-container {
    animation: fadeIn 0.3s ease;
}

.suggestion-card {
    animation: fadeIn 0.5s ease;
}

/* Custom scrollbar */
::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-track {
    background: transparent;
}

::-webkit-scrollbar-thumb {
    background-color: rgba(16, 188, 59, 0.2);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background-color: rgba(16, 188, 59, 0.4);
}

.app-container.dark-mode ::-webkit-scrollbar-thumb {
    background-color: rgba(16, 188, 59, 0.3);
}

.app-container.dark-mode ::-webkit-scrollbar-thumb:hover {
    background-color: rgba(16, 188, 59, 0.5);
}
</style>

