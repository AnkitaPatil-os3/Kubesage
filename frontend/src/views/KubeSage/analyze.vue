<template>
  <n-layout>
    <n-layout-header style="padding: 10px; background-color: #f4f4f4; display: flex; justify-content: space-between; align-items: center;">
      <h2 class="header-title">Analyze Resources</h2>
      <n-select
        v-model:value="selectedNamespace"
        :options="namespaceOptions"
        style="width: 200px;"
        placeholder="Select a namespace"
        @update:value="fetchNamespaces"
      />
    </n-layout-header>
    <n-layout-content style="padding: 20px;">
      <n-grid x-gap="20" y-gap="20" :cols="2">
        <n-grid-item v-for="resource in resources" :key="resource.type">
          <n-card :title="resource.title" size="medium" class="card-transition">
            <template #footer>
              <n-button type="primary" :loading="loadingResource === resource.type" @click="resource.action">
                Analyze {{ resource.title }}
              </n-button>
            </template>
          </n-card>
        </n-grid-item>
      </n-grid>
      <n-modal
        v-model:show="showAnalysisResult"
        :mask-closable="false"
        preset="dialog"
        title="Analysis Result"
        style="width: 800px;"
      >
        <n-card
          style="max-height: 70vh; overflow-y: auto;"
          :bordered="false"
          size="small"
        >
          <div v-html="analysisResult"></div>
          <template #footer>
            <div style="text-align: right;">
              <n-button @click="closeAnalysisResult">Close</n-button>
            </div>
          </template>
        </n-card>
      </n-modal>
    </n-layout-content>
  </n-layout>
</template>
 
<script setup>
import { ref, onMounted, computed } from 'vue';
import axios from 'axios';
import {
  NCard,
  NButton,
  NSelect,
  NGrid,
  NGridItem,
  NLayout,
  NLayoutHeader,
  NLayoutContent,
  NModal,
} from 'naive-ui';
 
const selectedNamespace = ref('');
const namespaces = ref([]);
const showAnalysisResult = ref(false);
const analysisResult = ref('');
const loadingResource = ref(null);
 
const getAuthHeaders = () => {
  try {
    const token = JSON.parse(localStorage.getItem('accessToken')).value;
    return { Authorization: `Bearer ${token}` };
  } catch (error) {
    console.error('Authentication error. Please login again.');
    return {};
  }
};
 
const baseUrl = 'https://10.0.34.77:8002/kubeconfig';
 
const fetchNamespaces = async () => {
  try {
    const headers = getAuthHeaders();
    const response = await axios.get(`${baseUrl}/namespaces`, { headers });
    namespaces.value = response.data.namespaces;
 
    if (!selectedNamespace.value || !namespaces.value.includes(selectedNamespace.value)) {
      selectedNamespace.value = namespaces.value.includes('default') ? 'default' : namespaces.value[0] || '';
    }
  } catch (error) {
    console.error('Error fetching namespaces:', error);
  }
};
 
const analyzeK8sResource = async (resourceType) => {
  if (!selectedNamespace.value) {
    alert("Please select a namespace first.");
    return;
  }
 
  loadingResource.value = resourceType;
 
  try {
    const headers = getAuthHeaders();
    const params = {
      backend: "ollama",
      explain: true,
      filter: resourceType,
      "max-concurrency": 5,
      namespace: selectedNamespace.value,
      output: "json"
    };
 
    const response = await axios.post(`${baseUrl}/analyze`, null, { headers, params });
 
    if (response.status === 200) {
      const { status, results } = response.data;
 
      if (status === "OK" && results === null) {
        analysisResult.value = `<p style="color: green;">No issues found for ${resourceType} in namespace ${selectedNamespace.value}.</p>`;
      } else if (status === "ProblemDetected" && results) {
        let errorMessages = results.map((result, index) => {
          let errorText =
            result.error?.map((err) => `<span style="color: red;">${err.Text}</span>`).join("<br>") ||
            "No error details available";
          let solutionText =
            result.details
              ?.split("Solution:")[1]
              ?.trim()
              ?.split("\n")
              ?.map((solution, idx) => `<li style="list-style-type: none; color: green;">${solution}</li>`)
              .join("") || "No solution details available";
 
          return `
            <div>
              <h4><strong>Problem ${index + 1}: ${result.name}</strong></h4>
              <p><strong>Error:</strong><br> ${errorText}</p>
              <p><strong>Solution:</strong>
                <ol>${solutionText}</ol>
              </p>
              <hr>
            </div>
          `;
        }).join("");
 
        analysisResult.value = `
          <h3 style="color: red;">Problems Detected (${response.data.problems}):</h3>
          ${errorMessages}
        `;
      } else {
        analysisResult.value = `<p style="color: orange;">Unknown response status.</p>`;
      }
 
      showAnalysisResult.value = true;
    } else {
      analysisResult.value = `<p style="color: red;">Something went wrong. Please try again.</p>`;
      showAnalysisResult.value = true;
    }
  } catch (error) {
    console.error(`Error analyzing ${resourceType}:`, error);
    analysisResult.value = `<p style="color: red;">Error: ${error.message}</p>`;
    showAnalysisResult.value = true;
  } finally {
    loadingResource.value = null;
  }
};
 
const resources = [
  { type: 'Pod', title: 'Pods', action: () => analyzeK8sResource('Pod') },
  { type: 'Deployment', title: 'Deployments', action: () => analyzeK8sResource('Deployment') },
  { type: 'Service', title: 'Services', action: () => analyzeK8sResource('Service') },
  { type: 'StorageClass', title: 'StorageClass', action: () => analyzeK8sResource('StorageClass') },
  { type: 'Secret', title: 'Secrets', action: () => analyzeK8sResource('Secret') },
  { type: 'Ingress', title: 'Ingress', action: () => analyzeK8sResource('Ingress') },
  { type: 'PersistentVolumeClaim', title: 'PVC', action: () => analyzeK8sResource('PersistentVolumeClaim') },
];
 
const closeAnalysisResult = () => {
  showAnalysisResult.value = false;
};
 
onMounted(() => {
  fetchNamespaces();
});
 
const namespaceOptions = computed(() => {
  return namespaces.value.map(namespace => ({
    label: namespace,
    value: namespace,
  }));
});
</script>
 
<style scoped>
.header-title {
  font-size: 24px;
  font-weight: bold;
}
 
.n-card {
  margin-bottom: 20px;
  transition: transform 0.3s ease, background-color 0.3s ease;
  background-color: #ffffff;
}
 
.n-card-n:hover {
  transform: scale(1.05);
  background-color: #f6fafdf5; /* Light blue background on hover */
}
</style>
 