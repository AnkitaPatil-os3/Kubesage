<template>
  <n-card class="p-6 rounded-lg shadow-md">
    <n-text class="text-2xl font-bold">
      Bootstrap the Windows server
    </n-text>   
     <n-form @submit.prevent="submitForm" :model="accountData" ref="formRef">
      <!-- Server IP -->
      <n-form-item label="Server IP" path="ipAdr">
        <n-input v-model:value="accountData.ipAdr" placeholder="0.0.0.0" class="w-full" />
   
      </n-form-item>

      <!-- Server Username -->
      <n-form-item label="Server Username" path="serverUser">
        <n-input v-model:value="accountData.serverUser" placeholder="Username" class="w-full" />
      </n-form-item>

      <!-- Server Password -->
      <n-form-item label="Server Password" path="serverPass">
        <n-input v-model:value="accountData.serverPass" type="password"       show-password-on="mousedown"
 placeholder="Password" class="w-full" />
      </n-form-item>
     

      <!-- Form Actions -->
      <div class="flex justify-between mt-4">
        <n-button type="primary" @click="submitForm" :loading="isLoading" class="w-full md:w-auto">
          <template v-if="isLoading">
            <n-icon>
              <i class="n-icon-loading" />
            </n-icon>
          </template>
          <template v-else>Submit</template>
        </n-button>
        <n-button @click="resetForm" :disabled="isLoading" class="w-full md:w-auto" ghost>Reset</n-button>
      </div>
    </n-form>
    </n-card>
</template>

<script setup>
import { ref } from 'vue';
import { useMessage } from 'naive-ui';

import axios from 'axios';
const accountData = ref({
  ipAdr: '',
  serverUser: '',
  serverPass: '',
});

const formRef = ref(null);
const isLoading = ref(false);

const message = useMessage();

const successMessage = ref('');
const errorMessage = ref('');

// Reset form to initial state
const resetForm = () => {
  accountData.value = {
    ipAdr: '',
    serverUser: '',
    serverPass: '',
  };};

// Handle form submission
const submitForm = async () => {
  isLoading.value = true;
  successMessage.value = '';
  errorMessage.value = '';
  try {
    const response = await axios.post('http://172.16.1.56:8000/api/v3/onboardWindow/', accountData.value);
    successMessage.value = 'Bootstrapping is successful';
    message.success(successMessage.value);
  } catch (error) {
    errorMessage.value = 'Bootstrapping process failed. Try again.';
    message.error(errorMessage.value);
  } finally {
    isLoading.value = false;
    resetForm();
  }
};
</script>

<style scoped>
/* Custom styles for light/dark mode */
</style>
