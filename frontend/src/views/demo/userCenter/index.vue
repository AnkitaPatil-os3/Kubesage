<template>
  <n-card class="bordered" :shadow="'always'" size="large">
    <n-space vertical>
      <n-text type="success" class="text-2xl font-bold uppercase">
        Welcome kubeSage User {{ username }}
      </n-text>
      <n-text class="text-lg font-medium">
        Streamline your observability journey with kubeSage: Advanced monitoring and analytics in one platform.
      </n-text>
    </n-space>
  </n-card>
</template>
 
<script setup>
import { ref, onMounted } from 'vue';
 
const username = ref(''); // Initialize as an empty ref
 
onMounted(() => {
  // Retrieve user information from localStorage
  const userInfo = JSON.parse(localStorage.getItem('userInfo'));
 
  // Set the username dynamically if userInfo exists
  if (userInfo) {
    username.value = userInfo.nickname || userInfo.userName || 'User'; // Use 'nickname' or fallback to 'userName'
  } else {
    console.warn("User information not found in localStorage.");
    username.value = 'User'; // Default fallback if no user info is found
  }
});
</script>
 
<style scoped>
/* Add any additional styling here if needed */
</style>
 
 