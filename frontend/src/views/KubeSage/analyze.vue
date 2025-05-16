<template>
  <div class="app-container" :class="{ 'dark-mode': isDarkMode }">
    <div class="main-content">
      <!-- Header -->
      <div class="analyze-header">
        <h2>KubeSage Analyzer</h2>
        <div class="header-actions">
          <n-select
            v-model:value="selectedNamespace"
            :options="namespaceOptions"
            class="namespace-select"
            placeholder="Select a namespace"
            @update:value="fetchNamespaces"
          />
        </div>
      </div>

      <!-- Resource Cards -->
      <div class="resource-grid">
        <div class="resource-card" @click="goToPods">
          <div class="card-icon"><i class="fas fa-cube"></i></div>
          <div class="card-title">Pods</div>
          <div class="card-description">Analyze pod configurations and identify issues</div>
          <n-button class="analyze-btn" :disabled="loadingResource !== ''" @click.stop="goToPods">
            <template v-if="loadingResource === 'Pod'">loading .
              <i class="fas fa-spinner fa-spin"></i>
            </template>
            <template v-else>
              Analyze Pods
            </template>
          </n-button>
        </div>

        <div class="resource-card" @click="goToDeployments">
          <div class="card-icon accent-1"><i class="fas fa-layer-group"></i></div>
          <div class="card-title">Deployments</div>
          <div class="card-description">Check deployment configurations and best practices</div>
          <n-button class="analyze-btn" :disabled="loadingResource !== ''" @click.stop="goToDeployments">
            <template v-if="loadingResource === 'Deployment'">loading .
              <i class="fas fa-spinner fa-spin"></i>
            </template>
            <template v-else>
              Analyze Deployments
            </template>
          </n-button>
        </div>

        <div class="resource-card" @click="goToServices">
          <div class="card-icon accent-2"><i class="fas fa-network-wired"></i></div>
          <div class="card-title">Services</div>
          <div class="card-description">Validate service configurations and connectivity</div>
          <n-button class="analyze-btn" :disabled="loadingResource !== ''" @click.stop="goToServices">
            <template v-if="loadingResource === 'Service'">loading .
              <i class="fas fa-spinner fa-spin"></i>
            </template>
            <template v-else>
              Analyze Services
            </template>
          </n-button>
        </div>

        <div class="resource-card" @click="goToStorageClass">
          <div class="card-icon accent-3"><i class="fas fa-database"></i></div>
          <div class="card-title">StorageClasses</div>
          <div class="card-description">Review storage class configurations</div>
          <n-button class="analyze-btn" :disabled="loadingResource !== ''" @click.stop="goToStorageClass">
            <template v-if="loadingResource === 'StorageClass'">loading .
              <i class="fas fa-spinner fa-spin"></i>
            </template>
            <template v-else>
              Analyze StorageClasses
            </template>
          </n-button>
        </div>

        <div class="resource-card" @click="goToSecrets">
          <div class="card-icon accent-4"><i class="fas fa-key"></i></div>
          <div class="card-title">Secrets</div>
          <div class="card-description">Check secret configurations and security</div>
          <n-button class="analyze-btn" :disabled="loadingResource !== ''" @click.stop="goToSecrets">
            <template v-if="loadingResource === 'Secret'">loading .
              <i class="fas fa-spinner fa-spin"></i>
            </template>
            <template v-else>
              Analyze Secrets
            </template>
          </n-button>
        </div>

        <div class="resource-card" @click="goToIngress">
          <div class="card-icon accent-5"><i class="fas fa-route"></i></div>
          <div class="card-title">Ingress</div>
          <div class="card-description">Validate ingress rules and configurations</div>
          <n-button class="analyze-btn" :disabled="loadingResource !== ''" @click.stop="goToIngress">
            <template v-if="loadingResource === 'Ingress'">loading .
              <i class="fas fa-spinner fa-spin"></i>
            </template>
            <template v-else>
              Analyze Ingress
            </template>
          </n-button>
        </div>

        <div class="resource-card" @click="goToPVC">
          <div class="card-icon accent-6"><i class="fas fa-hdd"></i></div>
          <div class="card-title">PVC</div>
          <div class="card-description">Check persistent volume claim configurations</div>
          <n-button class="analyze-btn" :disabled="loadingResource !== ''" @click.stop="goToPVC">
            <template v-if="loadingResource === 'PersistentVolumeClaim'">loading .
              <i class="fas fa-spinner fa-spin"></i>
            </template>
            <template v-else>
              Analyze PVC
            </template>
          </n-button>
        </div>
      </div>

      <!-- Analysis Result Modal -->
      <div class="modal-overlay" v-if="showAnalysisResult" @click.self="closeAnalysisResult">
        <div class="modal-container">
          <div class="modal-header">
            <h3>Analysis Results</h3>
            <button class="close-btn" @click="closeAnalysisResult">
              <i class="fas fa-times"></i>
            </button>
          </div>
          <div class="modal-content">
            <div v-html="analysisResult"></div>
          </div>
        </div>
      </div>

      <!-- Popup Message Modal -->
      <div class="modal-overlay" v-if="showPopupMessage" @click.self="closePopupMessage">
        <div class="modal-container">
          <div class="modal-header">
            <h3>Message</h3>
            <button class="close-btn" @click="closePopupMessage">
              <i class="fas fa-times"></i>
            </button>
          </div>
          <div class="modal-content">
            <p>{{ popupMessage }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import axios from 'axios';
import {
  NSelect,
  NButton
} from 'naive-ui';

const selectedNamespace = ref(''); // Default namespace
const namespaces = ref([]);
const showAnalysisResult = ref(false);
const analysisResult = ref('');
const isDarkMode = ref(localStorage.getItem('darkMode') === 'true');

// New reactive state for loading buttons
const loadingResource = ref(''); // holds resource type currently loading

// API base URL
const baseUrl = import.meta.env.VITE_KUBECONFIG_SERVICE ;

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


 
// Fetch namespaces from the backend
const fetchNamespaces = async () => {
  try {
    const headers = getAuthHeaders();
    const response = await axios.get(`${baseUrl}/kubeconfig/namespaces`, { headers });
    namespaces.value = response.data.namespaces;
 
    // If selectedNamespace is empty or not in the list, set it to default (only once)
    if (!selectedNamespace.value || !namespaces.value.includes(selectedNamespace.value)) {
      selectedNamespace.value = namespaces.value.includes('default') ? 'default' : namespaces.value[0] || '';
    }
  } catch (error) {
    console.error('Error fetching namespaces:', error);
  }
};

const popupMessage = ref('');
const showPopupMessage = ref(false);

const closePopupMessage = () => {
  showPopupMessage.value = false;
  popupMessage.value = '';
};

const analyzeK8sResource = async (resourceType) => {
  if (!selectedNamespace.value) {
    popupMessage.value = "Please select a namespace first.";
    showPopupMessage.value = true;
    return;
  }

  loadingResource.value = resourceType; // set loading state

  try {
    const headers = getAuthHeaders(); // Get authentication headers

    // Define query parameters
    const params = {
      // backend: "ollama",
      explain: true,
      filter: resourceType, // Send resource type as filter
      "max-concurrency": 5,
      namespace: selectedNamespace.value, // Namespace from selection
      output: "json"
    };

    console.log("Query Parameters:", params);

    // Axios POST request with query parameters
    const response = await axios.post(`${baseUrl}/kubeconfig/analyze`, null, { headers, params });

    if (response.status === 200) {
      const { status, results } = response.data;

      if (status === "OK" && results === null) {
        analysisResult.value = `<p class="success-message">No issues found for ${resourceType} in namespace ${selectedNamespace.value}.</p>`;
      } else if (status === "ProblemDetected" && results) {
        let errorMessages = results.map((result, index) => {
          let errorText =
            result.error?.map((err) => `<span class="error-text">${err.Text}</span>`).join("<br>") ||
            "No error details available";
          // Extract solution details
let solutionText =
  result.details
    ?.split("Solution:")[1]
    ?.trim()
    ?.split(/\d+\.\s*/)
    ?.filter(s => s.trim() !== '')
    ?.map((solution, idx) => {
      const number = idx + 1;
      const text = solution.trim().replace(/\n/g, '<br>&nbsp;&nbsp;&nbsp;&nbsp;');
      return `<li class="solution-item"><span class="solution-number">${number}. </span><span class="solution-text">${text}</span></li>`;
    })
    .join("") || "No solution details available";

          return `
            <div class="problem-item">
              <h4 class="problem-title">Problem ${index + 1}: ${result.name}</h4>
              <div class="problem-error">
                <strong>Error:</strong><br> ${errorText}
              </div>
              <div class="problem-solution">
                <strong>Solution:</strong>
                <ul class="solution-list">${solutionText}</ul>
              </div>
            </div>
          `;
        }).join("");

        analysisResult.value = `
          <h3 class="problems-header">Problems Detected (${response.data.problems}):</h3>
          ${errorMessages}
        `;
      } else {
        analysisResult.value = `<p class="warning-message">Unknown response status.</p>`;
      }

      showAnalysisResult.value = true;
    } else {
      analysisResult.value = `<p class="error-message">Something went wrong. Please try again.</p>`;
      showAnalysisResult.value = true;
    }
  } catch (error) {
    console.error(`Error analyzing ${resourceType}:`, error);
    analysisResult.value = `<p class="error-message">Error: ${error.message}</p>`;
    showAnalysisResult.value = true;
  } finally {
    loadingResource.value = ''; // reset loading state
  }
};

// Button click handlers
const goToPods = () => analyzeK8sResource('Pod');
const goToDeployments = () => analyzeK8sResource('Deployment');
const goToServices = () => analyzeK8sResource('Service');
const goToStorageClass = () => analyzeK8sResource('StorageClass');
const goToSecrets = () => analyzeK8sResource('Secret');
const goToIngress = () => analyzeK8sResource('Ingress');
const goToPVC = () => analyzeK8sResource('PersistentVolumeClaim');

// Close the analysis result modal
const closeAnalysisResult = () => {
  showAnalysisResult.value = false;
};

// Fetch namespaces on component mount
onMounted(() => {
  fetchNamespaces();
  updateDarkModeClasses();
});

// Namespace options for the dropdown
const namespaceOptions = computed(() => {
  return namespaces.value.map(namespace => ({
    label: namespace,
    value: namespace,
  }));
});
</script>

<style scoped>
/* Import Font Awesome */
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');

/* Main container */
.app-container {
  width: 100%;
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
.analyze-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background-color: #ffffff;
  background-image: linear-gradient(135deg, #ffffff, #f5fff7);
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(16, 188, 59, 0.08);
  margin-bottom: 24px;
  border-left: 4px solid #10BC3B;
}

.app-container.dark-mode .analyze-header {
  background-color: #222222;
  background-image: linear-gradient(135deg, #222222, #1a2e1d);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  border-left: 4px solid #10BC3B;
}

.analyze-header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: #10BC3B;
  letter-spacing: 0.5px;
}

.app-container.dark-mode .analyze-header h2 {
  color: #10BC3B;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.namespace-select {
  width: 200px;
}

:deep(.n-base-selection) {
  border-color: #10BC3B !important;
}

:deep(.n-base-selection:hover) {
  border-color: #09a431 !important;
}

:deep(.n-base-selection-placeholder) {
  color: #718096 !important;
}

:deep(.n-base-selection-tags) {
  color: #10BC3B !important;
}

/* Resource Grid */
.resource-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 24px;
}

.resource-card {
  background-color: #ffffff;
  background-image: linear-gradient(135deg, #ffffff, #f9fdf9);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  cursor: pointer;
  border-top: 3px solid transparent;
  height: 100%;
}

.app-container.dark-mode .resource-card {
  background-color: #222222;
  background-image: linear-gradient(135deg, #222222, #1e261f);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.2);
}

.resource-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 12px 28px rgba(16, 188, 59, 0.12);
  border-top: 3px solid #10BC3B;
}

.app-container.dark-mode .resource-card:hover {
  box-shadow: 0 12px 28px rgba(16, 188, 59, 0.2);
  border-top: 3px solid #10BC3B;
}

.card-icon {
  width: 70px;
  height: 70px;
  border-radius: 50%;
  background: linear-gradient(135deg, #e0ffe5, #c5f1d0);
  color: #10BC3B;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  font-size: 26px;
  box-shadow: 0 4px 12px rgba(16, 188, 59, 0.15);
}

.card-icon.accent-1 {
  background: linear-gradient(135deg, #e0f7ff, #c5e8f1);
  color: #0a8aaa;
}

.card-icon.accent-2 {
  background: linear-gradient(135deg, #fff0e0, #f1e2c5);
  color: #aa7b0a;
}

.card-icon.accent-3 {
  background: linear-gradient(135deg, #f5e0ff, #e5c5f1);
  color: #8a0aaa;
}

.card-icon.accent-4 {
  background: linear-gradient(135deg, #ffe0e0, #f1c5c5);
  color: #aa0a0a;
}

.card-icon.accent-5 {
  background: linear-gradient(135deg, #e0ffe0, #c5f1c5);
  color: #0aaa0a;
}

.card-icon.accent-6 {
  background: linear-gradient(135deg, #e0e0ff, #c5c5f1);
  color: #0a0aaa;
}

.app-container.dark-mode .card-icon {
  background: linear-gradient(135deg, #0a7024, #0d8c2c);
  color: #e0ffe5;
  box-shadow: 0 4px 12px rgba(16, 188, 59, 0.3);
}

.app-container.dark-mode .card-icon.accent-1 {
  background: linear-gradient(135deg, #0a5e74, #0c7490);
  color: #e0f7ff;
}

.app-container.dark-mode .card-icon.accent-2 {
  background: linear-gradient(135deg, #745a0a, #907c0c);
  color: #fff0e0;
}

.app-container.dark-mode .card-icon.accent-3 {
  background: linear-gradient(135deg, #5a0a74, #7c0c90);
  color: #f5e0ff;
}

.app-container.dark-mode .card-icon.accent-4 {
  background: linear-gradient(135deg, #740a0a, #900c0c);
  color: #ffe0e0;
}

.app-container.dark-mode .card-icon.accent-5 {
  background: linear-gradient(135deg, #0a740a, #0c900c);
  color: #e0ffe0;
}

.app-container.dark-mode .card-icon.accent-6 {
  background: linear-gradient(135deg, #0a0a74, #0c0c90);
  color: #e0e0ff;
}

.card-title {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 8px;
  color: #10BC3B;
  letter-spacing: 0.3px;
}

.app-container.dark-mode .card-title {
  color: #10BC3B;
}

.card-description {
  font-size: 0.95rem;
  color: #4a5568;
  margin-bottom: 20px;
  line-height: 1.6;
  flex-grow: 1;
}

.app-container.dark-mode .card-description {
  color: #a0aec0;
}

:deep(.analyze-btn) {
  background: linear-gradient(135deg, #10BC3B, #09a431) !important;
  border: none !important;
  color: white !important;
  padding: 8px 16px !important;
  border-radius: 8px !important;
  font-size: 0.9rem !important;
  font-weight: 500 !important;
  cursor: pointer !important;
  transition: all 0.3s ease !important;
  box-shadow: 0 4px 12px rgba(16, 188, 59, 0.2) !important;
  width: 80%;
}

:deep(.analyze-btn:hover) {
  background: linear-gradient(135deg, #09a431, #078a29) !important;
  box-shadow: 0 6px 16px rgba(16, 188, 59, 0.3) !important;
  transform: translateY(-2px) !important;
}

/* Modal */
.modal-overlay {
  position: fixed;
  z-index: 1000;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  /* z-index: 100; */
  backdrop-filter: blur(4px);
}

.modal-container {
  background-color: #ffffff;
  background-image: linear-gradient(135deg, #ffffff, #f5fff7);
  border-radius: 16px;
  width: 90%;
  max-width: 800px;
  max-height: 70vh;
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
  letter-spacing: 0.5px;
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
  padding: 28px 32px;
  overflow-y: auto;
  max-height: calc(80vh - 70px);
  /* background: linear-gradient(135deg, #d4f8d4, #a6e6a6); */
  border-radius: 0;
  box-shadow: 0 10px 30px rgba(16, 188, 59, 0.25);
  color: #145214;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  font-size: 1.05rem;
  line-height: 1.7;
  /* border: 1.5px solid #4caf50; */
  transition: background-color 0.3s ease, color 0.3s ease;
}

.modal-content p {
  margin-bottom: 1.1rem;
  color: #2e7d32;
  font-weight: 600;
}

.modal-content h3,
.modal-content h4 {
  color: #1b5e20;
  font-weight: 800;
  margin-bottom: 0.85rem;
  text-shadow: 0 1px 3px rgba(76, 175, 80, 0.5);
}

.modal-content ul {
  padding-left: 1.75rem;
  margin-bottom: 1.1rem;
  color: #1b5e20;
}

.modal-content li {
  margin-bottom: 0.6rem;
  font-weight: 600;
}

.modal-content strong {
  color: #145214;
  font-weight: 800;
}

.app-container.dark-mode .modal-content {
  background: linear-gradient(135deg, #0f2f0f, #164916);
  box-shadow: 0 10px 30px rgba(16, 188, 59, 0.7);
  color: #a8d5a8;
  border: 1.5px solid #4caf50;
}

.app-container.dark-mode .modal-content p {
  color: #b2d8b2;
}

.app-container.dark-mode .modal-content h3,
.app-container.dark-mode .modal-content h4 {
  color: #81c784;
  text-shadow: 0 1px 3px rgba(76, 175, 80, 0.8);
}

.app-container.dark-mode .modal-content ul {
  color: #81c784;
}

.app-container.dark-mode .modal-content li {
  color: #b2d8b2;
}

.app-container.dark-mode .modal-content strong {
  color: #a5d6a7;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .resource-grid {
    grid-template-columns: 1fr;
  }
  
  .analyze-header {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
  }
  
  .header-actions {
    width: 100%;
    justify-content: space-between;
  }
  
  .namespace-select {
    width: 100%;
  }
  
  .modal-container {
    width: 95%;
    max-height: 90vh;
  }
}
/* Animation keyframes */
@keyframes fadeInUp {
  0% {
    opacity: 0;
    transform: translateY(20px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Apply animation to problem items */
.problem-item {
  animation-name: fadeInUp;
  animation-duration: 0.6s;
  animation-fill-mode: both;
  animation-timing-function: ease-out;
  opacity: 0;
  animation-delay: 0s;
  animation-play-state: running;
  transition: box-shadow 0.3s ease, border-color 0.3s ease;
  cursor: default;
}

/* Stagger animation delays for each problem item */
.problem-item:nth-child(1) {
  animation-delay: 0.1s;
  opacity: 1;
}
.problem-item:nth-child(2) {
  animation-delay: 0.3s;
  opacity: 1;
}
.problem-item:nth-child(3) {
  animation-delay: 0.5s;
  opacity: 1;
}
.problem-item:nth-child(4) {
  animation-delay: 0.7s;
  opacity: 1;
}
.problem-item:nth-child(5) {
  animation-delay: 0.9s;
  opacity: 1;
}
.problem-item:nth-child(6) {
  animation-delay: 1.1s;
  opacity: 1;
}
.problem-item:nth-child(7) {
  animation-delay: 1.3s;
  opacity: 1;
}
.problem-item:nth-child(8) {
  animation-delay: 1.5s;
  opacity: 1;
}
.problem-item:nth-child(9) {
  animation-delay: 1.7s;
  opacity: 1;
}
.problem-item:nth-child(10) {
  animation-delay: 1.9s;
  opacity: 1;
}

/* Hover effect */
.problem-item:hover {
  box-shadow: 0 8px 24px rgba(239, 68, 68, 0.3);
  border-left-color: #dc2626;
}
</style>

<style>
.error-text {
  color: #ef4444;
  display: block;
  margin-top: 8px;
  line-height: 1.6;
  /* font-weight: 600;
  animation: fadeIn 0.8s ease forwards, pulseRed 1.5s ease-in-out infinite;
  text-shadow: 0 0 5px rgba(239, 68, 68, 0.7); */
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* @keyframes pulseRed {
  0%, 100% {
    text-shadow: 0 0 5px rgba(239, 68, 68, 0.7);
    color: #ef4444;
  }
  50% {
    text-shadow: 0 0 15px rgba(239, 68, 68, 1);
    color: #b91c1c;
  }
} */

/* Loader styles */
/* Removed page loading overlay styles as pageLoading is removed */

/* External CSS for solution text indentation */
.solution-list {
  list-style: none;
  padding-left: 0;
  margin-left: 0;
}

.solution-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 0.6rem;
}

.solution-number {
  flex: 0 0 2em;
  font-weight: 700;
  color: #145214;
  text-align: right;
  padding-right: 0.5em;
  user-select: none;
}

.solution-text {
  flex: 1;
  font-weight: 400; /* changed to normal weight */
  color: #1b5e20; /* same color as problem title */
  line-height: 1.4;
}
</style>