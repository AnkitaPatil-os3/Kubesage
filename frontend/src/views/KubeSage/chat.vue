<template>
    <div class="app-container" :class="{ 'dark-mode': isDarkMode }">
        <!-- Sidebar -->
        <div class="sidebar" :class="{ 'sidebar-hidden': !isSidebarVisible }">
            <div class="sidebar-header">
                <button class="new-chat-btn" @click="startNewChat">
                    <span>+ New Chat</span>
                </button>
            </div>
            <div class="chat-history">
                <h3>Chat History</h3>
                <ul>
                    <li v-for="(chat, index) in chatSessions" :key="chat.session_id" @click="loadChat(chat.session_id)"
                        :class="{ active: activeChatSessionId === chat.session_id }">
                        {{ chat.title || `Chat ${index + 1}` }}
                    </li>
                </ul>
            </div>
        </div>

        <!-- Main Chat Section -->
        <div class="main-chat" :class="{ 'full-width': !isSidebarVisible }">
            <!-- Chat Header -->
            <div class="chat-header">
                <button class="toggle-sidebar-btn" @click="toggleSidebar">
                    <svg v-if="isSidebarVisible" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
                        <path fill="currentColor" d="M3 4h18v2H3V4zm0 7h18v2H3v-2zm0 7h18v2H3v-2z" />
                    </svg>
                    <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
                        <path fill="currentColor" d="M3 4h18v2H3V4zm0 7h18v2H3v-2zm0 7h18v2H3v-2z" />
                    </svg>
                </button>
                <h2>ChatOps</h2>
                <button class="toggle-theme-btn" @click="toggleTheme">
                    <svg v-if="isDarkMode" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
                        <path fill="currentColor" d="M12 18c-3.309 0-6-2.691-6-6s2.691-6 6-6 6 2.691 6 6-2.691 6-6 6zm0-10c-2.206 0-4 1.794-4 4s1.794 4 4 4 4-1.794 4-4-1.794-4-4-4zM12 4c-0.553 0-1-0.447-1-1V1c0-0.553 0.447-1 1-1s1 0.447 1 1v2C13 3.553 12.553 4 12 4zM12 24c-0.553 0-1-0.447-1-1v-2c0-0.553 0.447-1 1-1s1 0.447 1 1v2C13 23.553 12.553 24 12 24zM4.929 6.343c-0.391-0.391-0.391-1.023 0-1.414l1.414-1.414c0.391-0.391 1.023-0.391 1.414 0s0.391 1.023 0 1.414L6.343 6.343C5.952 6.734 5.32 6.734 4.929 6.343zM17.657 19.071c-0.391-0.391-0.391-1.023 0-1.414l1.414-1.414c0.391-0.391 1.023-0.391 1.414 0s0.391 1.023 0 1.414l-1.414 1.414C18.68 19.462 18.048 19.462 17.657 19.071zM1 12c0-0.553 0.447-1 1-1h2c0.553 0 1 0.447 1 1s-0.447 1-1 1H2C1.447 13 1 12.553 1 12zM20 12c0-0.553 0.447-1 1-1h2c0.553 0 1 0.447 1 1s-0.447 1-1 1h-2C20.447 13 20 12.553 20 12zM6.343 17.657c-0.391-0.391-0.391-1.023 0-1.414l1.414-1.414c0.391-0.391 1.023-0.391 1.414 0s0.391 1.023 0 1.414l-1.414 1.414C7.366 18.048 6.734 18.048 6.343 17.657zM19.071 4.929c-0.391-0.391-0.391-1.023 0-1.414l1.414-1.414c0.391-0.391 1.023-0.391 1.414 0s0.391 1.023 0 1.414l-1.414 1.414C20.094 5.32 19.462 5.32 19.071 4.929z" />
                    </svg>
                    <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
                        <path fill="currentColor" d="M12 18c-3.309 0-6-2.691-6-6s2.691-6 6-6 6 2.691 6 6-2.691 6-6 6zm0-10c-2.206 0-4 1.794-4 4s1.794 4 4 4 4-1.794 4-4-1.794-4-4-4zM12 4c-0.553 0-1-0.447-1-1V1c0-0.553 0.447-1 1-1s1 0.447 1 1v2C13 3.553 12.553 4 12 4zM12 24c-0.553 0-1-0.447-1-1v-2c0-0.553 0.447-1 1-1s1 0.447 1 1v2C13 23.553 12.553 24 12 24zM4.929 6.343c-0.391-0.391-0.391-1.023 0-1.414l1.414-1.414c0.391-0.391 1.023-0.391 1.414 0s0.391 1.023 0 1.414L6.343 6.343C5.952 6.734 5.32 6.734 4.929 6.343zM17.657 19.071c-0.391-0.391-0.391-1.023 0-1.414l1.414-1.414c0.391-0.391 1.023-0.391 1.414 0s0.391 1.023 0 1.414l-1.414 1.414C18.68 19.462 18.048 19.462 17.657 19.071zM1 12c0-0.553 0.447-1 1-1h2c0.553 0 1 0.447 1 1s-0.447 1-1 1H2C1.447 13 1 12.553 1 12zM20 12c0-0.553 0.447-1 1-1h2c0.553 0 1 0.447 1 1s-0.447 1-1 1h-2C20.447 13 20 12.553 20 12zM6.343 17.657c-0.391-0.391-0.391-1.023 0-1.414l1.414-1.414c0.391-0.391 1.023-0.391 1.414 0s0.391 1.023 0 1.414l-1.414 1.414C7.366 18.048 6.734 18.048 6.343 17.657zM19.071 4.929c-0.391-0.391-0.391-1.023 0-1.414l1.414-1.414c0.391-0.391 1.023-0.391 1.414 0s0.391 1.023 0 1.414l-1.414 1.414C20.094 5.32 19.462 5.32 19.071 4.929z" />
                    </svg>
                </button>
            </div>

            <!-- Chat Messages -->
            <div class="chat-messages" ref="chatMessagesContainer">
                <div v-for="(message, index) in activeChat.messages" :key="index" :class="['message', message.role]">
                    <div class="message-content" v-html="renderMarkdown(message.content)"></div>
                </div>
            </div>

            <!-- Chat Input -->
            <div class="chat-input">
                <textarea v-model="newMessage" @keyup.enter.exact="sendMessage" placeholder="Type a message..." rows="1"
                    ref="textarea"></textarea>
                <button @click="sendMessage">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
                        <path fill="currentColor" d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                    </svg>
                </button>
            </div>
        </div>
    </div>
