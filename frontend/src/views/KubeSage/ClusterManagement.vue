<template>
  <div class="app-container" :class="{ 'dark-mode': isDarkMode }">
    <div class="main-content">
      <!-- Header -->
      <div class="cluster-header">
        <h2>Kubernetes Cluster Management</h2>
       
      </div>
 
      <!-- Upload Section -->
      <div class="upload-section">
        <div class="upload-container" @dragover.prevent @drop.prevent="handleDrop">
          <div class="upload-icon">
            <i class="fas fa-cloud-upload-alt"></i>
          </div>
          <h3>Upload Kubeconfig File</h3>
          <p>Drag & drop your kubeconfig file here or click to browse</p>
          <p class="upload-hint">Allowed Only KubeConfig Files (.yaml, .yml)</p>
          <input
            type="file"
            ref="fileInput"
            accept=".yaml,.yml"
            class="file-input"
            @change="handleFileChange"
            :disabled="isSubmitting"
          />
          <n-button class="browse-btn" @click="triggerFileInput" :disabled="isSubmitting">
            Browse Files
          </n-button>
        </div>
      </div>
 
      <!-- Messages -->
      <div v-if="message.show" :class="['message-alert', `message-${message.type}`]">
        <div class="message-icon">
          <i :class="messageIcon"></i>
        </div>
        <div class="message-content">
          <div class="message-title">{{ message.title }}</div>
          <div class="message-text">{{ message.content }}</div>
        </div>
        <button class="message-close" @click="message.show = false">
          <i class="fas fa-times"></i>
        </button>
      </div>
 
      <!-- Clusters Table -->
      <div class="clusters-section">
        <h3>Your Kubernetes Clusters</h3>
        <div class="clusters-table-container">
          <table class="clusters-table">
            <thead>
              <tr>
                <th>S.No</th>
                <th>Cluster Name</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading" class="loading-row">
                <td colspan="4">
                  <div class="loading-indicator">
                    <div class="loading-spinner"></div>
                    <span>Loading clusters...</span>
                  </div>
                </td>
              </tr>
              <tr v-else-if="configurations.length === 0" class="empty-row">
                <td colspan="4">
                  <div class="empty-message">
                    <i class="fas fa-info-circle"></i>
                    <span>No clusters configured. Upload a kubeconfig file to get started.</span>
                  </div>
                </td>
              </tr>
              <tr v-for="(config, index) in configurations" :key="config.filename" class="cluster-row">
                <td>{{ index + 1 }}</td>
                <td>{{ config.cluster_name }}</td>
                <td>
                  <span :class="['status-badge', config.active ? 'status-active' : 'status-inactive']">
                    {{ config.active ? 'Active' : 'Inactive' }}
                  </span>
                </td>
                <!-- Modify the table row in the Clusters Table section -->
<td class="actions-cell">
  <div class="action-buttons">
    <label class="switch">
      <input type="checkbox" :checked="config.active" @change="toggleActive(config.filename, $event.target.checked)">
      <span class="slider round"></span>
    </label>
    <n-button
      v-if="config.active && !installedOperators.includes(config.filename)"
      class="action-btn install-btn"
      @click="startInstallOperator(config.filename)"
    >
      <i class="fas fa-download"></i> Install Operator
    </n-button>
    <n-button class="action-btn delete-btn" @click="removeConfig(config.filename)">
      <i class="fas fa-trash-alt"></i> Delete
    </n-button>
  </div>
</td>
 
              </tr>
            </tbody>
          </table>
        </div>
      </div>
 
      <!-- Install Operator Dialog -->
      <div class="modal-overlay" v-if="showInstallModal" @click.self="cancelInstallOperator">
        <div class="modal-container">
          <div class="modal-header">
            <h3>Install Operator</h3>
            <button class="close-btn" @click="cancelInstallOperator">
              <i class="fas fa-times"></i>
            </button>
          </div>
          <div class="modal-content">
            <p>Are you sure you want to install the operator on the active cluster? This will create necessary resources in your Kubernetes cluster.</p>
            <div class="modal-actions">
              <n-button class="cancel-btn" @click="cancelInstallOperator">Cancel</n-button>
              <n-button class="confirm-btn" @click="confirmInstallOperator" :disabled="isSubmitting">
                <span v-if="isSubmitting">
                  <i class="fas fa-spinner fa-spin"></i> Installing...
                </span>
                <span v-else>Install</span>
              </n-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
 
