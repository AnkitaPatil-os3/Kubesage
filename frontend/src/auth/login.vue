<template>
  <div class="app-container" :class="{ 'dark-mode': isDarkMode }">
    <div class="login-layout">
      <!-- Left section - Login form -->
      <div class="form-section">
        <div class="form-container">
          <div class="logo-container">
            <img src="../assets/logo.png" alt="KubeSage Logo" class="logo" />
          </div>
          
          <n-card class="login-card">
            <div class="login-header">
              <h1 class="text-3xl">KubeSage</h1>
              <p class="login-subtitle">AI-Powered Kubernetes Assistant</p>
            </div>
            
            <n-form 
              :model="formData" 
              :rules="formRules" 
              ref="formRef" 
              class="login-form"
            >
              <n-form-item path="username" class="form-item">
                
                <div class="input-wrapper">
                  <n-input 
                    v-model:value="formData.username"  
                    class="login-input"
                    placeholder="Enter your username"
                  >
                    <template #prefix>
                      <i class="fas fa-user input-icon"></i>
                    </template>
                  </n-input>
                </div>
              </n-form-item>
              
              <n-form-item path="password" class="form-item">
                <div class="input-wrapper">
                  <n-input 
                    type="password" 
                    v-model:value="formData.password" 
                    class="login-input"
                    placeholder="Enter your password"
                    show-password-on="click"
                  >
                    <template #prefix>
                      <i class="fas fa-lock input-icon"></i>
                    </template>
                    <template #password-invisible-icon>
                      <i class="fas fa-eye-slash"></i>
                    </template>
                    <template #password-visible-icon>
                      <i class="fas fa-eye"></i>
                    </template>
                  </n-input>
                </div>
              </n-form-item>
              
              <n-form-item class="form-item">
                <n-button 
                  type="primary" 
                  class="login-button"
                  @click="handleSubmit"
                  :loading="isLoggingIn"
                >
                  {{ isLoggingIn ? 'Logging in...' : 'Login' }}
                </n-button>
              </n-form-item>
            </n-form>
          </n-card>
        </div>
      </div>
      
      <!-- Right section - Visual content -->
      <div class="visual-section">
        <div class="visual-content">
          <h2 class="text-3xl font-bold mb-4">Welcome to KubeSage</h2>
          <p class="mb-6">
            KubeSage is an AI-powered Kubernetes management tool that enables seamless cluster analysis, ChatOps, and intelligent automation for your Kubernetes environments.
          </p>
          
          <div class="feature-list">
            <div class="feature-item">
              <div class="feature-icon">
                <i class="fas fa-server"></i>
              </div>
              <div class="feature-text">
                <h4 class="font-semibold">Cluster Management</h4>
                <p>Upload your cluster's kubeconfig file for management</p>
              </div>
            </div>
            
            <div class="feature-item">
              <div class="feature-icon">
                <i class="fas fa-chart-bar"></i>
              </div>
              <div class="feature-text">
                <h4 class="font-semibold">Cluster Analysis</h4>
                <p>Analyze Pods, Deployments, Services, and PVCs</p>
              </div>
            </div>
            
            <div class="feature-item">
              <div class="feature-icon">
                <i class="fas fa-robot"></i>
              </div>
              <div class="feature-text">
                <h4 class="font-semibold">ChatOps</h4>
                <p>ChatGPT-like UI allowing direct interaction with AI-powered backend</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { 
  NCard, 
  NForm, 
  NFormItem, 
  NInput, 
  NButton, 
  useMessage 
} from 'naive-ui';
import axios from 'axios';
import qs from 'qs';  
import jwt_decode from 'jwt-decode';

export default {
  components: {
    NCard,
    NForm,
    NFormItem,
    NInput,
    NButton
  },
  setup() {
    const formRef = ref(null);
    const isLoggingIn = ref(false);
    
    const formData = ref({
      username: '',
      password: '',
    });

    const formRules = {
      username: [{ required: true, message: 'Username is required', trigger: 'blur' }],
      password: [{ required: true, message: 'Password is required', trigger: 'blur' }],
    };

    const message = useMessage();
    const router = useRouter();
    const isDarkMode = ref(localStorage.getItem('darkMode') === 'true');

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

    onMounted(() => {
      updateDarkModeClasses();
    });

    const handleSubmit = async () => {
      try {
        await formRef.value?.validate();
        isLoggingIn.value = true;
        
        const data = qs.stringify({
          username: formData.value.username,
          password: formData.value.password,
        });

        const response = await axios.post(
          'https://10.0.34.171:8001/auth/token', 
          data, 
          {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
          }
        );

        if (response.data.access_token) {
          const token = response.data.access_token;
          const refreshTokenValue = response.data.refresh_token;
          const decodedToken = jwt_decode(token);
  
          const currentTime = new Date().getTime();
          const expireTime = currentTime + decodedToken.exp * 1000;
  
          const userInfo = {
            value: {
              id: decodedToken.sub,
              userName: formData.value.username,
              nickname: decodedToken.preferred_username || formData.value.username,
              email: decodedToken.email || `${formData.value.username}@example.com`,
              roles: decodedToken.roles || ["user"],
            },
            expire: expireTime,
          };
          localStorage.setItem("userInfo", JSON.stringify(userInfo));
  
          const accessToken = {
            value: token,
            expire: expireTime,
          };
          localStorage.setItem("accessToken", JSON.stringify(accessToken));
  
          const refreshToken = {
            value: refreshTokenValue,
            expire: expireTime,
          };
          localStorage.setItem("refreshToken", JSON.stringify(refreshToken));
  
          window.location.href = "/";
        }
      } catch (error) {
        message.error('Invalid username or password');
      } finally {
        isLoggingIn.value = false;
      }
    };

    return {
      formData,
      formRules,
      formRef,
      isLoggingIn,
      handleSubmit,
      isDarkMode
    };
  },
};
</script>

