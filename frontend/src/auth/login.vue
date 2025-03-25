<template>
    <n-space vertical align="center" style="width: 100%; height: 100vh; justify-content: center;">
      <n-card style="width: 400px;">
        <h3 style="text-align: center; margin-bottom: 20px;">Login</h3>
        <n-form :model="formData" :rules="formRules" ref="formRef">
          <n-form-item label="Username" path="username" style="margin-bottom: 16px;">
            <n-input 
              v-model:value="formData.username" 
              placeholder="Enter your username" 
              style="font-size: 16px; height: 40px;" 
            />
          </n-form-item>
          <n-form-item label="Password" path="password" style="margin-bottom: 16px;">
            <n-input 
              type="password" 
              v-model:value="formData.password" 
              placeholder="Enter your password" 
              style="font-size: 16px; height: 40px;" 
            />
          </n-form-item>
          <n-form-item style="margin-top: 20px;">
            <n-button 
              type="primary" 
              style="width: 100%; font-size: 16px; height: 40px;" 
              @click="handleSubmit"
            >
              Login
            </n-button>
          </n-form-item>
        </n-form>
        <div style="text-align: center; margin-top: 20px;">
          <span>Don't have an account? </span>
          <a @click="goToRegister" style="color: #409EFF; cursor: pointer;">Register here</a>
        </div>
      </n-card>
    </n-space>
  </template>
  
  <script>
  import { ref } from 'vue';
  import { useRouter } from 'vue-router';
  import { NCard, NForm, NFormItem, NInput, NButton, NSpace, useMessage } from 'naive-ui';
  import axios from 'axios';
  import qs from 'qs';  
  import jwt_decode from 'jwt-decode';
  
  export default {
    components: {
      NCard,
      NForm,
      NFormItem,
      NInput,
      NButton,
      NSpace,
    },
    setup() {
      const formData = ref({
        username: '',
        password: '',
      });
  
      const formRules = ref({
        username: [{ required: true, message: 'Username is required' }],
        password: [{ required: true, message: 'Password is required' }],
      });
  
      const formRef = ref(null);
      const message = useMessage();
      const router = useRouter();
  
      const handleSubmit = async () => {
        try {
          const data = qs.stringify({
            username: formData.value.username,
            password: formData.value.password,
          });
  
          const response = await axios.post(
            'https://10.0.34.129:8006/auth/token', 
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
        }
      };
  
      const goToRegister = () => {
        router.push('/register');
      };
  
      return {
        formData,
        formRules,
        formRef,
        handleSubmit,
        goToRegister
      };
    },
  };
  </script>
  
  <style scoped>
  .n-card {
    border-radius: 12px;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
  }
  
  h3 {
    font-size: 24px;
    font-weight: bold;
  }
  
  .n-input, .n-button {
    font-size: 16px;
  }
  
  .n-button {
    height: 40px;
  }
  </style>
  