<script setup>
import { ref, onMounted, computed } from 'vue';
import { debounce } from 'lodash-es';
import axios from 'axios';
import { NButton } from 'naive-ui';
 
// State variables
const fileInput = ref(null);
const configurations = ref([]);
const message = ref({ show: false, type: 'info', title: '', content: '' });
const showInstallModal = ref(false);
const activeConfigForInstall = ref(null);
const loading = ref(false);
const isSubmitting = ref(false);
const cancelTokenSource = ref(null);
const isDarkMode = ref(localStorage.getItem('darkMode') === 'true');
 
const installedOperators = ref([]);
// Toggle light/dark mode
const toggleTheme = () => {
  isDarkMode.value = !isDarkMode.value;
  localStorage.setItem('darkMode', isDarkMode.value);
  updateDarkModeClasses();
};
 
// Update dark mode classes
const updateDarkModeClasses = () => {
  if (isDarkMode.value) {
    document.documentElement.classList.add('dark');
    document.body.style.backgroundColor = 'rgb(24 24 28)';
  } else {
    document.documentElement.classList.remove('dark');
    document.body.style.backgroundColor = '';
  }
};
 
// Computed property for message icon
const messageIcon = computed(() => {
  switch (message.value.type) {
    case 'success': return 'fas fa-check-circle';
    case 'error': return 'fas fa-exclamation-circle';
    case 'warning': return 'fas fa-exclamation-triangle';
    default: return 'fas fa-info-circle';
  }
});
 
// Get auth token from localStorage
const getAuthHeaders = () => {
  try {
    const token = JSON.parse(localStorage.getItem('accessToken')).value;
    return { Authorization: `Bearer ${token}` };
  } catch (error) {
    console.error('Authentication error. Please login again.');
    return {};
  }
};
 
// API base URL
const baseUrl = 'https://10.0.34.171:8002/kubeconfig';
 
// Trigger file input click
const triggerFileInput = () => {
  if (fileInput.value) {
    fileInput.value.click();
  }
};
 
// Handle file selection
const handleFileChange = (event) => {
  const file = event.target.files[0];
  if (file) {
    uploadFile(file);
  }
};
 
// Handle file drop
const handleDrop = (e) => {
  e.preventDefault();
  if (isSubmitting.value) return;
  
  const files = e.dataTransfer.files;
  if (files.length && files[0].name.match(/\.(yaml|yml)$/i)) {
    uploadFile(files[0]);
  } else {
    showMessage('error', 'Invalid File', 'Please upload a valid kubeconfig file (.yaml or .yml)');
  }
};
 
// Upload file to server
const uploadFile = async (file) => {
  if (isSubmitting.value) return;
  isSubmitting.value = true;
  
  try {
    console.log('Starting file upload');
    const formData = new FormData();
    formData.append('file', file);
 
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
    // Reset file input
    if (fileInput.value) {
      fileInput.value.value = '';
    }
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
// Modify the confirmInstallOperator function
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
      // Add the current config to installed operators list
      if (activeConfigForInstall.value && !installedOperators.value.includes(activeConfigForInstall.value)) {
        installedOperators.value.push(activeConfigForInstall.value);
      }
    }
  } catch (error) {
    console.error('Installation error:', error);
    // If the error indicates operator is already installed, add to installed list
    if (error.response?.data?.detail?.includes('already installed') ||
        error.message?.includes('already installed')) {
      if (activeConfigForInstall.value && !installedOperators.value.includes(activeConfigForInstall.value)) {
        installedOperators.value.push(activeConfigForInstall.value);
      }
    }
    showMessage('error', 'Installation Failed', error.response?.data?.detail || 'Operator is already installed.');
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
 
// Fetch configurations on component mount
onMounted(() => {
  console.log('Component mounted - initializing');
  fetchConfigurations();
  updateDarkModeClasses();
});
</script>
 
<style scoped>
/* Import Font Awesome */
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');
 
/* Main container */
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: #f8f9fa;
  background-image: linear-gradient(to bottom right, #f8f9fa, #e8f5e9);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
}
 
.app-container.dark-mode {
  background-color: #1a1a1a;
  background-image: linear-gradient(to bottom right, #1a1a1a, #0d2d0f);
  color: #f0f0f0;
}
 
.main-content {
  flex: 1;
  padding: 20px;
  max-width: 100%;
  margin: 0 auto;
  width: 100%;
}
 
/* Header */
.cluster-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background-color: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(16, 188, 59, 0.08);
  margin-bottom: 24px;
  border-left: 4px solid #10BC3B;
}
 
.app-container.dark-mode .cluster-header {
  background-color: #222222;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  border-left: 4px solid #10BC3B;
}
 
.cluster-header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: #10BC3B;
  letter-spacing: 0.5px;
}
 