</template>

<script>
import { ref, watch, nextTick, onMounted } from 'vue';
import axios from 'axios';
import MarkdownIt from 'markdown-it';

export default {
    name: 'ChatApp',
    setup() {
        const host = 'https://10.0.32.123:8004/chat/';
        const chatSessions = ref([]); // List of chat sessions
        const activeChatSessionId = ref(null); // Currently active chat session ID
        const activeChat = ref({ messages: [] }); // Messages for the active chat session
        const newMessage = ref('');
        const textarea = ref(null);
        const chatMessagesContainer = ref(null);

        // Sidebar visibility state
        const isSidebarVisible = ref(true);

        // Dark mode state
        const isDarkMode = ref(false);

        // Initialize Markdown parser
        const md = new MarkdownIt();

        // Function to render Markdown
        const renderMarkdown = (text) => {
            return md.render(text);
        };

        // Toggle sidebar visibility
        const toggleSidebar = () => {
            isSidebarVisible.value = !isSidebarVisible.value;
        };

        // Toggle light/dark mode
        const toggleTheme = () => {
            isDarkMode.value = !isDarkMode.value;
        };

        // Fetch chat sessions on component mount
        onMounted(async () => {
            await fetchChatSessions();
            if (chatSessions.value.length > 0) {
                loadChat(chatSessions.value[0].session_id);
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
                chatSessions.value.push(response.data);
                activeChatSessionId.value = response.data.session_id;
                activeChat.value = { messages: [] };
            } catch (error) {
                console.error('Failed to create new chat session:', error);
            }
        };

        // Load chat history for a specific session
        const loadChat = async (sessionId) => {
            try {
                const response = await axios.get(`${host}history/${sessionId}`, {
                    headers: getAuthHeaders()
                });
                activeChatSessionId.value = sessionId;
                activeChat.value = {
                    messages: response.data.messages,
                };
            } catch (error) {
                console.error('Failed to load chat history:', error);
            }
        };

        // Send a message to the active chat session
        const sendMessage = async () => {
            if (newMessage.value.trim() === '') return;

            try {
                // Add user message to the UI
                activeChat.value.messages.push({
                    role: 'user',
                    content: newMessage.value,
                });
                const userMessage = newMessage.value;
                newMessage.value = '';

                // Send message to the backend
                const response = await axios.post(
                    `${host}`,
                    { content: userMessage, session_id: activeChatSessionId.value },
                    {
                        headers: getAuthHeaders()
                    }
                );

                // Add bot response to the UI
                activeChat.value.messages.push({
                    role: 'bot',
                    content: response.data.content,
                });
            } catch (error) {
                console.error('Failed to send message:', error);

                // Display an error message to the user
                activeChat.value.messages.push({
                    role: 'bot',
                    content: "Sorry, I encountered an error. Please try again.",
                });
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

        return {
            chatSessions,
            activeChatSessionId,
            activeChat,
            newMessage,
            textarea,
            chatMessagesContainer,
            isSidebarVisible,
            isDarkMode,
            renderMarkdown,
            toggleSidebar,
            toggleTheme,
            startNewChat,
            loadChat,
            sendMessage,
        };
    },
};
</script>

<style scoped>
/* Full App Layout */
.app-container {
    display: flex;
    height: 100vh;
    background-color: #f5f5f5;
}

/* Dark Mode */
.app-container.dark-mode {
    background-color: #1e1e1e;
    color: #ffffff;
}

/* Sidebar */
.sidebar {
    width: 250px;
    background-color: #ffffff;
    border-right: 1px solid #e0e0e0;
    padding: 16px;
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
    transition: transform 0.3s ease;
}

.app-container.dark-mode .sidebar {
    background-color: #2d2d2d;
    color: #ffffff;
}

.sidebar.sidebar-hidden {
    transform: translateX(-100%);
}

.sidebar-header {
    margin-bottom: 16px;
}

.new-chat-btn {
    width: 100%;
    padding: 10px;
    background-color: #007bff;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.9rem;
    transition: background-color 0.3s ease;
}

.new-chat-btn:hover {
    background-color: #0056b3;
}

.chat-history {
    margin-top: 16px;
}

.chat-history h3 {
    margin: 0 0 12px;
    font-size: 1rem;
    color: #333;
}

.app-container.dark-mode .chat-history h3 {
    color: #ffffff;
}

.chat-history ul {
    list-style: none;
    padding: 0;
    margin: 0;
}

.chat-history li {
    padding: 8px 12px;
    margin-bottom: 8px;
    border-radius: 8px;
    cursor: pointer;
    transition: background-color 0.3s ease;
}

.chat-history li:hover {
    background-color: #f0f0f0;
}

.app-container.dark-mode .chat-history li:hover {
    background-color: #444;
}

.chat-history li.active {
    background-color: #007bff;
    color: white;
}

/* Main Chat Section */
.main-chat {
    flex: 1;
    display: flex;
    flex-direction: column;
    background-color: #ffffff;
    transition: margin-left 0.3s ease;
}

.main-chat.full-width {
    margin-left: 0;
}

.app-container.dark-mode .main-chat {
    background-color: #1e1e1e;
    color: #ffffff;
}

.chat-header {
    padding: 16px;
    background-color: #f9f9f9;
    border-bottom: 1px solid #e0e0e0;
    text-align: center;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.app-container.dark-mode .chat-header {
    background-color: #2d2d2d;
    color: #ffffff;
}

.chat-header h2 {
    margin: 0;
    font-size: 1.5rem;
    color: #333;
}

.app-container.dark-mode .chat-header h2 {
    color: #ffffff;
}

.toggle-sidebar-btn,
.toggle-theme-btn {
    padding: 8px 12px;
    background-color: transparent;
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
}

.toggle-sidebar-btn svg,
.toggle-theme-btn svg {
    fill: currentColor;
    width: 24px;
    height: 24px;
}

.chat-messages {
    flex: 1;
    padding: 16px;
    overflow-y: auto;
    background-color: #fafafa;
}

.app-container.dark-mode .chat-messages {
    background-color: #1e1e1e;
    color: #ffffff;
}

.message {
    margin-bottom: 12px;
    display: flex;
}

.message.user {
    justify-content: flex-end;
}

.message.bot {
    justify-content: flex-start;
}

.message-content {
    max-width: 70%;
    padding: 12px 16px;
    border-radius: 12px;
    font-size: 0.9rem;
    line-height: 1.4;
}

.message.user .message-content {
    background-color: #007bff;
    color: white;
    border-radius: 12px 12px 0 12px;
}

.message.bot .message-content {
    background-color: #e9ecef;
    color: #333;
    border-radius: 12px 12px 12px 0;
}

.app-container.dark-mode .message.bot .message-content {
    background-color: #444;
    color: #ffffff;
}

.chat-input {
    display: flex;
    align-items: center;
    padding: 12px;
    background-color: #f9f9f9;
    border-top: 1px solid #e0e0e0;
}

.app-container.dark-mode .chat-input {
    background-color: #2d2d2d;
    color: #ffffff;
}

.chat-input textarea {
    flex: 1;
    padding: 10px;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    font-size: 0.9rem;
    resize: none;
    overflow-y: hidden;
    outline: none;
    transition: border-color 0.3s ease;
}

.app-container.dark-mode .chat-input textarea {
    background-color: #1e1e1e;
    color: #ffffff;
    border-color: #444;
}

.chat-input textarea:focus {
    border-color: #007bff;
}

.chat-input button {
    margin-left: 12px;
    padding: 10px;
    background-color: #007bff;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background-color 0.3s ease;
}

.chat-input button:hover {
    background-color: #0056b3;
}

.chat-input button svg {
    fill: white;
    width: 20px;
    height: 20px;
}
</style>