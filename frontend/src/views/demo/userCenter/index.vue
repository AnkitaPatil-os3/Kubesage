<template>
  <div class="app-container" :class="{ 'dark-mode': isDarkMode }">
    <div class="main-content">
      <!-- Header -->
      <div class="user-header">
        <h2>User Profile</h2>
       <!--- <div class="header-actions">
          <button class="toggle-theme-btn" @click="toggleTheme">
            <i :class="isDarkMode ? 'fas fa-sun' : 'fas fa-moon'"></i>
          </button>
        </div> -->
      </div>
 
      <!-- User Profile Card -->
      <div class="profile-card">
        <div class="profile-avatar">
          <i class="fas fa-user"></i>
        </div>
        <div class="profile-info">
          <h1 class="profile-name">Welcome, {{ username }}</h1>
          <p class="profile-description">
            Streamline your observability journey with KubeSage: Advanced monitoring and analytics in one platform.
          </p>
        </div>
      </div>
 
      <!-- Dashboard Cards -->
      <div class="dashboard-grid">
        <div class="dashboard-card" @click="goToAnalyze">
          <div class="card-icon"><i class="fas fa-chart-line"></i></div>
          <div class="card-title">Kubernetes Analyzer</div>
          <div class="card-description">Analyze your Kubernetes resources and identify issues</div>
          <button class="action-btn">Go to Analyzer</button>
        </div>
        
        <div class="dashboard-card" @click="goToChat">
          <div class="card-icon"><i class="fas fa-comment-dots"></i></div>
          <div class="card-title">KubeSage Chat</div>
          <div class="card-description">Chat with KubeSage AI about your Kubernetes environment</div>
          <button class="action-btn">Start Chatting</button>
        </div>
        
        <div class="dashboard-card" @click="goToSettings">
          <div class="card-icon"><i class="fas fa-cog"></i></div>
          <div class="card-title">Settings</div>
          <div class="card-description">Manage your account settings and preferences</div>
          <button class="action-btn">Manage Settings</button>
        </div>
        
       
      </div>
    </div>
  </div>
</template>
 
<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
 
const router = useRouter();
const username = ref(''); // Initialize as an empty ref
const isDarkMode = ref(localStorage.getItem('darkMode') === 'true');
 
// Toggle light/dark mode
const toggleTheme = () => {
  isDarkMode.value = !isDarkMode.value;
  localStorage.setItem('darkMode', isDarkMode.value);
  updateDarkModeClasses();
};
 
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
 
// Navigation functions
const goToAnalyze = () => {
  router.push('cluster-analysis');
};
 
const goToChat = () => {
  router.push('chat-with-kubesage');
};
 
const goToSettings = () => {
  router.push('auth-settings');
  // Placeholder for settings page
  console.log('Navigate to settings page');
};
 
const goToDocumentation = () => {
  // Placeholder for documentation page
  console.log('Navigate to documentation page');
};
 
onMounted(() => {
  try {
    // Retrieve user information from localStorage
    const userInfoData = JSON.parse(localStorage.getItem('userInfo'));
    
    // Check if userInfo exists and has the nested value property
    if (userInfoData && userInfoData.value) {
      // Access the nested properties correctly
      username.value = userInfoData.value.nickname ||
                       userInfoData.value.userName ||
                       'User';
    } else {
      console.warn("User information not found or has invalid structure in localStorage.");
      username.value = 'User'; // Default fallback
    }
  } catch (error) {
    console.error("Error parsing user information:", error);
    username.value = 'User'; // Fallback in case of parsing error
  }
  
  // Apply dark mode settings
  updateDarkModeClasses();
});
</script>
 
<style scoped>
/* Import Font Awesome */
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');
 
/* Main container */
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: #f8f9fa;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  width: 100%;
}
 
.app-container.dark-mode {
  background-color: #1a1a1a;
  color: #f0f0f0;
}
 
.main-content {
  flex: 1;
  padding: 20px;
  width: 100%;
}
 
/* Header */
.user-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background-color: #ffffff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  margin-bottom: 24px;
}
 
.app-container.dark-mode .user-header {
  background-color: #222222;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}
 
.user-header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: #111827;
}
 
.app-container.dark-mode .user-header h2 {
  color: #f0f0f0;
}
 
.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}
 
.toggle-theme-btn {
  background: transparent;
  border: none;
  color: #6b7280;
  cursor: pointer;
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s ease;
}
 
.toggle-theme-btn:hover {
  background-color: #f3f4f6;
}
 
.app-container.dark-mode .toggle-theme-btn {
  color: #9ca3af;
}
 
.app-container.dark-mode .toggle-theme-btn:hover {
  background-color: #2d2d2d;
}
 
/* Profile Card */
.profile-card {
  background-color: #ffffff;
  border-radius: 12px;
  padding: 32px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  margin-bottom: 32px;
  display: flex;
  align-items: center;
  gap: 24px;
  width: 100%;
}
 
.app-container.dark-mode .profile-card {
  background-color: #222222;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}
 
.profile-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background-color: #4f46e5;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
}
 
.profile-info {
  flex: 1;
}
 
.profile-name {
  font-size: 2rem;
  font-weight: 700;
  margin: 0 0 12px 0;
  color: #111827;
  background: linear-gradient(90deg, #4f46e5, #8b5cf6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
 
.app-container.dark-mode .profile-name {
  color: #f0f0f0;
}
 
.profile-description {
  font-size: 1.1rem;
  color: #6b7280;
  margin: 0;
  line-height: 1.5;
}
 
.app-container.dark-mode .profile-description {
  color: #9ca3af;
}
 
/* Dashboard Grid */
.dashboard-grid {
  text-align: center;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(480px, 1fr));
  gap: 24px;
  width: 100%;
}
 
.dashboard-card {
  background-color: #ffffff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  cursor: pointer;
}
 
.app-container.dark-mode .dashboard-card {
  background-color: #222222;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}
 
.dashboard-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
}
 
.app-container.dark-mode .dashboard-card:hover {
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
}
 
.card-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background-color: #e0e7ff;
  color: #4f46e5;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  font-size: 24px;
}
 
.app-container.dark-mode .card-icon {
  background-color: #312e81;
  color: #e0e7ff;
}
 
.card-title {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 8px;
  color: #111827;
}
 
.app-container.dark-mode .card-title {
  color: #f0f0f0;
}
 
.card-description {
  font-size: 0.9rem;
  color: #6b7280;
  margin-bottom: 16px;
  line-height: 1.5;
}
 
.app-container.dark-mode .card-description {
  color: #9ca3af;
}
 
.action-btn {
  padding: 8px 16px;
  background-color: #4f46e5;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s ease;
  margin-top: auto;
}
 
.action-btn:hover {
  background-color: #4338ca;
}
 
/* Responsive adjustments */
@media (max-width: 768px) {
  .profile-card {
    flex-direction: column;
    text-align: center;
    padding: 24px;
  }
  
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}
</style>
 
 