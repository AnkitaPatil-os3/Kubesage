<template>
  <n-card class="p-6 rounded-lg shadow-md">
    <n-text class="text-2xl font-bold">
      Bootstrap the k8s Server
    </n-text> 
    <n-form @submit.prevent="submitForm" :model="accountData" ref="formRef">
      <!-- Kubeconfig Data -->
      <n-form-item label="Kubeconfig File Content" path="kubeconfig_data">
        <n-input type="textarea" v-model:value="accountData.kubeconfig_data" rows="5"
          placeholder="Enter your kubeconfig data here" class="w-full" />
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

// const { $api } = useNuxtApp();

const accountData = ref({
  kubeconfig_data: '',
});

const formRef = ref(null);


const isLoading = ref(false);

const message = useMessage();

// Reset form to initial state
const resetForm = () => {
  accountData.value = {
    kubeconfig_data: '',
  };
};

// Handle form submission
const submitForm = async () => {
  isLoading.value = true;
  try {
    const response = await axios.post('http://172.16.1.56:8000/api/v3/onboardkubernetes/', accountData.value);
    message.success('Bootstrapping is successful');
    console.log("API RESPONSE from backend", response);
  } catch (error) {
    if (error.response) {
      message.error(`Bootstrapping process failed: ${error.response.data.message || 'Try again.'}`);
    } else if (error.request) {
      message.error('Bootstrapping process failed: No response from server. Please try again.');
    } else {
      message.error(`Bootstrapping process failed: ${error.message}. Please try again.`);
    }
  } finally {
    isLoading.value = false;
    resetForm();
  }
};
</script>

<style scoped>
/* Custom styles for light/dark mode */
</style>