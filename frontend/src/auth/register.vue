<template>
    <div class="app-container" :class="{ 'dark-mode': isDarkMode }">
      <n-space vertical align="center" class="register-container">
        <!-- Logo above register card -->
        <div class="logo-container">
          <img src="../../dist/logo.svg" alt="KubeSage Logo" class="logo" />
        </div>
        
        <n-card class="register-card">
          <div class="register-header">
            <h2>Create an Account</h2>
            <p class="register-subtitle">Join KubeSage - Your intelligent Kubernetes assistant</p>
          </div>
          
          <n-form :model="form" :rules="rules" ref="formRef" class="register-form">
            <n-form-item label="Username" path="username" class="form-item">
              <div class="input-wrapper">
                <i class="fas fa-user input-icon"></i>
                <n-input 
                  v-model:value="form.username" 
                  placeholder="Enter your username" 
                  class="register-input"
                  clearable
                />
              </div>
            </n-form-item>
            
            <n-form-item label="Email" path="email" class="form-item">
              <div class="input-wrapper">
                <i class="fas fa-envelope input-icon"></i>
                <n-input 
                  v-model:value="form.email" 
                  type="email" 
                  placeholder="Enter your email" 
                  class="register-input"
                  clearable
                />
              </div>
            </n-form-item>
            
            <n-form-item label="Password" path="password" class="form-item">
              <div class="input-wrapper">
                <i class="fas fa-lock input-icon"></i>
                <n-input 
                  type="password" 
                  v-model:value="form.password" 
                  placeholder="Enter your password" 
                  class="register-input"
                  show-password-on="click"
                  clearable
                >
                  <template #password-invisible-icon>
                    <i class="fas fa-eye-slash"></i>
                  </template>
                  <template #password-visible-icon>
                    <i class="fas fa-eye"></i>
                  </template>
                </n-input>
              </div>
            </n-form-item>
            
            <n-form-item label="First Name" path="first_name" class="form-item">
              <div class="input-wrapper">
                <i class="fas fa-user-tag input-icon"></i>
                <n-input 
                  v-model:value="form.first_name" 
                  placeholder="Enter your first name" 
                  class="register-input"
                  clearable
                />
              </div>
            </n-form-item>
            
            <n-form-item label="Last Name" path="last_name" class="form-item">
              <div class="input-wrapper">
                <i class="fas fa-user-tag input-icon"></i>
                <n-input 
                  v-model:value="form.last_name" 
                  placeholder="Enter your last name" 
                  class="register-input"
                  clearable
                />
              </div>
            </n-form-item>
            
            <n-space justify="space-between" class="checkbox-container">
              <n-checkbox v-model:checked="form.is_active">Active</n-checkbox>
              <n-checkbox v-model:checked="form.is_admin">Admin</n-checkbox>
            </n-space>
            
            <n-form-item class="form-item">
              <n-button 
                type="primary" 
                class="register-button"
                :loading="loading"
                @click="registerUser"
              >
                Register
              </n-button>
            </n-form-item>
          </n-form>
          
          <div class="register-footer">
            <span>Already have an account? </span>
            <n-button text type="primary" @click="goToLogin" class="login-link">
              Login here
            </n-button>
          </div>
        </n-card>
      </n-space>
    </div>
  </template>
  
  <script>
  import { ref, onMounted } from 'vue';
  import { useRouter } from 'vue-router';
  import { NCard, NForm, NFormItem, NInput, NButton, NSpace, NCheckbox, useMessage } from 'naive-ui';
  import axios from 'axios';
  
  export default {
    components: {
      NCard,
      NForm,
      NFormItem,
      NInput,
      NButton,
      NSpace,
      NCheckbox
    },
    setup() {
      const formRef = ref(null);
      const message = useMessage();
      const router = useRouter();
      const loading = ref(false);
      const isDarkMode = ref(localStorage.getItem('darkMode') === 'true');
  
      const form = ref({
        username: "",
        email: "",
        password: "",
        first_name: "",
        last_name: "",
        is_active: true,
        is_admin: false,
      });
  
      const rules = {
        username: [
          { required: true, message: "Username is required", trigger: "blur" },
          { min: 3, message: "Username must be at least 3 characters", trigger: "blur" },
        ],
        email: [
          { required: true, message: "Email is required", trigger: "blur" },
          { type: "email", message: "Invalid email format", trigger: "blur" },
        ],
        password: [
          { required: true, message: "Password is required", trigger: "blur" },
          { min: 6, message: "Password must be at least 6 characters", trigger: "blur" },
        ],
        first_name: [{ required: true, message: "First name is required", trigger: "blur" }],
        last_name: [{ required: true, message: "Last name is required", trigger: "blur" }],
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
  
      onMounted(() => {
        updateDarkModeClasses();
      });
  
      const registerUser = async () => {
        formRef.value?.validate(async (errors) => {
          if (!errors) {
            loading.value = true;
            
            try {
              const response = await axios.post("https://10.0.32.122:8003/auth/register", form.value, {
                headers: {
                  'Content-Type': 'application/json',
                },
              });
  
              message.success(`User ${response.data.username} registered successfully!`);
              router.push('/login');
            } catch (error) {
              const errorMessage = error.response?.data?.detail || error.message || "Registration failed";
              message.error(errorMessage);
            } finally {
              loading.value = false;
            }
          }
        });
      };
  
      const goToLogin = () => {
        router.push('/login');
      };
  
      return {
        form,
        rules,
        formRef,
        loading,
        registerUser,
        goToLogin,
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
    background-image: linear-gradient(to bottom right, #f8f9fa, #e8f5e9);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  }
  
  .app-container.dark-mode {
    background-color: #1a1a1a;
    background-image: linear-gradient(to bottom right, #1a1a1a, #0d2d0f);
    color: #f0f0f0;
  }
  
  .register-container {
    width: 100%;
    height: 100vh;
    justify-content: center;
    padding: 20px;
  }
  
  /* Logo styling */
  .logo-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-bottom: 24px;
  }
  
  .logo {
    margin-top: 100px;
    width: 400px;
    height: 100px;
    margin-bottom: 12px;
  }
  
  .register-card {
    width: 100%;
    max-width: 480px;
    background-color: #ffffff;
    background-image: linear-gradient(135deg, #ffffff, #f5fff7);
    border-radius: 16px;
    padding: 32px;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
    border-top: 3px solid #10BC3B;
    transition: all 0.3s ease;
  }
  
  .app-container.dark-mode .register-card {
    background-color: #222222;
    background-image: linear-gradient(135deg, #222222, #1a2e1d);
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.2);
    border-top: 3px solid #10BC3B;
  }
  
  .register-header {
    text-align: center;
    margin-bottom: 32px;
  }
  
  .register-header h2 {
    margin: 0 0 8px 0;
    font-size: 1.8rem;
    font-weight: 600;
    color: #10BC3B;
    letter-spacing: 0.5px;
  }
  
  .app-container.dark-mode .register-header h2 {
    color: #10BC3B;
  }
  
  .register-subtitle {
    color: #4a5568;
    margin: 0;
    font-size: 1rem;
  }
  
  .app-container.dark-mode .register-subtitle {
    color: #a0aec0;
  }
  
  .register-form {
    margin-bottom: 24px;
  }
  
  .form-item {
    margin-bottom: 20px;
  }
  
  .input-wrapper {
    position: relative;
    display: flex;
    align-items: center;
  }
  
  .input-icon {
    position: absolute;
    left: 12px;
    color: #10BC3B;
    font-size: 16px;
    z-index: 1;
  }
  
  .app-container.dark-mode .input-icon {
    color: #10BC3B;
  }
  
  :deep(.register-input) {
    width: 100%;
    font-size: 16px;
    height: 40px;
  }
  
  /* Fix for overlapping icons and placeholders */
  :deep(.register-input .n-input__input-el) {
    padding-left: 36px !important;
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
  
  /* Fix for form label styling */
  :deep(.n-form-item-label) {
    padding-bottom: 8px;
    font-weight: 500;
    color: #4a5568;
  }
  
  .app-container.dark-mode :deep(.n-form-item-label) {
    color: #a0aec0;
  }
  
  .checkbox-container {
    margin-bottom: 20px;
  }
  
  :deep(.register-button) {
    background: linear-gradient(135deg, #10BC3B, #09a431) !important;
    border: none !important;
    color: white !important;
    width: 100% !important;
    font-size: 16px !important;
    height: 40px !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 12px rgba(16, 188, 59, 0.2) !important;
  }
  
  :deep(.register-button:hover) {
    background: linear-gradient(135deg, #09a431, #078a29) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 16px rgba(16, 188, 59, 0.3) !important;
  }
  
  .register-footer {
    text-align: center;
    margin-top: 20px;
    color: #4a5568;
  }
  
  .app-container.dark-mode .register-footer {
    color: #a0aec0;
  }
  
  :deep(.login-link) {
    color: #10BC3B !important;
    font-weight: 500;
  }
  
  :deep(.login-link:hover) {
    color: #09a431 !important;
    text-decoration: underline;
  }
  
  /* Responsive adjustments */
  @media (max-width: 768px) {
    .logo {
      width: 60px;
      height: 60px;
    }
    
    .register-card {
      padding: 24px;
    }
    
    .register-header h2 {
      font-size: 1.5rem;
    }
  }
  </style>
  