.app-container.dark-mode .cluster-header h2 {
  color: #10BC3B;
}
 
.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}
 
.toggle-theme-btn {
  background: transparent;
  border: none;
  color: #10BC3B;
  cursor: pointer;
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s ease;
}
 
.toggle-theme-btn:hover {
  background-color: rgba(16, 188, 59, 0.1);
}
 
.app-container.dark-mode .toggle-theme-btn {
  color: #10BC3B;
}
 
.app-container.dark-mode .toggle-theme-btn:hover {
  background-color: rgba(16, 188, 59, 0.2);
}
 
/* Upload Section */
.upload-section {
  margin-bottom: 24px;
}
 
.upload-container {
  background-color: #ffffff;
  background-image: linear-gradient(135deg, #ffffff, #f5fff7);
  border: 2px dashed #10BC3B;
  border-radius: 12px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(16, 188, 59, 0.05);
}
 
.app-container.dark-mode .upload-container {
  background-color: #222222;
  background-image: linear-gradient(135deg, #222222, #1a2e1d);
  border-color: #10BC3B;
  box-shadow: 0 4px 12px rgba(16, 188, 59, 0.1);
}
 
.upload-container:hover {
  border-color: #10BC3B;
  background-color: #f0fff5;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(16, 188, 59, 0.1);
}
 
.app-container.dark-mode .upload-container:hover {
  border-color: #10BC3B;
  background-color: #1a2e1d;
  box-shadow: 0 6px 16px rgba(16, 188, 59, 0.15);
}
 
.upload-icon {
  font-size: 48px;
  color: #10BC3B;
  margin-bottom: 16px;
}
 
.app-container.dark-mode .upload-icon {
  color: #10BC3B;
}
 
.upload-container h3 {
  margin: 0 0 8px;
  font-size: 1.25rem;
  font-weight: 600;
  color: #10BC3B;
}
 
.app-container.dark-mode .upload-container h3 {
  color: #10BC3B;
}
 
.upload-container p {
  margin: 0 0 8px;
  color: #4a5568;
  font-size: 0.95rem;
}
 
.app-container.dark-mode .upload-container p {
  color: #a0aec0;
}
 
.upload-hint {
  font-size: 0.85rem !important;
  color: #718096 !important;
}
 
.app-container.dark-mode .upload-hint {
  color: #718096 !important;
}
 
.file-input {
  display: none;
}
 
:deep(.browse-btn) {
  margin-top: 16px;
  background: linear-gradient(135deg, #10BC3B, #09a431) !important;
  border: none !important;
  color: white !important;
  padding: 10px 24px !important;
  border-radius: 8px !important;
  font-size: 0.95rem !important;
  font-weight: 500 !important;
  cursor: pointer !important;
  transition: all 0.3s ease !important;
  box-shadow: 0 4px 12px rgba(16, 188, 59, 0.2) !important;
}
 
:deep(.browse-btn:hover) {
  background: linear-gradient(135deg, #09a431, #078a29) !important;
  box-shadow: 0 6px 16px rgba(16, 188, 59, 0.3) !important;
  transform: translateY(-2px) !important;
}
 
:deep(.browse-btn:disabled) {
  background: #a0aec0 !important;
  cursor: not-allowed !important;
  box-shadow: none !important;
  transform: none !important;
}
 
/* Message Alert */
.message-alert {
  display: flex;
  align-items: flex-start;
  padding: 16px;
  border-radius: 10px;
  margin-bottom: 24px;
  animation: slideIn 0.3s ease;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}
 
@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
 
.message-success {
  background-color: rgba(16, 185, 129, 0.1);
  border-left: 4px solid #10BC3B;
}
 
.message-error {
  background-color: rgba(239, 68, 68, 0.1);
  border-left: 4px solid #ef4444;
}
 
.message-warning {
  background-color: rgba(245, 158, 11, 0.1);
  border-left: 4px solid #f59e0b;
}
 
.message-info {
  background-color: rgba(59, 130, 246, 0.1);
  border-left: 4px solid #3b82f6;
}
 
.message-icon {
  font-size: 20px;
  margin-right: 16px;
}
 
.message-success .message-icon {
  color: #10BC3B;
}
 
.message-error .message-icon {
  color: #ef4444;
}
 
.message-warning .message-icon {
  color: #f59e0b;
}
 
.message-info .message-icon {
  color: #3b82f6;
}
 
.message-content {
  flex: 1;
}
 
.message-title {
  font-weight: 600;
  margin-bottom: 4px;
  color: #111827;
}
 
.app-container.dark-mode .message-title {
  color: #f0f0f0;
}
 
.message-text {
  color: #4a5568;
  font-size: 0.95rem;
}
 
.app-container.dark-mode .message-text {
  color: #a0aec0;
}
 
.message-close {
  background: transparent;
  border: none;
  color: #6b7280;
  cursor: pointer;
  padding: 4px;
  font-size: 14px;
  transition: color 0.2s ease;
}
 
.message-close:hover {
  color: #111827;
}
 
.app-container.dark-mode .message-close:hover {
  color: #f0f0f0;
}
 
/* Clusters Section */
.clusters-section {
  background-color: #ffffff;
  background-image: linear-gradient(135deg, #ffffff, #f5fff7);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(16, 188, 59, 0.08);
  padding: 24px;
  margin-bottom: 24px;
  border-bottom: 3px solid #10BC3B;
}
 
.app-container.dark-mode .clusters-section {
  background-color: #222222;
  background-image: linear-gradient(135deg, #222222, #1a2e1d);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  border-bottom: 3px solid #10BC3B;
}
 
.clusters-section h3 {
  margin: 0 0 16px;
  font-size: 1.25rem;
  font-weight: 600;
  color: #10BC3B;
  letter-spacing: 0.5px;
}
 
.app-container.dark-mode .clusters-section h3 {
  color: #10BC3B;
}
 
.clusters-table-container {
  overflow-x: auto;
}
 
.clusters-table {
  width: 100%;
  border-collapse: collapse;
}
 
.clusters-table th {
  text-align: left;
  padding: 14px 16px;
  font-size: 0.9rem;
  font-weight: 600;
  color: #4a5568;
  border-bottom: 1px solid #e2e8f0;
  background-color: #f7fafc;
}
 
.app-container.dark-mode .clusters-table th {
  color: #a0aec0;
  border-bottom: 1px solid #2d3748;
  background-color: #1a202c;
}
 
.clusters-table td {
  padding: 16px;
  border-bottom: 1px solid #e2e8f0;
  color: #2d3748;
}
 
.app-container.dark-mode .clusters-table td {
  color: #e2e8f0;
  border-bottom: 1px solid #2d3748;
}
 
.cluster-row {
  transition: all 0.2s ease;
}
 
.cluster-row:hover {
  background-color: rgba(16, 188, 59, 0.05);
}
 
.app-container.dark-mode .cluster-row:hover {
  background-color: rgba(16, 188, 59, 0.1);
}
 
.loading-row td {
  padding: 32px 16px;
}
 
.loading-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}
 
.loading-spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #e2e8f0;
  border-top-color: #10BC3B;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
 
.app-container.dark-mode .loading-spinner {
  border-color: #2d3748;
  border-top-color: #10BC3B;
}
 
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
 
.empty-row td {
  padding: 32px 16px;
}
 
.empty-message {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #718096;
}
 
.app-container.dark-mode .empty-message {
  color: #a0aec0;
}
 
.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 500;
  text-align: center;
}
 
.status-active {
  background-color: #10BC3B;
  color: white;
  box-shadow: 0 2px 6px rgba(16, 188, 59, 0.2);
}
 
.status-inactive {
  background-color: #ef4444;
  color: white;
  box-shadow: 0 2px 6px rgba(239, 68, 68, 0.2);
}
 
.actions-cell {
  width: 350px;
}
 
.action-buttons {
  display: flex;
  align-items: center;
  gap: 12px;
}
 
/* Toggle Switch */
.switch {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 24px;
}
 
.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
 
.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #cbd5e0;
  transition: .4s;
}
 
.app-container.dark-mode .slider {
  background-color: #4a5568;
}
 
.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: .4s;
}
 
input:checked + .slider {
  background-color: #10BC3B;
}
 
input:checked + .slider {
  background-color: #10BC3B;
}
 
input:focus + .slider {
  box-shadow: 0 0 1px #10BC3B;
}
 
input:checked + .slider:before {
  transform: translateX(24px);
}
 
.slider.round {
  border-radius: 24px;
}
 
.slider.round:before {
  border-radius: 50%;
}
 
/* Action Buttons */
:deep(.action-btn) {
  padding: 8px 12px;
  border: none;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s ease;
}
 
:deep(.install-btn) {
  background: linear-gradient(135deg, #10BC3B, #09a431) !important;
  border: none !important;
  color: white !important;
  box-shadow: 0 2px 6px rgba(16, 188, 59, 0.2) !important;
}
 
:deep(.install-btn:hover) {
  background: linear-gradient(135deg, #09a431, #078a29) !important;
  box-shadow: 0 4px 8px rgba(16, 188, 59, 0.3) !important;
  transform: translateY(-2px) !important;
}
 
:deep(.delete-btn) {
  background-color: rgba(239, 68, 68, 0.1) !important;
  color: #ef4444 !important;
  border: 1px solid rgba(239, 68, 68, 0.2) !important;
}
 
:deep(.delete-btn:hover) {
  background-color: rgba(239, 68, 68, 0.2) !important;
  border-color: rgba(239, 68, 68, 0.3) !important;
  transform: translateY(-2px) !important;
}
 
.app-container.dark-mode :deep(.delete-btn) {
  background-color: rgba(239, 68, 68, 0.2) !important;
  border-color: rgba(239, 68, 68, 0.3) !important;
}
 
.app-container.dark-mode :deep(.delete-btn:hover) {
  background-color: rgba(239, 68, 68, 0.3) !important;
  border-color: rgba(239, 68, 68, 0.4) !important;
}
 
/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}
 
.modal-container {
  background-color: #ffffff;
  background-image: linear-gradient(135deg, #ffffff, #f5fff7);
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-bottom: 3px solid #10BC3B;
}
 
.app-container.dark-mode .modal-container {
  background-color: #222222;
  background-image: linear-gradient(135deg, #222222, #1a2e1d);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
  border-bottom: 3px solid #10BC3B;
}
 
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid #e2e8f0;
}
 
.app-container.dark-mode .modal-header {
  border-bottom: 1px solid #2d3748;
}
 
.modal-header h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #10BC3B;
}
 
.close-btn {
  background: transparent;
  border: none;
  color: #718096;
  cursor: pointer;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}
 
.close-btn:hover {
  background-color: rgba(16, 188, 59, 0.1);
  color: #10BC3B;
}
 
.app-container.dark-mode .close-btn {
  color: #a0aec0;
}
 
.app-container.dark-mode .close-btn:hover {
  background-color: rgba(16, 188, 59, 0.2);
  color: #10BC3B;
}
 
.modal-content {
  padding: 24px;
}
 
.modal-content p {
  margin: 0 0 24px;
  color: #4a5568;
  line-height: 1.6;
}
 
.app-container.dark-mode .modal-content p {
  color: #a0aec0;
}
 
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
 
:deep(.cancel-btn) {
  background-color: #e2e8f0 !important;
  color: #4a5568 !important;
  border: none !important;
  padding: 8px 16px !important;
  border-radius: 8px !important;
  font-size: 0.95rem !important;
  font-weight: 500 !important;
  cursor: pointer !important;
  transition: all 0.2s ease !important;
}
 
:deep(.cancel-btn:hover) {
  background-color: #cbd5e0 !important;
  color: #2d3748 !important;
}
 
.app-container.dark-mode :deep(.cancel-btn) {
  background-color: #2d3748 !important;
  color: #e2e8f0 !important;
}
 
.app-container.dark-mode :deep(.cancel-btn:hover) {
  background-color: #4a5568 !important;
}
 
:deep(.confirm-btn) {
  background: linear-gradient(135deg, #10BC3B, #09a431) !important;
  border: none !important;
  color: white !important;
  padding: 8px 16px !important;
  border-radius: 8px !important;
  font-size: 0.95rem !important;
  font-weight: 500 !important;
  cursor: pointer !important;
  transition: all 0.2s ease !important;
  box-shadow: 0 2px 6px rgba(16, 188, 59, 0.2) !important;
}
 
:deep(.confirm-btn:hover) {
  background: linear-gradient(135deg, #09a431, #078a29) !important;
  box-shadow: 0 4px 8px rgba(16, 188, 59, 0.3) !important;
}
 
:deep(.confirm-btn:disabled) {
  background: #a0aec0 !important;
  cursor: not-allowed !important;
  box-shadow: none !important;
}
 
/* Responsive adjustments */
@media (max-width: 768px) {
  .action-buttons {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .actions-cell {
    width: auto;
  }
  
  .cluster-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .header-actions {
    align-self: flex-end;
  }
}
</style>
 
 
 
 