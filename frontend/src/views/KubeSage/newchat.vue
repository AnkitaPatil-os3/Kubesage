<template>
    <div
        class="flex h-screen bg-gradient-to-br from-gray-50 to-green-50 dark:from-gray-900 dark:to-gray-800 transition-colors duration-300">
        <!-- Sidebar -->
        <div :class="[
            'transition-all duration-300 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 shadow-lg relative',
            isSidebarVisible ? (isMinimized ? 'w-20' : 'w-72') : 'w-0 -translate-x-full'
        ]">
            <!-- Sidebar header with minimize button -->
            <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                <div class="flex items-center">
                    <!-- Logo placeholder -->
                    <span v-if="!isMinimized"
                        class="text-lg font-semibold text-green-600 dark:text-green-500">ChatOps</span>
                </div>
                <button @click="toggleMinimize"
                    class="w-8 h-8 flex items-center justify-center rounded-md text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                    :title="isMinimized ? 'Expand sidebar' : 'Minimize sidebar'">
                    <i :class="isMinimized ? 'fas fa-expand' : 'fas fa-compress'"></i>
                </button>
            </div>

            <!-- Sidebar content when not minimized -->
            <div v-show="!isMinimized" class="flex flex-col h-full overflow-y-auto">
                <div class="p-4 border-b border-gray-200 dark:border-gray-700">
                    <div class="flex items-center mb-4">
                        <!-- Logo placeholder -->
                    </div>
                    <button @click="startNewChat"
                        class="w-full py-3 px-4 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white rounded-lg shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all duration-200 flex items-center justify-center">
                        <i class="fas fa-plus mr-2"></i>
                        <span>New Chat</span>
                    </button>
                </div>
                <div class="flex-1 p-4">
                    <h3 class="text-xs uppercase tracking-wider text-green-600 dark:text-green-500 font-semibold mb-4">
                        Recent Conversations</h3>
                    <div class="space-y-2">
                        <div v-for="(chat, index) in chatSessions" :key="chat.session_id"
                            @click="loadChat(chat.session_id)" :class="[
                                'flex items-center p-2 rounded-lg cursor-pointer transition-all duration-200 border-l-2',
                                activeChatSessionId === chat.session_id
                                    ? 'bg-green-50 dark:bg-green-900/20 border-l-green-500'
                                    : 'hover:bg-gray-50 dark:hover:bg-gray-700/30 border-l-transparent hover:border-l-green-500'
                            ]">
                            <div class="w-8 h-8 flex items-center justify-center text-gray-600 dark:text-gray-400">
                                <i class="fas fa-comment-dots"></i>
                            </div>
                            <div class="ml-3 flex-1 truncate text-gray-700 dark:text-gray-300">
                                {{ getUserQuestion(chat.session_id) || chat.title || `Chat ${index + 1}` }}
                            </div>
                            <button @click.stop="deleteChat(chat.session_id)"
                                class="w-8 h-8 flex items-center justify-center text-gray-500 hover:text-red-500 dark:text-gray-400 dark:hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Minimized sidebar content -->
            <div v-show="isMinimized" class="flex flex-col items-center py-4 h-full">
                <button @click="startNewChat"
                    class="w-12 h-12 mb-6 flex items-center justify-center bg-green-500 hover:bg-green-600 text-white rounded-lg shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all duration-200">
                    <i class="fas fa-plus"></i>
                </button>
                <div class="flex-1 overflow-y-auto flex flex-col items-center space-y-2 w-full px-2">
                    <button v-for="(chat, index) in chatSessions" :key="chat.session_id"
                        @click="loadChat(chat.session_id)" :class="[
                            'w-12 h-12 flex items-center justify-center rounded-lg transition-all duration-200',
                            activeChatSessionId === chat.session_id
                                ? 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-500 shadow-md'
                                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700/30'
                        ]" :title="chat.title || `Chat ${index + 1}`">
                        <i class="fas fa-comment-dots"></i>
                    </button>
                </div>
            </div>

            <!-- Minimize/Expand toggle button -->
            <button @click="toggleMinimize"
                class="absolute -right-3 top-1/2 transform -translate-y-1/2 w-6 h-6 rounded-full bg-green-500 border-2 border-white dark:border-gray-800 flex items-center justify-center text-white text-xs shadow-md hover:bg-green-600 transition-all duration-200"
                :title="isMinimized ? 'Expand' : 'Minimize'">
                <i :class="isMinimized ? 'fas fa-chevron-right' : 'fas fa-chevron-left'"></i>
            </button>
        </div>

        <!-- Main Chat Section -->
        <div :class="[
            'flex-1 flex flex-col bg-white dark:bg-gray-900 transition-all duration-300',
            isSidebarVisible ? (isMinimized ? 'ml-0' : 'ml-0') : 'ml-0'
        ]">
            <!-- Chat Header -->
            <div
                class="sticky top-0 z-10 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex justify-between items-center">
                <h2 class="text-xl font-semibold text-green-600 dark:text-green-500">{{ activeChat.title || 'New Chat'
                    }}</h2>
                <div class="flex items-center space-x-2">
                    <!-- <button @click="toggleTheme" class="w-10 h-10 rounded-lg flex items-center justify-center text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                        <i :class="isDarkMode ? 'fas fa-sun' : 'fas fa-moon'"></i>
                    </button> -->
                </div>
            </div>

            <!-- Welcome Screen (shown when no messages) -->
            <div v-if="activeChat.messages.length === 0"
                class="flex-1 flex items-center justify-center p-6 overflow-y-auto">
                <div class="max-w-3xl mx-auto text-center p-8">
                    <h1
                        class="text-4xl font-bold mb-4 bg-gradient-to-r from-green-500 to-green-600 bg-clip-text text-transparent">
                        Welcome to KubeSage</h1>
                    <p class="text-lg text-gray-600 dark:text-gray-400 mb-10">Your intelligent GenAI assistant for
                        seamless Kubernetes operations and troubleshooting</p>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div @click="usePrompt('Explain my cluster health status')"
                            class="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer flex flex-col items-center">
                            <i class="fas fa-heartbeat text-2xl text-green-500 mb-3"></i>
                            <span class="text-gray-700 dark:text-gray-300">Explain my cluster health status</span>
                        </div>
                        <div @click="usePrompt('Troubleshoot pod crashes in namespace default')"
                            class="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer flex flex-col items-center">
                            <i class="fas fa-bug text-2xl text-green-500 mb-3"></i>
                            <span class="text-gray-700 dark:text-gray-300">Troubleshoot pod crashes</span>
                        </div>
                        <div @click="usePrompt('Optimize resource usage in my cluster')"
                            class="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer flex flex-col items-center">
                            <i class="fas fa-tachometer-alt text-2xl text-green-500 mb-3"></i>
                            <span class="text-gray-700 dark:text-gray-300">Optimize resource usage</span>
                        </div>
                        <div @click="usePrompt('Explain best practices for Kubernetes security')"
                            class="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer flex flex-col items-center">
                            <i class="fas fa-shield-alt text-2xl text-green-500 mb-3"></i>
                            <span class="text-gray-700 dark:text-gray-300">Kubernetes security best practices</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Chat Messages -->
            <div v-else ref="chatMessagesContainer" class="flex-1 p-4 md:p-6 overflow-y-auto space-y-6 pb-20"
                @scroll="handleScroll">
                <div v-for="(message, index) in activeChat.messages" :key="index" :class="[
                    'flex',
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                ]">
                    <div :class="[
                        'flex max-w-[85%]',
                        message.role === 'user' ? 'flex-row-reverse' : 'flex-row'
                    ]">
                        <div :class="[
                            'w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0',
                            message.role === 'user' ? 'bg-green-500 ml-3' : 'bg-blue-500 mr-3'
                        ]">
                            <i
                                :class="message.role === 'user' ? 'fas fa-user text-white' : 'fas fa-robot text-white'"></i>
                        </div>
                        <div :class="[
                            'rounded-2xl p-4 shadow-sm',
                            message.role === 'user'
                                ? 'bg-gray-100 dark:bg-gray-800 rounded-tr-none border-l-4 border-green-500'
                                : 'bg-gray-100 dark:bg-gray-800 rounded-tl-none border-l-4 border-blue-500'
                        ]">
                            <div class="flex justify-between items-center mb-2 text-xs">
                                <span class="font-semibold text-gray-700 dark:text-gray-300">
                                    {{ message.role === 'user' ? 'You' : 'KubeSage' }}
                                </span>
                                <span class="text-gray-500 dark:text-gray-400">{{ formatTime(message.created_at)
                                    }}</span>
                            </div>
                            <div class="prose dark:prose-invert prose-sm max-w-none"
                                v-html="renderMarkdownWithButtons(message.content)"></div>
                        </div>
                    </div>
                </div>

                <!-- Streaming response -->
                <div v-if="isStreaming" class="flex justify-start">
                    <div class="flex max-w-[85%]">
                        <div
                            class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 bg-blue-500 mr-3">
                            <i class="fas fa-robot text-white"></i>
                        </div>
                        <div
                            class="rounded-2xl p-4 shadow-sm bg-gray-100 dark:bg-gray-800 rounded-tl-none border-l-4 border-blue-500">
                            <div class="flex justify-between items-center mb-2 text-xs">
                                <span class="font-semibold text-gray-700 dark:text-gray-300">KubeSage</span>
                                <span class="text-gray-500 dark:text-gray-400">{{ formatTime(new Date()) }}</span>
                            </div>
                            <div class="prose dark:prose-invert prose-sm max-w-none"
                                v-html="renderMarkdownWithButtons(streamingText)"></div>
                            <div v-if="!streamingText" class="flex space-x-1 mt-2">
                                <div class="w-2 h-2 rounded-full bg-blue-500 animate-bounce"
                                    style="animation-delay: 0ms"></div>
                                <div class="w-2 h-2 rounded-full bg-blue-500 animate-bounce"
                                    style="animation-delay: 200ms"></div>
                                <div class="w-2 h-2 rounded-full bg-blue-500 animate-bounce"
                                    style="animation-delay: 400ms"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Kubectl Commands Section -->
                <div v-if="kubectlCommands.length > 0" class="ml-[5%] max-w-[85%] space-y-4">
                    <div v-for="(cmd, cmdIndex) in kubectlCommands" :key="cmdIndex" class="flex flex-col space-y-2">
                        <div
                            class="rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 border-l-4 border-l-green-500">
                            <div
                                class="flex justify-between items-center px-4 py-2 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                                <span
                                    class="text-xs font-mono font-semibold text-green-600 dark:text-green-500">KUBECTL</span>
                                <div class="flex space-x-2">
                                    <button @click="copyToClipboard(cmd)"
                                        class="text-xs px-2 py-1 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 rounded flex items-center space-x-1 transition-colors">
                                        <i class="fas fa-copy"></i>
                                        <span>Copy</span>
                                    </button>
                                    <button @click="executeKubectlCommand(cmd, cmdIndex)"
                                        class="text-xs px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 hover:bg-green-200 dark:hover:bg-green-800/30 rounded flex items-center space-x-1 transition-colors">
                                        <i class="fas fa-play"></i>
                                        <span>Execute</span>
                                    </button>
                                </div>
                            </div>
                            <pre
                                class="p-4 text-sm font-mono overflow-x-auto text-gray-800 dark:text-gray-300"><code>{{ cmd }}</code></pre>
                        </div>

                        <!-- Command Execution Result -->
                        <div v-if="commandResults[cmdIndex]"
                            class="rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 border-l-4 border-l-blue-500">
                            <div
                                class="px-4 py-2 bg-blue-50 dark:bg-blue-900/20 border-b border-gray-200 dark:border-gray-700">
                                <span class="text-xs font-semibold text-blue-600 dark:text-blue-400">Execution
                                    Result</span>
                            </div>

                            <!-- Display table data if available -->
                            <div v-if="commandResults[cmdIndex].type === 'table' && commandResults[cmdIndex].data"
                                class="p-4 overflow-x-auto">
                                <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                                    <thead>
                                        <tr>
                                            <th v-for="(_, key) in commandResults[cmdIndex].data[0]" :key="key"
                                                class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider bg-gray-50 dark:bg-gray-800">
                                                {{ key.charAt(0).toUpperCase() + key.slice(1) }}
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody
                                        class="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-800">
                                        <tr v-for="(row, rowIndex) in commandResults[cmdIndex].data" :key="rowIndex"
                                            class="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                                            <td v-for="(value, key) in row" :key="key"
                                                class="px-4 py-2 text-sm text-gray-700 dark:text-gray-300">
                                                {{ value }}
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>

                            <!-- Display plain text result if not a table -->
                            <pre v-else
                                class="p-4 text-sm font-mono overflow-x-auto text-gray-800 dark:text-gray-300"><code>{{ typeof commandResults[cmdIndex] === 'string' ? commandResults[cmdIndex] : JSON.stringify(commandResults[cmdIndex], null, 2) }}</code></pre>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Scroll to bottom button -->
            <button v-if="showScrollToBottom" @click="scrollToBottom"
                class="fixed bottom-24 right-6 w-10 h-10 rounded-full bg-green-500 text-white flex items-center justify-center shadow-lg hover:bg-green-600 transition-all duration-200 z-50">
                <i class="fas fa-arrow-down"></i>
            </button>

            <!-- Chat Input -->