<style scoped>
/* Import Font Awesome */
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');

.app-container {
  width: 100%;
  min-height: 100vh;
  display: flex;
  background-color: #f8f9fa;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
}

.app-container.dark-mode {
  background-color: #1a1a1a;
  color: #f0f0f0;
}

.login-layout {
  display: flex;
  width: 100%;
  min-height: 100vh;
  overflow: hidden;
}

/* Left section - Form */
.form-section {
  flex: 1;
  display: flex;
  /* align-items: center; */
  justify-content: center;
  padding: 2rem;
  background-color: #ffffff;
}

.app-container.dark-mode .form-section {
  background-color: #222222;
}

.form-container {
  width: 100%;
  max-width: 480px;
}

.logo-container {
  display: flex;
  justify-content: center;
  margin-bottom: 4rem;
  margin-top: 7rem;
}

.logo {
  width: 1000px; /* Increased logo size */
  /* height: 400px; */
  max-height: 350px;
  /* Add these properties to remove background */
  background: transparent;
  object-fit: contain;
}

.login-card {
  background-color: #ffffff;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.app-container.dark-mode .login-card {
  background-color: #2d2d2d;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.login-header {
  text-align: center;
  margin-bottom: 2rem;
}

.login-header h1 {
  margin: 0 0 0.5rem 0;
  font-size: 2rem; /* Slightly larger heading */
  font-weight: 600;
  color: #10BC3B;
}

.app-container.dark-mode .login-header h1 {
  color: #10BC3B;
}

.login-subtitle {
  color: #4a5568;
  margin: 0;
  font-size: 1.1rem;
}

.app-container.dark-mode .login-subtitle {
  color: #a0aec0;
}


/* Fix for label positioning */
:deep(.label) {
  padding-bottom: 8px;
  font-weight: 500;
}

.input-wrapper {
  width: 400px;
  margin-left: 8px;
  position: relative;
  display: flex;
  align-items: center;
}

/* Fix for icon positioning - using Naive UI's prefix slot instead */
:deep(.input-icon) {
  color: #10BC3B;
  font-size: 16px;
}

.app-container.dark-mode :deep(.input-icon) {
  color: #10BC3B;
}

:deep(.login-input) {
  width: 100%;
  font-size: 16px;
  height: 42px;
}

:deep(.n-input) {
  border-radius: 8px;
}

:deep(.n-input:hover) {
  border-color: #10BC3B !important;
}

:deep(.n-input:focus) {
  border-color: #10BC3B !important;
  box-shadow: 0 0 0 2px rgba(16, 188, 59, 0.2) !important;
}

:deep(.login-button) {
  background: linear-gradient(135deg, #10BC3B, #09a431) !important;
  border: none !important;
  color: white !important;
  width: 100% !important;
  font-size: 16px !important;
  height: 44px !important;
  border-radius: 8px !important;
  transition: all 0.3s ease !important;
  box-shadow: 0 4px 12px rgba(16, 188, 59, 0.2) !important;
  margin-top: 1rem;
}

:deep(.login-button:hover) {
  background: linear-gradient(135deg, #09a431, #078a29) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 16px rgba(16, 188, 59, 0.3) !important;
}

/* Right section - Visual content */
.visual-section {
  flex: 1;
  background: linear-gradient(135deg, #10BC3B, #078a29);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  color: white;
}

.visual-content {
  max-width: 500px;
  padding: 2rem;
}

.visual-content h2 {
  font-size: 2.2rem;
  margin-bottom: 1rem;
  font-weight: 600;
}

.visual-content p {
  font-size: 1.1rem;
  margin-bottom: 2rem;
  line-height: 1.6;
  opacity: 0.9;
}

.feature-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
}

.feature-icon {
  background-color: rgba(255, 255, 255, 0.2);
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.feature-icon i {
  font-size: 1.2rem;
}

.feature-text h4 {
  font-size: 1.1rem;
  margin: 0 0 0.5rem 0;
  font-weight: 600;
}

.feature-text p {
  font-size: 0.95rem;
  margin: 0;
  opacity: 0.8;
  line-height: 1.4;
}

/* Responsive adjustments */
@media (max-width: 992px) {
  .login-layout {
    flex-direction: column-reverse;
  }
  
  .visual-section {
    padding: 2rem 1.5rem;
  }
  
  .visual-content {
    padding: 1rem;
  }
  
  .visual-content h2 {
    font-size: 1.8rem;
  }
  
  .visual-content p {
    font-size: 1rem;
    margin-bottom: 1.5rem;
  }
  
  .feature-list {
    gap: 1rem;
  }
  
  .logo {
    width: 250px;
  }
}

@media (max-width: 768px) {
  .form-section {
    padding: 1.5rem 1rem;
  }
  
  .login-card {
    padding: 1.5rem;
  }
  
  .visual-section {
    display: none; /* Hide on mobile */
  }
  
  .logo {
    width: 220px;
  }
  
  .login-header h1 {
    font-size: 1.8rem;
  }
}
</style>
