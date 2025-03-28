<template>
    <div class="app-container" :class="{ 'dark-mode': isDarkMode }">
      <div class="main-content">
        <!-- Header -->
        <div class="user-header">
          <h2>User Profile</h2>
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
            <n-button type="primary" class="card-button">Go to Analyzer</n-button>
          </div>
          
          <div class="dashboard-card" @click="goToChat">
            <div class="card-icon accent-1"><i class="fas fa-comment-dots"></i></div>
            <div class="card-title">KubeSage Chat</div>
            <div class="card-description">Chat with KubeSage AI about your Kubernetes environment</div>
            <n-button type="primary" class="card-button">Start Chatting</n-button>
          </div>
          
          <div class="dashboard-card" @click="goToSettings">
            <div class="card-icon accent-2"><i class="fas fa-cog"></i></div>
            <div class="card-title">Settings</div>
            <div class="card-description">Manage your account settings and preferences</div>
            <n-button type="primary" class="card-button">Manage Settings</n-button>
          </div>
        </div>
      </div>
    </div>
  </template>
   
  <script setup>
  import { ref, onMounted, computed } from 'vue';
  import { useRouter } from 'vue-router';
  import { NButton } from 'naive-ui';
  
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
    background-image: linear-gradient(to bottom right, #f8f9fa, #e8f5e9);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
    width: 100%;
  }
  
  .app-container.dark-mode {
    background-color: #1a1a1a;
    background-image: linear-gradient(to bottom right, #1a1a1a, #0d2d0f);
    color: #f0f0f0;
  }
  
  .main-content {
    flex: 1;
    padding: 20px;
    width: 100%;
    max-width: 100%;
    margin: 0 auto;
  }
  
  /* Header */
  .user-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    background-color: #ffffff;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    margin-bottom: 24px;
    border-left: 4px solid #10BC3B;
  }
  
  .app-container.dark-mode .user-header {
    background-color: #222222;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    border-left: 4px solid #10BC3B;
  }
  
  .user-header h2 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: #10BC3B;
    letter-spacing: 0.5px;
  }
  
  .app-container.dark-mode .user-header h2 {
    color: #10BC3B;
  }
  
  /* Profile Card */
  .profile-card {
    background-color: #ffffff;
    background-image: linear-gradient(135deg, #ffffff, #f5fff7);
    border-radius: 16px;
    padding: 32px;
    box-shadow: 0 8px 24px rgba(16, 188, 59, 0.08);
    margin-bottom: 32px;
    display: flex;
    align-items: center;
    gap: 24px;
    width: 100%;
    border-bottom: 3px solid #10BC3B;
  }
  
  .app-container.dark-mode .profile-card {
    background-color: #222222;
    background-image: linear-gradient(135deg, #222222, #1a2e1d);
    box-shadow: 0 8px 24px rgba(16, 188, 59, 0.15);
    border-bottom: 3px solid #10BC3B;
  }
  
  .profile-avatar {
    width: 90px;
    height: 90px;
    border-radius: 50%;
    background: linear-gradient(135deg, #10BC3B, #08963a);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 36px;
    box-shadow: 0 6px 16px rgba(16, 188, 59, 0.25);
  }
  
  .profile-info {
    flex: 1;
  }
  
  .profile-name {
    font-size: 2.2rem;
    font-weight: 700;
    margin: 0 0 12px 0;
    background: linear-gradient(90deg, #10BC3B, #078a2a);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.5px;
  }
  
  .app-container.dark-mode .profile-name {
    background: linear-gradient(90deg, #10BC3B, #3dd665);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  
  .profile-description {
    font-size: 1.1rem;
    color: #4a5568;
    margin: 0;
    line-height: 1.6;
    max-width: 80%;
  }
  
  .app-container.dark-mode .profile-description {
    color: #a0aec0;
  }
  
  /* Dashboard Grid */
  .dashboard-grid {
    text-align: center;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(480px, 1fr));
    gap: 28px;
    width: 100%;
  }
  
  .dashboard-card {
    background-color: #ffffff;
    background-image: linear-gradient(135deg, #ffffff, #f9fdf9);
    border-radius: 16px;
    padding: 28px;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
    transition: all 0.3s ease;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    cursor: pointer;
    border-top: 3px solid transparent;
    height: 100%;
  }
  
  .app-container.dark-mode .dashboard-card {
    background-color: #222222;
    background-image: linear-gradient(135deg, #222222, #1e261f);
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.2);
  }
  
  .dashboard-card:hover {
    transform: translateY(-6px);
    box-shadow: 0 12px 28px rgba(16, 188, 59, 0.12);
    border-top: 3px solid #10BC3B;
  }
  
  .app-container.dark-mode .dashboard-card:hover {
    box-shadow: 0 12px 28px rgba(16, 188, 59, 0.2);
    border-top: 3px solid #10BC3B;
  }
  
  .card-icon {
    width: 70px;
    height: 70px;
    border-radius: 50%;
    background: linear-gradient(135deg, #e0ffe5, #c5f1d0);
    color: #10BC3B;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 20px;
    font-size: 26px;
    box-shadow: 0 4px 12px rgba(16, 188, 59, 0.15);
  }
  
  .card-icon.accent-1 {
    background: linear-gradient(135deg, #e0f7ff, #c5e8f1);
    color: #0a8aaa;
  }
  
  .card-icon.accent-2 {
    background: linear-gradient(135deg, #fff0e0, #f1e2c5);
    color: #aa7b0a;
  }
  
  .app-container.dark-mode .card-icon {
    background: linear-gradient(135deg, #0a7024, #0d8c2c);
    color: #e0ffe5;
    box-shadow: 0 4px 12px rgba(16, 188, 59, 0.3);
  }
  
  .app-container.dark-mode .card-icon.accent-1 {
    background: linear-gradient(135deg, #0a5e74, #0c7490);
    color: #e0f7ff;
  }
  
  .app-container.dark-mode .card-icon.accent-2 {
    background: linear-gradient(135deg, #745a0a, #907c0c);
    color: #fff0e0;
  }
  
  .card-title {
    font-size: 1.35rem;
    font-weight: 600;
    margin-bottom: 12px;
    color: #10BC3B;
    letter-spacing: 0.3px;
  }
  
  .app-container.dark-mode .card-title {
    color: #10BC3B;
  }
  
  .card-description {
    font-size: 1rem;
    color: #4a5568;
    margin-bottom: 24px;
    line-height: 1.6;
    flex-grow: 1;
  }
  
  .app-container.dark-mode .card-description {
    color: #a0aec0;
  }
  
  /* Override n-button styles to match our theme */
  :deep(.n-button.card-button) {
    background: linear-gradient(135deg, #10BC3B, #09a431) !important;
    border: none !important;
    color: white !important;
    padding: 10px 20px !important;
    font-size: 0.95rem !important;
    font-weight: 500 !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 12px rgba(16, 188, 59, 0.2) !important;
    transition: all 0.3s ease !important;
    margin-top: auto;
    width: 80%;
  }
  
  :deep(.n-button.card-button:hover) {
    background: linear-gradient(135deg, #09a431, #078a29) !important;
    box-shadow: 0 6px 16px rgba(16, 188, 59, 0.3) !important;
    transform: translateY(-2px) !important;
  }
  
  /* Responsive adjustments */
  @media (max-width: 768px) {
    .profile-card {
      flex-direction: column;
      text-align: center;
      padding: 24px;
    }
    
    .profile-description {
      max-width: 100%;
    }
    
    .dashboard-grid {
      grid-template-columns: 1fr;
    }
    
    .card-icon {
      width: 60px;
      height: 60px;
      font-size: 24px;
    }
    
    .profile-name {
      font-size: 1.8rem;
    }
  }
  </style>
  