<div class="sticky bottom-0 bg-white/90 dark:bg-gray-900/90 backdrop-blur-md border-t border-gray-200 dark:border-gray-700 p-4 z-30">
    <div class="flex items-end space-x-2 bg-gray-100 dark:bg-gray-800 rounded-xl p-3 shadow-sm focus-within:ring-2 focus-within:ring-green-500 transition-all">
        <textarea v-model="newMessage" @keyup.enter.exact="sendMessage" ref="textarea"
            placeholder="Ask KubeSage about your Kubernetes cluster..." 
            class="flex-1 bg-transparent border-0 focus:ring-0 focus:outline-none resize-none max-h-32 text-gray-700 dark:text-gray-300 placeholder-gray-500 dark:placeholder-gray-400"
            rows="1"></textarea>
        <button @click="sendMessage" :disabled="!newMessage.trim()" 
            class="flex-shrink-0 w-10 h-10 rounded-lg bg-gradient-to-r from-green-500 to-green-600 text-white flex items-center justify-center shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200">
            <i class="fas fa-paper-plane"></i>
        </button>
    </div>
</div>

        </div>
    </div>
</template>

<script>
import { ref, watch, nextTick, onMounted, computed, onUnmounted } from 'vue';
import axios from 'axios';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import { NButton, useMessage } from 'naive-ui';
import { useStorage } from '@vueuse/core';

