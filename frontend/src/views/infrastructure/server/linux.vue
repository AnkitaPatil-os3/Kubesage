<template>
  <n-card class="p-6 rounded-lg shadow-md">
    <n-text class="text-2xl font-bold">
      Bootstrap the Linux Server
    </n-text>
    <n-form @submit.prevent="submitForm" :model="accountData" ref="formRef">
      <n-form-item label="Server IP/Hostname" path="ipAdr">
        <!-- Wrap n-input in a div to apply the width -->
        <div class="w-full md:w-1/2">
          <n-input v-model:value="accountData.ipAdr" placeholder="0.0.0.0" />
        </div>
      </n-form-item>

      <n-form-item label="Server Username" path="serverUser">
        <!-- Wrap n-input in a div to apply the width -->
        <div class="w-full md:w-1/2">
          <n-input v-model:value="accountData.serverUser"  placeholder="Username" />
        </div>
      </n-form-item>

      <n-form-item label="Server Password" path="serverPass">
        <!-- Wrap n-input in a div to apply the width -->
        <div class="w-full md:w-1/2">
          <n-input v-model:value="accountData.serverPass"  show-password-on="mousedown" placeholder="Password" type="password" />
        </div>
      </n-form-item>

      <n-form-item label="OS Type" path="osType">
        <n-select v-model:value="accountData.osType" :options="osOptions" placeholder="Select OS Type" class="w-full md:w-1/2" />
      </n-form-item>

      <div class="flex justify-between mt-4">
        <n-button type="primary" @click="submitForm" :loading="isLoading" class="w-full md:w-auto">
          <template v-if="isLoading">
            <n-icon>
              <i class="n-icon-loading" />
            </n-icon>
          </template>
          <template v-else>Submit</template>
        </n-button>
        <!-- <div class="w-full md:w-auto">
          <n-button @click="resetForm" :disabled="isLoading"  ghost>Reset</n-button>
        </div> -->
      
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
  osType: 'Ubuntu'
});

const formRef = ref(null);
const isLoading = ref(false);

const osOptions = [
  { label: 'RHEL', value: 'RHEL' },
  { label: 'Centos', value: 'Centos' },
  { label: 'RedHat', value: 'RedHat' },
  { label: 'Fadora', value: 'Fadora' },
  { label: 'Ubuntu', value: 'Ubuntu' },
  { label: 'SUSE Linux', value: 'SUSE Linux' }
];

const message = useMessage();

const resetForm = () => {
  accountData.value = {
    ipAdr: '',
    serverUser: '',
    serverPass: '',
    osType: 'Ubuntu'
  };
};

const submitForm = async () => {
  isLoading.value = true;
  try {
    const response = await axios.post('http://172.16.1.56:8000/api/v3/onboard/', accountData.value);
    message.success('Bootstrapping is successful');
    console.log("API RESPONSE", response);
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
