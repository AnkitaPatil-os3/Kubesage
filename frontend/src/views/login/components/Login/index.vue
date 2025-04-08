<script setup lang="ts">
import type { FormInst } from 'naive-ui'
import { useAuthStore } from '@/store'
import { local } from '@/utils'

const emit = defineEmits(['update:modelValue'])

const authStore = useAuthStore()

function toOtherForm(type: any) {
  emit('update:modelValue', type)
}

const { t } = useI18n()
const rules = computed(() => {
  return {
    account: {
      required: true,
      trigger: 'blur',
      message: t('login.accountRuleTip'),
    },
    pwd: {
      required: true,
      trigger: 'blur',
      message: t('login.passwordRuleTip'),
    },
  }
})
const formValue = ref({
  account: 'super',
  pwd: '123456',
})
const isRemember = ref(false)
const isLoading = ref(false)
const isDarkMode = ref(localStorage.getItem('darkMode') === 'true')

const formRef = ref<FormInst | null>(null)

function handleLogin() {
  formRef.value?.validate(async (errors) => {
    if (errors)
      return

    isLoading.value = true
    const { account, pwd } = formValue.value

    if (isRemember.value)
      local.set('loginAccount', { account, pwd })
    else local.remove('loginAccount')

    await authStore.login(account, pwd)
    isLoading.value = false
  })
}

onMounted(() => {
  checkUserAccount()
  updateDarkModeClasses()
})

function checkUserAccount() {
  const loginAccount = local.get('loginAccount')
  if (!loginAccount)
    return

  formValue.value = loginAccount
  isRemember.value = true
}

// Update dark mode classes
const updateDarkModeClasses = () => {
  if (isDarkMode.value) {
    document.documentElement.classList.add('dark')
    document.body.style.backgroundColor = 'rgb(24 24 28)'
  } else {
    document.documentElement.classList.remove('dark')
    document.body.style.backgroundColor = ''
  }
}
</script>

<template>
  <div class="app-container" :class="{ 'dark-mode': isDarkMode }">
    <div class="login-container">
      <div class="login-card">
        <div class="login-header">
          <h2>{{ $t('login.signInTitle') }}</h2>
          <p class="login-subtitle">Welcome to KubeSage</p>
        </div>
        
        <n-form 
          ref="formRef" 
          :rules="rules" 
          :model="formValue" 
          :show-label="false" 
          size="large"
          class="login-form"
        >
          <n-form-item path="account">
            <div class="input-wrapper">
              <i class="fas fa-user input-icon"></i>
              <n-input 
                v-model:value="formValue.account" 
                clearable 
                :placeholder="$t('login.accountPlaceholder')"
                class="login-input"
              />
            </div>
          </n-form-item>
          
          <n-form-item path="pwd">
            <div class="input-wrapper">
              <i class="fas fa-lock input-icon"></i>
              <n-input 
                v-model:value="formValue.pwd" 
                type="password" 
                :placeholder="$t('login.passwordPlaceholder')" 
                clearable 
                show-password-on="click"
                class="login-input"
              >
                <template #password-invisible-icon>
                  <icon-park-outline-preview-close-one />
                </template>
                <template #password-visible-icon>
                  <icon-park-outline-preview-open />
                </template>
              </n-input>
            </div>
          </n-form-item>
          
          <div class="login-options">
            <n-checkbox v-model:checked="isRemember" class="remember-checkbox">
              {{ $t('login.rememberMe') }}
            </n-checkbox>
            <n-button type="primary" text @click="toOtherForm('resetPwd')" class="forgot-password">
              {{ $t('login.forgotPassword') }}
            </n-button>
          </div>
          
          <n-button 
            block 
            class="login-button" 
            :loading="isLoading" 
            :disabled="isLoading" 
            @click="handleLogin"
          >
            {{ $t('login.signIn') }}
          </n-button>
        </n-form>
      </div>
    </div>
  </div>
</template>

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

.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  padding: 24px;
}

.login-card {
  width: 100%;
  max-width: 420px;
  background-color: #ffffff;
  background-image: linear-gradient(135deg, #ffffff, #f5fff7);
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
  border-top: 3px solid #10BC3B;
  transition: all 0.3s ease;
}

.app-container.dark-mode .login-card {
  background-color: #222222;
  background-image: linear-gradient(135deg, #222222, #1a2e1d);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.2);
  border-top: 3px solid #10BC3B;
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-header h2 {
  margin: 0 0 8px 0;
  font-size: 1.8rem;
  font-weight: 600;
  color: #10BC3B;
  letter-spacing: 0.5px;
}

.app-container.dark-mode .login-header h2 {
  color: #10BC3B;
}

.login-subtitle {
  color: #4a5568;
  margin: 0;
  font-size: 1rem;
}

.app-container.dark-mode .login-subtitle {
  color: #a0aec0;
}

.login-form {
  margin-bottom: 24px;
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

:deep(.login-input) {
  width: 100%;
}

:deep(.login-input .n-input__input-el) {
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

.login-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

:deep(.remember-checkbox .n-checkbox__label) {
  color: #4a5568;
}

.app-container.dark-mode :deep(.remember-checkbox .n-checkbox__label) {
  color: #a0aec0;
}

:deep(.forgot-password) {
  color: #10BC3B !important;
}

:deep(.forgot-password:hover) {
  color: #09a431 !important;
}

:deep(.login-button) {
  background: linear-gradient(135deg, #10BC3B, #09a431) !important;
  border: none !important;
  color: white !important;
  padding: 12px !important;
  border-radius: 8px !important;
  font-size: 1rem !important;
  font-weight: 500 !important;
  height: 48px !important;
  transition: all 0.3s ease !important;
  box-shadow: 0 4px 12px rgba(16, 188, 59, 0.2) !important;
}

:deep(.login-button:hover) {
  background: linear-gradient(135deg, #09a431, #078a29) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 16px rgba(16, 188, 59, 0.3) !important;
}

:deep(.login-button:disabled) {
  background: #a0aec0 !important;
  cursor: not-allowed !important;
  transform: none !important;
  box-shadow: none !important;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .login-card {
    padding: 24px;
  }
  
  .login-header h2 {
    font-size: 1.5rem;
  }
}
</style>