export default {
    name: 'ChatApp',
    components: {
        NButton
    },
    setup() {
        const host = `${import.meta.env.VITE_CHAT_API_HOST}/chat/`;
        const kubectlApiHost = `${import.meta.env.VITE_AIAGENT_API_HOST}`;
        const chatSessions = ref([]);
        const activeChatSessionId = ref(null);
        const activeChat = ref({ messages: [], title: '' });
        const newMessage = ref('');
        const textarea = ref(null);
        const chatMessagesContainer = ref(null);
        const isSidebarVisible = ref(true);
        const isMinimized = ref(false);
        const isTyping = ref(false);
        const sessionQuestionsCache = ref({});
        const message = useMessage();
        const kubectlCommands = ref([]);
        const commandResults = ref({});
        const showScrollToBottom = ref(false);

        // Streaming related refs
        const isStreaming = ref(false);
        const streamingText = ref('');
        const streamController = ref(null);

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

        // Function to render markdown with copy and execute buttons for code blocks
        const renderMarkdownWithButtons = (text) => {
            if (!text) return '';

            // First, render the markdown
            let rendered = md.render(text);

            // Then add buttons to code blocks
            rendered = rendered.replace(/<pre><code class="language-(\w+)">([\s\S]*?)<\/code><\/pre>/g,
                (match, language, code) => {
                    const isCommand = language === 'bash' || language === 'sh';
                    const commandClass = isCommand ? 'executable-command' : '';

                    return `
                        <div class="relative rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 ${isCommand ? 'border-l-4 border-l-green-500' : ''}">
                            <div class="flex justify-between items-center px-4 py-2 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                                <span class="text-xs font-mono font-semibold text-gray-600 dark:text-gray-400 uppercase">${language}</span>
                                <div class="flex space-x-2">
                                    <button class="code-action-btn copy-btn text-xs px-2 py-1 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 rounded flex items-center space-x-1 transition-colors" data-code="${encodeURIComponent(code.trim())}">
                                        <i class="fas fa-copy"></i>
                                        <span>Copy</span>
                                    </button>
                                    ${isCommand ? `
                                    <button class="code-action-btn execute-btn text-xs px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 hover:bg-green-200 dark:hover:bg-green-800/30 rounded flex items-center space-x-1 transition-colors" data-code="${encodeURIComponent(code.trim())}">
                                        <i class="fas fa-play"></i>
                                        <span>Execute</span>
                                    </button>
                                    ` : ''}
                                </div>
                            </div>
                            <pre class="p-4 text-sm font-mono overflow-x-auto text-gray-800 dark:text-gray-300"><code class="language-${language}">${code}</code></pre>
                        </div>
                    `;
                }
            );

            return rendered;
        };

        // Function to copy code to clipboard
        const copyToClipboard = (text) => {
            navigator.clipboard.writeText(text)
                .then(() => {
                    message.success('Code copied to clipboard');
                })
                .catch(err => {
                    console.error('Failed to copy: ', err);
                    message.error('Failed to copy code');
                });
        };

        // Function to execute command
        const executeCommand = async (command) => {
            try {
                message.info('Executing command...');

                // Send the command to the backend for execution
                const response = await axios.post(
                    `${import.meta.env.VITE_AIAGENT_API_HOST}/execute`,
                    { command, session_id: activeChatSessionId.value },
                    { headers: getAuthHeaders() }
                );

                // Add the execution result to the chat
                activeChat.value.messages.push({
                    role: 'bot',
                    content: `**Command Execution Result:**\n\`\`\`\n${response.data.result}\n\`\`\``,
                    created_at: new Date().toISOString()
                });

                message.success('Command executed successfully');
                scrollToBottom();
            } catch (error) {
                console.error('Command execution failed:', error);

                // Add error message to the chat
                activeChat.value.messages.push({
                    role: 'bot',
                    content: `**Command Execution Failed:**\n\`\`\`\n${error.response?.data?.error || error.message}\n\`\`\``,
                    created_at: new Date().toISOString()
                });

                message.error('Command execution failed');
                scrollToBottom();
            }
        };

        // Function to extract kubectl commands from response
        const extractKubectlCommands = async (responseText) => {
            try {
                console.log('start');

                // Send the response to the kubectl-command API
                const response = await axios.post(
                    `${kubectlApiHost}/kubectl-command`,
                    { query: responseText },
                    {
                        headers: {
                            'accept': 'application/json',
                            'x-api-key': 'test-key',
                            'Content-Type': 'application/json'
                        }
                    }
                );
                console.log('kubectl response:', response.data.kubectl_command);

                // Check if the response contains commands
                if (response.data && response.data.kubectl_command && Array.isArray(response.data.kubectl_command)) {
                    kubectlCommands.value = response.data.kubectl_command;
                } else if (response.data && response.data.kubectl_command && typeof response.data.kubectl_command === 'string') {
                    // Handle case where kubectl_command is a single string
                    kubectlCommands.value = [response.data.kubectl_command];
                } else {
                    kubectlCommands.value = [];
                }
                scrollToBottom();
            } catch (error) {
                console.error('Failed to extract kubectl commands:', error);
                kubectlCommands.value = [];
            }
        };

        const executeKubectlCommand = async (command, cmdIndex) => {
            try {
                message.info(`Executing kubectl command: ${command}`);

                // Send the command to the execute API
                const response = await axios.post(
                    `${kubectlApiHost}/execute`,
                    { execute: command },
                    {
                        headers: {
                            'accept': 'application/json',
                            'x-api-key': 'test-key',
                            'Content-Type': 'application/json'
                        }
                    }
                );

                console.log('Execute API response:', response.data);

                // Check if we have structured execution result data
                if (response.data.execution_result && response.data.execution_result.type === 'table') {
                    // Store the structured table data
                    commandResults.value[cmdIndex] = response.data.execution_result;
                } else if (response.data.execution_result && typeof response.data.execution_result === 'object') {
                    // Store other structured data
                    commandResults.value[cmdIndex] = response.data.execution_result;
                } else if (response.data.result) {
                    // Fallback to plain text result if available
                    commandResults.value[cmdIndex] = response.data.result;
                } else {
                    // Default success message
                    commandResults.value[cmdIndex] = 'Command executed successfully';
                }

                message.success('Command executed successfully');
                scrollToBottom();
            } catch (error) {
                console.error('Kubectl command execution failed:', error);

                // Check if we have structured error data
                if (error.response?.data?.execution_error) {
                    commandResults.value[cmdIndex] = error.response.data.execution_error;
                } else {
                    // Fallback to error message
                    commandResults.value[cmdIndex] = error.response?.data?.error || error.message;
                }

                message.error('Command execution failed');
                scrollToBottom();
            }
        };

        // Implement streaming functionality
        const streamResponse = async (userMessage) => {
            try {
                // Reset streaming state
                isStreaming.value = true;
                streamingText.value = '';

                // Create a new AbortController for this request
                streamController.value = new AbortController();
                const signal = streamController.value.signal;

                // Send the streaming request
                const response = await fetch(`${host}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${getAuthToken()}`
                    },
                    body: JSON.stringify({
                        content: userMessage,
                        session_id: activeChatSessionId.value
                    }),
                    signal
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const reader = response.body.content.getReader();
                const decoder = new TextDecoder();

                let done = false;
                let fullText = '';

                while (!done) {
                    const { value, done: readerDone } = await reader.read();
                    done = readerDone;

                    if (value) {
                        const chunk = decoder.decode(value, { stream: !done });
                        fullText += chunk;
                        streamingText.value = fullText;
                        scrollToBottom();
                    }
                }

                // Add the complete response to messages
                activeChat.value.messages.push({
                    role: 'bot',
                    content: fullText,
                    created_at: new Date().toISOString()
                });

                // Extract kubectl commands from the response
                await extractKubectlCommands(fullText);

                // Reset streaming state
                isStreaming.value = false;
                streamingText.value = '';

                // If this is the first message, generate a title
                if (activeChat.value.messages.length === 2) {
                    try {
                        const titleResponse = await axios.post(
                            `${host}sessions/${activeChatSessionId.value}/title`,
                            {},
                            { headers: getAuthHeaders() }
                        );

                        // Update title in UI and session list
                        activeChat.value.title = titleResponse.data.title;
                        const sessionIndex = chatSessions.value.findIndex(s => s.session_id === activeChatSessionId.value);
                        if (sessionIndex !== -1) {
                            chatSessions.value[sessionIndex].title = titleResponse.data.title;
                        }
                    } catch (error) {
                        console.error('Failed to generate title:', error);
                    }
                }

                scrollToBottom();
            } catch (error) {
                if (error.name === 'AbortError') {
                    console.log('Fetch aborted');
                } else {
                    console.error('Streaming error:', error);

                    // Add error message to chat
                    activeChat.value.messages.push({
                        role: 'bot',
                        content: "Sorry, I encountered an error. Please try again.",
                        created_at: new Date().toISOString()
                    });
                }

                // Reset streaming state
                isStreaming.value = false;
                streamingText.value = '';
                scrollToBottom();
            }
        };

        // Cancel streaming if in progress
        const cancelStreaming = () => {
            if (isStreaming.value && streamController.value) {
                streamController.value.abort();
                isStreaming.value = false;
                streamingText.value = '';
            }
        };

        // Add event listeners for copy and execute buttons after DOM updates
        watch(
            () => activeChat.value.messages,
            () => {
                nextTick(() => {
                    // Add event listeners to copy buttons
                    document.querySelectorAll('.copy-btn').forEach(btn => {
                        btn.addEventListener('click', (e) => {
                            const code = decodeURIComponent(e.currentTarget.getAttribute('data-code'));
                            copyToClipboard(code);
                        });
                    });

                    // Add event listeners to execute buttons
                    document.querySelectorAll('.execute-btn').forEach(btn => {
                        btn.addEventListener('click', (e) => {
                            const command = decodeURIComponent(e.currentTarget.getAttribute('data-code'));
                            executeCommand(command);
                        });
                    });
                });
            },
            { deep: true }
        );

        // Format timestamp
        const formatTime = (timestamp) => {
            if (!timestamp) return '';
            const date = new Date(timestamp);
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
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
            colorScheme.value = isDarkMode.value ? 'dark' : 'light';
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
                kubectlCommands.value = [];
                commandResults.value = {};
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

        // Scroll to bottom function
const scrollToBottom = () => {
    nextTick(() => {
        setTimeout(() => {
            if (chatMessagesContainer.value) {
                // Calculate the scroll position accounting for the input height
                const inputHeight = document.querySelector('.chat-input-container')?.offsetHeight || 0;
                chatMessagesContainer.value.scrollTop = chatMessagesContainer.value.scrollHeight - chatMessagesContainer.value.clientHeight + inputHeight;
                
                // Double check if scroll worked correctly
                if (chatMessagesContainer.value.scrollTop + chatMessagesContainer.value.clientHeight < chatMessagesContainer.value.scrollHeight - 20) {
                    // If not, try one more time with a longer delay
                    setTimeout(() => {
                        chatMessagesContainer.value.scrollTop = chatMessagesContainer.value.scrollHeight;
                    }, 100);
                }
            }
        }, 50);
    });
};

        // Handle scroll events
        const handleScroll = () => {
            if (chatMessagesContainer.value) {
                const { scrollTop, scrollHeight, clientHeight } = chatMessagesContainer.value;
                // Show scroll button when not at bottom
                showScrollToBottom.value = scrollTop + clientHeight < scrollHeight - 50;
            }
        };

        // Fetch chat sessions on component mount
        onMounted(async () => {
            // Apply dark mode from localStorage and update classes
            updateDarkModeClasses();

            // Add resize listener for textarea
            if (textarea.value) {
                textarea.value.addEventListener('input', autoResizeTextarea);
            }

            await fetchChatSessions();
            if (chatSessions.value.length > 0) {
                loadChat(chatSessions.value[0].session_id);
            } else {
                startNewChat();
            }

            // Initial scroll to bottom
            scrollToBottom();
        });

        // Clean up event listeners
        onUnmounted(() => {
            if (textarea.value) {
                textarea.value.removeEventListener('input', autoResizeTextarea);
            }
            // Cancel any ongoing streaming
            cancelStreaming();
        });

        // Auto-resize textarea function
        const autoResizeTextarea = () => {
            if (textarea.value) {
                textarea.value.style.height = 'auto';
                textarea.value.style.height = `${Math.min(textarea.value.scrollHeight, 150)}px`;
            }
        };

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
                // Clear previous command results when starting a new chat
                commandResults.value = {};
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
                kubectlCommands.value = []; // Clear kubectl commands for new chat
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
                    return truncated;
                }
            }

            return null;
        };

        const extractUserQuestion = (content) => {
            // Check if the content contains "User question:"
            if (content.includes("User question:")) {
                // Extract everything after "User question:"
                return content.split("User question:")[1].trim();
            }

            // If "User question:" is not found, return the original content
            return content;
        };

        // Modify the loadChat function to cache the first user question
        const loadChat = async (sessionId) => {
            try {
                // Cancel any ongoing streaming
                cancelStreaming();

                // Clear previous command results when loading a chat
                commandResults.value = {};
                const response = await axios.get(`${host}history/${sessionId}`, {
                    headers: getAuthHeaders()
                });
                activeChatSessionId.value = sessionId;
                // Process messages to extract only user questions
                const processedMessages = response.data.messages.map(msg => {
                    if (msg.role === 'user') {
                        return {
                            ...msg,
                            content: extractUserQuestion(msg.content)
                        };
                    }
                    return msg;
                });

                // Cache the first user question from this session
                const userMessages = processedMessages.filter(msg => msg.role === 'user');
                if (userMessages.length > 0) {
                    const question = userMessages[0].content;
                    const truncated = question.length > 30 ? question.substring(0, 30) + '...' : question;
                    sessionQuestionsCache.value[sessionId] = truncated;
                    activeChat.value = {
                        messages: processedMessages,
                        title: truncated
                    };
                }

                // Clear kubectl commands when loading a chat
                kubectlCommands.value = [];

                // If there are bot messages, extract kubectl commands from the last one
                const botMessages = processedMessages.filter(msg => msg.role === 'bot');
                if (botMessages.length > 0) {
                    const lastBotMessage = botMessages[botMessages.length - 1];
                    extractKubectlCommands(lastBotMessage.content);
                }

                scrollToBottom();
            } catch (error) {
                console.error('Failed to load chat history:', error);
            }
        };

        // Get auth token helper
        const getAuthToken = () => {
            try {
                return JSON.parse(localStorage.getItem('accessToken')).value;
            } catch (error) {
                console.error('Authentication error. Please login again.');
                return '';
            }
        };

        // Get auth headers helper
        const getAuthHeaders = () => {
            const token = getAuthToken();
            return token ? { Authorization: `Bearer ${token}` } : {};
        };

        // Send a message to the active chat session
        const sendMessage = async () => {
            if (newMessage.value.trim() === '') return;

            // Cancel any ongoing streaming
            cancelStreaming();

            try {
                // Clear previous command results when sending a new message
                commandResults.value = {};
                // Add user message to the UI
                activeChat.value.messages.push({
                    role: 'user',
                    content: newMessage.value,
                    created_at: new Date().toISOString()
                });
                const userMessage = newMessage.value;
                newMessage.value = '';

                // Auto-resize textarea
                if (textarea.value) {
                    textarea.value.style.height = 'auto';
                }

                // If this is the first message, cache it as the question for this session
                if (activeChat.value.messages.length === 1) {
                    const truncated = userMessage.length > 30 ? userMessage.substring(0, 30) + '...' : userMessage;
                    sessionQuestionsCache.value[activeChatSessionId.value] = truncated;
                }

                // Clear kubectl commands when sending a new message
                kubectlCommands.value = [];

                // Scroll to bottom after adding user message
                scrollToBottom();

                // Use streaming response
                await streamResponse(userMessage);

            } catch (error) {
                console.error('Failed to send message:', error);

                // Display an error message to the user
                activeChat.value.messages.push({
                    role: 'bot',
                    content: "Sorry, I encountered an error. Please try again.",
                    created_at: new Date().toISOString()
                });

                scrollToBottom();
            }
        };

        // Auto-resize textarea
        watch(newMessage, () => {
            nextTick(() => {
                autoResizeTextarea();
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
            isStreaming,
            streamingText,
            sessionQuestionsCache,
            kubectlCommands,
            showScrollToBottom,
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
            getUserQuestion,
            renderMarkdownWithButtons,
            copyToClipboard,
            executeCommand,
            executeKubectlCommand,
            commandResults,
            scrollToBottom,
            handleScroll,
        };
    },
};
</script>

<style>
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Import Font Awesome */
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');
/* Import highlight.js styles */
@import url('https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/github.min.css');

/* Dark mode override for highlight.js */
.dark .hljs {
    background: #2d2d2d;
    color: #e6e6e6;
}

/* Ensure proper spacing at the bottom of chat messages */
.chat-messages-container {
    padding-bottom: 80px !important; /* Ensure enough space for the input */
}

/* Ensure chat input is always visible */
.chat-input-container {
    position: sticky;
    bottom: 0;
    z-index: 50 !important;
    background-color: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border-top: 1px solid rgba(0, 0, 0, 0.1);
}

.dark .chat-input-container {
    background-color: rgba(17, 24, 39, 0.95);
    border-top: 1px solid rgba(255, 255, 255, 0.1);
}

/* Ensure scroll to bottom button is visible */
.scroll-to-bottom-btn {
    z-index: 60 !important;
}

textarea {
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
}

textarea:focus {
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
}

/* Override any browser-specific styling */
textarea::-moz-focus-inner {
    border: 0;
}

textarea:-moz-focusring {
    outline: none;
}

/* Ensure the container gets the focus styling instead */
.chat-input-container .focus-within\:ring-2:focus-within {
    box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.5);
}

