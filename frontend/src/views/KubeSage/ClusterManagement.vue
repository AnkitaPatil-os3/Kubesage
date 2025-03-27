<template>
  <div class="kube-config-manager">
    <n-card title="Kubernetes Cluster Management" class="main-card">
      <!-- Upload Section -->
      <n-space vertical>
        <n-upload
          ref="upload"
          :custom-request="customRequest"
          :show-file-list="false"
          accept=".yaml,.yml"
          @drop.prevent="handleDrop"
          :disabled="isSubmitting"
        >
          <n-upload-dragger>
            <div class="upload-area">
              <n-icon size="48" :depth="3">
                <cloud-upload-outline />
              </n-icon>
              <n-text style="font-size: 16px; margin-top: 12px">
                Drag & drop your kubeconfig file here or click to browse
              </n-text>
              <n-text depth="3" style="font-size: 14px; margin-top: 8px">
                Allowed Only KubeConfig Files
              </n-text>
            </div>
          </n-upload-dragger>
        </n-upload>
 
        <!-- Messages -->
        <n-alert v-if="message.show" :type="message.type" :title="message.title" closable>
          {{ message.content }}
        </n-alert>
      </n-space>
 
      <!-- Clusters Table -->
      <div class="table-section">
        <n-h3>Your Kubernetes Clusters</n-h3>
        <n-data-table
          :columns="columns"
          :data="configurations"
          :bordered="false"
          :single-line="false"
          striped
          size="large"
          :loading="loading"
        />
      </div>
 
      <!-- Install Operator Dialog -->
      <n-modal v-model:show="showInstallModal" preset="dialog" title="Install Operator" positive-text="Install" negative-text="Cancel" @positive-click="confirmInstallOperator" @negative-click="cancelInstallOperator">
        <n-text>
          Are you sure you want to install the K8sGPT operator on the active cluster? This will create necessary resources in your Kubernetes cluster.
        </n-text>
      </n-modal>
    </n-card>
  </div>
</template>
 
<script setup>
import { ref, h, onMounted } from 'vue';
import { debounce } from 'lodash-es';
import {
  NCard,
  NUpload,
  NUploadDragger,
  NSpace,
  NAlert,
  NDataTable,
  NH3,
  NButton,
  NIcon,
  NText,
  NModal,
  NSwitch,
  useMessage
} from 'naive-ui';
import axios from 'axios';
import { CloudUploadOutline } from '@vicons/ionicons5';
 
// State variables
const upload = ref(null);
const configurations = ref([]);
const message = ref({ show: false, type: 'info', title: '', content: '' });
const showInstallModal = ref(false);
const activeConfigForInstall = ref(null);
const loading = ref(false);
const isSubmitting = ref(false);
const cancelTokenSource = ref(null);
const messageApi = useMessage();
 
// Get auth token from localStorage
const getAuthHeaders = () => {
  try {
    const token = JSON.parse(localStorage.getItem('accessToken')).value;
    return { Authorization: `Bearer ${token}` };
  } catch (error) {
    messageApi.error('Authentication error. Please login again.');
    return {};
  }
};
 
// API base URL
const baseUrl = 'https://10.0.34.129:8002/kubeconfig';
 
// Table columns configuration
const columns = [
  {
    title: 'S.No',
    key: 'index',
    width: 80,
    render: (row, index) => index + 1
  },
  {
    title: 'Cluster Name',
    key: 'cluster_name',
    width: 250
  },
  {
    title: 'Status',
    key: 'active',
    width: 120,
    render: (row) => {
      return h('div', { class: row.active ? 'status-active' : 'status-inactive' },
        row.active ? 'Active' : 'Inactive'
      );
    }
  },
  {
    title: 'Actions',
    key: 'actions',
    width: 350,
    render: (row) => {
      return h(NSpace, { justify: 'center', align: 'center' }, {
        default: () => [
          h(NSwitch, {
            value: row.active,
            railStyle: ({ checked }) => {
              const style = {};
              if (checked) {
                style.background = '#18a058';
              }
              return style;
            },
            onChange: (checked) => toggleActive(row.filename, checked)
          }),
          row.active ? h(NButton, {
            type: 'info',
            size: 'medium',
            onClick: () => startInstallOperator(row.filename)
          }, { default: () => 'Install Operator' }) : null,
          h(NButton, {
            type: 'error',
            size: 'medium',
            onClick: () => removeConfig(row.filename)
          }, { default: () => 'Delete' })
        ]
      });
    }
  }
];
 
// Fetch all configurations on component mount
onMounted(() => {
  console.log('Component mounted - initializing');
  fetchConfigurations();
});
 
// Custom upload request handler with debounce and submission lock
const customRequest = debounce(async ({ file }) => {
  if (isSubmitting.value) {
    console.log('Upload already in progress - skipping');
    return;
  }
 
  isSubmitting.value = true;
  
  try {
    console.log('Starting file upload');
    const formData = new FormData();
    formData.append('file', file.file);
 
    const response = await axios.post(`${baseUrl}/upload`, formData, {
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'multipart/form-data'
      }
    });
 
    if (response.status === 201) {
      console.log('Upload successful');
      showMessage('success', 'Upload Successful', 'Kubeconfig file has been uploaded.');
      await fetchConfigurations();
    }
  } catch (error) {
    console.error('Upload error:', error);
    showMessage('error', 'Upload Failed', error.response?.data?.detail || 'Could not upload the file.');
  } finally {
    isSubmitting.value = false;
  }
}, 500, { leading: true, trailing: false });
 
