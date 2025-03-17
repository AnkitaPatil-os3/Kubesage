<template>
  <n-card class="p-6 rounded-lg shadow-md">
    <n-text class="text-2xl font-bold">
      Bootstrap the Gitlab Server
    </n-text>
    <n-form @submit.prevent="submitForm" :model="accountData" ref="formRef">
      <n-form-item label="Server IP/Hostname" path="ipAdr">
        <n-input v-model:value="accountData.ipAdr" placeholder="0.0.0.0" class="w-full" />
      </n-form-item>

      <n-form-item label="Server Username" path="serverUser">
        <n-input v-model:value="accountData.serverUser" placeholder="Username" class="w-full" />
      </n-form-item>

      <n-form-item label="Server Password" path="serverPass">
        <n-input v-model:value="accountData.serverPass"  show-password-on="mousedown" placeholder="Password" type="password" class="w-full" />
      </n-form-item>
      <n-form-item label="GitLab Url" path="GitlabUrl">
        <n-input v-model:value="accountData.GitlabUrl" type="url" placeholder="GitLab Url" class="w-full" />
      </n-form-item>
      <n-form-item label="GitLab Token" path="GitlabToken">
        <n-input v-model:value="accountData.GitlabToken" placeholder="GitLab Token" type="password"  show-password-on="mousedown" class="w-full" />
      </n-form-item>

     

      <!-- <n-form-item label="Access Key" path="osType">
        <n-select v-model:value="accountData.osType" :options="osOptions" placeholder="Access Key" class="w-full" />
      </n-form-item> -->

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
  GitlabToken: '',
  GitlabUrl: '',

  // osType: 'Ubuntu'
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
    GitlabToken: '',
    GitlabUrl: '',

  //   osType: 'Ubuntu'
  };
};

const submitForm = async () => {
  isLoading.value = true;
  try {
    const response = await axios.post('http://172.16.1.56:8000/api/v3/OnboardGitlab/', accountData.value);
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