/* Custom animation for typing indicator */
@keyframes bounce {

    0%,
    100% {
        transform: translateY(0);
    }

    50% {
        transform: translateY(-4px);
    }
}

.animate-bounce {
    animation: bounce 1s infinite;
}

/* Custom scrollbar */
::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-track {
    background: transparent;
}

::-webkit-scrollbar-thumb {
    @apply bg-green-500/20 rounded hover:bg-green-500/40;
}

.dark ::-webkit-scrollbar-thumb {
    @apply bg-green-500/30 hover:bg-green-500/50;
}

/* Prose styles for markdown content */
.prose pre {
    @apply bg-gray-50 dark:bg-gray-800/50 rounded-lg overflow-x-auto;
}

.prose code {
    @apply font-mono text-sm;
}

.prose p {
    @apply mb-3;
}

.prose p:last-child {
    @apply mb-0;
}

.prose h1,
.prose h2,
.prose h3,
.prose h4 {
    @apply font-semibold text-gray-800 dark:text-gray-200 mb-2;
}

.prose ul,
.prose ol {
    @apply pl-5 mb-3;
}

.prose li {
    @apply mb-1;
}

.prose blockquote {
    @apply border-l-4 border-gray-300 dark:border-gray-600 pl-4 italic;
}

.prose a {
    @apply text-blue-600 dark:text-blue-400 hover:underline;
}

.prose table {
    @apply w-full border-collapse mb-3;
}

.prose th {
    @apply bg-gray-100 dark:bg-gray-800 text-left p-2 border border-gray-300 dark:border-gray-700;
}

.prose td {
    @apply p-2 border border-gray-300 dark:border-gray-700;
}
</style>
