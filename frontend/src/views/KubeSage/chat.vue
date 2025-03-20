<template>
    <n-config-provider :theme="theme">
      <n-layout class="h-screen" :class="isDark ? 'bg-dark text-white' : 'bg-light text-dark'">
        <n-layout-sider width="250" :class="isDark ? 'bg-sidebar' : 'bg-light-sidebar'" class="p-4 shadow-md">
          <n-button type="primary" block ghost class="mb-4">+ New conversation</n-button>
          <n-scrollbar style="height: 75vh">
            <n-list bordered>
              <n-list-item v-for="(conversation, index) in conversations" :key="index">
                <n-ellipsis :tooltip="conversation">{{ conversation }}</n-ellipsis>
              </n-list-item>
            </n-list>
          </n-scrollbar>
          <div class="mt-4 space-y-2">
            <n-button text block @click="clearChat">Clear conversations</n-button>
            <n-button text block>Model Parameters</n-button>
            <n-button text block @click="toggleTheme">
              {{ isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode' }}
            </n-button>
            <n-button text block>Language</n-button>
            <n-button text block>Feedback</n-button>
            <n-button text block>Sign out</n-button>
          </div>
        </n-layout-sider>
  
        <n-layout>
          <n-layout-content :class="isDark ? 'bg-chat' : 'bg-chat-light'" class="flex flex-col justify-between p-4 h-full">
            <n-scrollbar class="flex-1">
              <transition-group name="fade" tag="div">
                <div v-for="(msg, index) in messages" :key="index" class="my-4">
                  <n-card :title="msg.sender" size="small" :class="isDark ? 'bg-message text-white' : 'bg-message-light text-dark'">
                    <p>{{ msg.text }}</p>
                  </n-card>
                </div>
              </transition-group>
            </n-scrollbar>
            <div class="border-t pt-3 flex items-center" :class="isDark ? 'border-gray-700' : 'border-gray-300'">
              <n-input
                v-model="input"
                placeholder="Write a message..."
                class="flex-1 mr-2"
                :class="isDark ? 'bg-input text-white' : 'bg-input-light text-dark'"
                @keydown.enter="sendMessage"
              />
              <n-button type="primary" ghost @click="sendMessage">
                <template #icon>
                  <n-icon><Send /></n-icon>
                </template>
              </n-button>
            </div>
          </n-layout-content>
        </n-layout>
      </n-layout>
    </n-config-provider>
  </template>
  
  <script setup>
  import { ref, computed, watch } from 'vue'
  import { darkTheme, NButton, NLayout, NLayoutSider, NLayoutContent, NList, NListItem, NEllipsis, NCard, NInput, NIcon, NScrollbar, NConfigProvider } from 'naive-ui'
  import { Send } from '@vicons/ionicons5'
  
  const conversations = [
    'Today’s Weather in Beijing',
    'Testing Django Projects',
    'Python Exception Handling',
    'Convert JS to Python',
    'Setting User-Agent in Python',
    'Feedback and more...'
  ]
  
  const messages = ref([
    { sender: 'Assistant', text: 'Hello! How can I help you today?' }
  ])
  
  const input = ref('')
  const isDark = ref(localStorage.getItem('theme') === 'dark' || !localStorage.getItem('theme'))
  const theme = computed(() => (isDark.value ? darkTheme : null))
  
  watch(isDark, (val) => {
    localStorage.setItem('theme', val ? 'dark' : 'light')
  })
  
  function sendMessage() {
    if (!input.value.trim()) return
    const userMessage = { sender: 'You', text: input.value }
    messages.value.push(userMessage)
  
    // Simulate dynamic bot response
    setTimeout(() => {
      const botResponse = {
        sender: 'Assistant',
        text: generateBotReply(input.value)
      }
      messages.value.push(botResponse)
    }, 700)
  
    input.value = ''
  }
  
  function generateBotReply(userText) {
    const responses = [
      "That's interesting! Can you elaborate?",
      "Let me think... 🤔",
      "Here's what I found on that topic!",
      "Good question! I'll look it up.",
      "Can you clarify your request?"
    ]
    return responses[Math.floor(Math.random() * responses.length)]
  }
  
  function toggleTheme() {
    isDark.value = !isDark.value
  }
  
  function clearChat() {
    messages.value = [
      { sender: 'Assistant', text: 'Chat cleared! How can I assist now?' }
    ]
  }
  </script>
  
  <style scoped>
  .bg-dark {
    background-color: #202123;
  }
  .bg-light {
    background-color: #f5f6fa;
  }
  .bg-sidebar {
    background-color: #343541;
  }
  .bg-light-sidebar {
    background-color: #ffffff;
  }
  .bg-chat {
    background-color: #202123;
  }
  .bg-chat-light {
    background: linear-gradient(135deg, #e0eafc, #cfdef3);
  }
  .bg-message {
    background-color: #3c3f4a;
    border-radius: 14px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
  }
  .bg-message-light {
    background-color: #ffffff;
    border-radius: 14px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  }
  .bg-input {
    background-color: #343541;
  }
  .bg-input-light {
    background-color: #ffffff;
  }
  .text-white {
    color: white;
  }
  .text-dark {
    color: #222;
  }
  .fade-enter-active,
  .fade-leave-active {
    transition: all 0.4s ease;
  }
  .fade-enter-from,
  .fade-leave-to {
    opacity: 0;
    transform: translateY(20px);
  }
  </style>
  