// Handle file drop
const handleDrop = (e) => {
  e.preventDefault();
  if (isSubmitting.value) return;
  
  const files = e.dataTransfer.files;
  if (files.length && files[0].name.match(/\.(yaml|yml)$/i)) {
    console.log('File dropped - starting upload');
    upload.value.submit(files[0]);
  }
};
 
// Fetch configurations list with cancellation
const fetchConfigurations = debounce(async () => {
  try {
    // Cancel previous request if it exists
    if (cancelTokenSource.value) {
      cancelTokenSource.value.cancel('Operation canceled due to new request');
    }
    
    cancelTokenSource.value = axios.CancelToken.source();
    
    loading.value = true;
    console.log('Fetching configurations');
    
    const response = await axios.get(`${baseUrl}/list`, {
      headers: getAuthHeaders(),
      cancelToken: cancelTokenSource.value.token
    });
 
    if (response.data && response.data.kubeconfigs) {
      console.log('Configurations fetched successfully');
      configurations.value = response.data.kubeconfigs;
    }
  } catch (error) {
    if (!axios.isCancel(error)) {
      console.error('Error fetching configurations:', error);
      showMessage('error', 'Error', 'Failed to fetch configurations.');
    }
  } finally {
    loading.value = false;
  }
}, 300);
 
// Toggle active status for a config
const toggleActive = debounce(async (filename, shouldActivate) => {
  if (isSubmitting.value) return;
  isSubmitting.value = true;
  
  try {
    if (shouldActivate) {
      console.log(`Activating config: ${filename}`);
      const response = await axios.put(`${baseUrl}/activate/${filename}`, {}, {
        headers: getAuthHeaders()
      });
 
      if (response.status === 200) {
        console.log('Activation successful');
        showMessage('success', 'Success', `Configuration "${filename}" set as active.`);
        await fetchConfigurations();
      }
    }
  } catch (error) {
    console.error('Activation error:', error);
    showMessage('error', 'Error', error.response?.data?.detail || 'Failed to activate configuration.');
  } finally {
    isSubmitting.value = false;
  }
}, 300);
 
// Remove a configuration
const removeConfig = debounce(async (filename) => {
  if (isSubmitting.value) return;
  isSubmitting.value = true;
  
  try {
    console.log(`Removing config: ${filename}`);
    const response = await axios.delete(`${baseUrl}/remove`, {
      headers: getAuthHeaders(),
      params: { filename }
    });
 
    if (response.status === 200) {
      console.log('Removal successful');
      showMessage('success', 'Success', 'Configuration successfully removed.');
      await fetchConfigurations();
    }
  } catch (error) {
    console.error('Removal error:', error);
    showMessage('error', 'Error', error.response?.data?.detail || 'Failed to delete configuration.');
  } finally {
    isSubmitting.value = false;
  }
}, 300);
 
// Show modal for installing operator
const startInstallOperator = (filename) => {
  console.log(`Preparing to install operator for: ${filename}`);
  activeConfigForInstall.value = filename;
  showInstallModal.value = true;
};
 
// Confirm operator installation
const confirmInstallOperator = debounce(async () => {
  if (isSubmitting.value) return;
  isSubmitting.value = true;
  
  try {
    console.log('Installing operator');
    const response = await axios.post(`${baseUrl}/install-operator`, {}, {
      headers: getAuthHeaders()
    });
 
    if (response.status === 200) {
      console.log('Operator installed successfully');
      showMessage('success', 'Success', 'Operator installed successfully.');
    }
  } catch (error) {
    console.error('Installation error:', error);
    showMessage('error', 'Installation Failed', error.response?.data?.detail || 'Failed to install operator.');
  } finally {
    isSubmitting.value = false;
    showInstallModal.value = false;
  }
}, 300);
 
// Cancel operator installation
const cancelInstallOperator = () => {
  console.log('Operator installation cancelled');
  showInstallModal.value = false;
  activeConfigForInstall.value = null;
};
 
// Show message helper
const showMessage = (type, title, content) => {
  message.value = {
    show: true,
    type,
    title,
    content
  };
  
  console.log(`Showing message: ${type} - ${title} - ${content}`);
  
  // Auto-hide message after 5 seconds
  setTimeout(() => {
    message.value.show = false;
  }, 5000);
};
</script>
 
<style scoped>
.kube-config-manager {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}
 
.main-card {
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
 
.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 30px 0;
}
 
.table-section {
  margin-top: 30px;
}
 
.status-active {
  background-color: #18a058;
  color: white;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  display: inline-block;
  text-align: center;
}
 
.status-inactive {
  background-color: #d03050;
  color: white;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  display: inline-block;
  text-align: center;
}
</style>
 