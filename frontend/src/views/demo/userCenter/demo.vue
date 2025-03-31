<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useMessage, useUpload } from 'naive-ui'
import axios from 'axios'
import { useAuthStore } from '@/store'

const authStore = useAuthStore()
const { userInfo } = authStore

// Form references and values
const formRef = ref()
const isLoading = ref(false)
const message = useMessage()

// User profile data
const userProfile = ref({
  id: '',
  username: '',
  nickname: '',
  email: '',
  role: '',
  avatar: '',
})

// Form values initialized from `userProfile`
const formValue = ref({
  name: '',
  Nickname: '',
  email: '',
  password: '',
})

// Function to fetch user profile data
async function fetchUserProfile() {
  try {
    const response = await axios.get(`/api/v1/user-profile/${userInfo?.id}/`, {
      headers: {
        Authorization: `Bearer ${authStore.token}`,
      },
    })
    if (response.status === 200) {
      const data = response.data
      userProfile.value = data
      formValue.value = {
        name: data.username,
        Nickname: data.nickname,
        email: data.email,
        password: '', // Leave password blank for security
      }
    }
  } catch (error) {
    console.error('Error fetching user profile:', error)
    message.error('Failed to fetch user profile')
  }
}

// Function to update profile picture
async function updateProfilePicture(file) {
  const formData = new FormData()
  formData.append('avatar', file)

  try {
    const response = await axios.post(
      `/api/v1/user-profile/${userProfile.value.id}/upload-avatar/`,
      formData,
      {
        headers: {
          Authorization: `Bearer ${authStore.token}`,
          'Content-Type': 'multipart/form-data',
        },
      }
    )
    if (response.status === 200) {
      userProfile.value.avatar = response.data.avatar
      message.success('Profile picture updated successfully')
    }
  } catch (error) {
    console.error('Error updating profile picture:', error)
    message.error('Failed to update profile picture')
  }
}

// Trigger file upload dialog on avatar click
function handleAvatarClick() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.addEventListener('change', (event) => {
    const file = event.target.files?.[0]
    if (file) {
      updateProfilePicture(file)
    }
  })
  input.click()
}

// Handle form submission
function handleValidateClick() {
  formRef.value?.validate((errors) => {
    if (!errors) {
      updateUserProfile()
    } else {
      message.error('Validation failed')
    }
  })
}

// Fetch the user profile data on component mount
onMounted(fetchUserProfile)
</script>

<template>
  <n-space vertical>
    <!-- User Management Section -->
    <n-card title="User Management">
      <n-space size="large" align="center">
        <n-avatar
          round
          :size="128"
          :src="userProfile?.avatar || ''"
          @click="handleAvatarClick"
          class="avatar-clickable"
        />
        <n-descriptions label-placement="left" :column="2" :title="`Hello, ${userProfile?.nickname || 'Guest'}`">
          <n-descriptions-item label="ID">{{ userProfile?.id }}</n-descriptions-item>
          <n-descriptions-item label="Username">{{ userProfile?.username }}</n-descriptions-item>
          <n-descriptions-item label="Nickname">{{ userProfile?.nickname }}</n-descriptions-item>
          <n-descriptions-item label="Email">{{ userProfile?.email }}</n-descriptions-item>
          <n-descriptions-item label="Role">{{ userProfile?.role }}</n-descriptions-item>
        </n-descriptions>
      </n-space>
    </n-card>

    <!-- Edit User Profile Section -->
    <n-card title="Edit User Profile">
      <n-space justify="center">
        <n-form ref="formRef" class="w-500px" :label-width="100" :model="formValue">
          <n-form-item label="Name">
            <n-input v-model:value="formValue.name" placeholder="Enter username" />
          </n-form-item>
          <n-form-item label="Nick Name">
            <n-input v-model:value="formValue.Nickname" placeholder="Enter your nickname" />
          </n-form-item>
          <n-form-item label="Email">
            <n-input v-model:value="formValue.email" type="email" placeholder="Enter email" />
          </n-form-item>
          <n-form-item label="Password">
            <n-input v-model:value="formValue.password" type="password" placeholder="Enter password" />
          </n-form-item>
          <n-form-item>
            <n-button type="primary" :loading="isLoading" block @click="handleValidateClick">
              Save Changes
            </n-button>
          </n-form-item>
        </n-form>
      </n-space>
    </n-card>
  </n-space>
</template>

<style scoped>
.w-500px {
  width: 500px;
}

.avatar-clickable {
  cursor: pointer;
  transition: transform 0.3s ease;
}
.avatar-clickable:hover {
  transform: scale(1.1);
}

@media (max-width: 600px) {
  .w-500px {
    width: 90%;
  }
}
</style>
