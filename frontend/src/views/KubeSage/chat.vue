<template>
    <div class="app-container">
        <!-- Sidebar -->
        <div class="sidebar">
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
        <div class="main-chat">
            <!-- Chat Header -->
            <div class="chat-header">
                <h2>ChatGPT</h2>
            </div>

            <!-- Chat Messages -->
            <div class="chat-messages" ref="chatMessagesContainer">
                <div v-for="(message, index) in activeChat.messages" :key="index" :class="['message', message.role]">
                    <div class="message-content">
                        {{ message.content }}
                    </div>
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

export default {
    name: 'ChatApp',
    setup() {
        const host = 'https://10.0.34.129:8003/chat/';
        const chatSessions = ref([]); // List of chat sessions
        const activeChatSessionId = ref(null); // Currently active chat session ID
        const activeChat = ref({ messages: [] }); // Messages for the active chat session
        const newMessage = ref('');
        const textarea = ref(null);
        const chatMessagesContainer = ref(null);

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
                messageApi.error('Authentication error. Please login again.');
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

/* Sidebar */
.sidebar {
    width: 250px;
    background-color: #ffffff;
    border-right: 1px solid #e0e0e0;
    padding: 16px;
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
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
}

.chat-header {
    padding: 16px;
    background-color: #f9f9f9;
    border-bottom: 1px solid #e0e0e0;
    text-align: center;
}

.chat-header h2 {
    margin: 0;
    font-size: 1.5rem;
    color: #333;
}

.chat-messages {
    flex: 1;
    padding: 16px;
    overflow-y: auto;
    background-color: #fafafa;
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

.chat-input {
    display: flex;
    align-items: center;
    padding: 12px;
    background-color: #f9f9f9;
    border-top: 1px solid #e0e0e0;
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