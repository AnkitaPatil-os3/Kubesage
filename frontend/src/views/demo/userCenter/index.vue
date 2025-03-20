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
});
</script>
 
<style scoped>
/* Add any additional styling here if needed */
</style>
 
 