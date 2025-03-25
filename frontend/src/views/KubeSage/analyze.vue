<template>
  <n-layout>
    <n-layout-header style="padding: 10px; background-color: #f4f4f4; display: flex; justify-content: flex-end; align-items: center;">
      <n-select
        v-model:value="selectedNamespace"
        :options="namespaceOptions"
        style="width: 200px;"
        placeholder="Select a namespace"
        @update:value="fetchNamespaces"
      />
    </n-layout-header>
    <n-layout-content style="padding: 20px;">
      <!-- <h3>k8sGPT Dashboard</h3> -->
      <n-grid x-gap="20" y-gap="20" :cols="2">
        <n-grid-item>
          <n-card title="Pod" size="medium">
            <template #footer>
              <n-button type="primary" @click="goToPods">Analyze Pods</n-button>
            </template>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card title="Deployment" size="medium">
            <template #footer>
              <n-button type="primary" @click="goToDeployments">Analyze Deployments</n-button>
            </template>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card title="Services" size="medium">
            <template #footer>
              <n-button type="primary" @click="goToServices">Analyze Services</n-button>
            </template>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card title="StorageClass" size="medium">
            <template #footer>
              <n-button type="primary" @click="goToStorageClass">Analyze StorageClass</n-button>
            </template>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card title="Secrets" size="medium">
            <template #footer>
              <n-button type="primary" @click="goToSecrets">Analyze Secrets</n-button>
            </template>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card title="Ingress" size="medium">
            <template #footer>
              <n-button type="primary" @click="goToIngress">Analyze Ingress</n-button>
            </template>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card title="PVC" size="medium">
            <template #footer>
              <n-button type="primary" @click="goToPVC">Analyze PVC</n-button>
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
 
const selectedNamespace = ref(''); // Default namespace
const namespaces = ref([]);
const showAnalysisResult = ref(false);
const analysisResult = ref('');
 
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
const baseUrl = 'https://10.0.34.129:8007/kubeconfig';
 
 
// Fetch namespaces from the backend
const fetchNamespaces = async () => {
  try {
    const headers = getAuthHeaders();
    const response = await axios.get(`${baseUrl}/namespaces`, { headers });
    namespaces.value = response.data.namespaces;
 
    // If selectedNamespace is empty or not in the list, set it to default (only once)
    if (!selectedNamespace.value || !namespaces.value.includes(selectedNamespace.value)) {
      selectedNamespace.value = namespaces.value.includes('default') ? 'default' : namespaces.value[0] || '';
    }
  } catch (error) {
    console.error('Error fetching namespaces:', error);
  }
};
 
 
// Analyze a Kubernetes resource
// const analyzeK8sResource = async (resourceType) => {
//   // if (!selectedNamespace.value) {
//   //   alert('Please select a namespace first.');
//   //   return;
//   // }
 
//   try {
//     const headers = getAuthHeaders();
//     const requestBody = {
//       anonymize: false,
//       custom_analysis: false,
//       explain: true,
//       filter_analyzers: [resourceType], // Pass the resource type as filter
//       interactive: false,
//       language: 'english',
//       max_concurrency: 10,
//       namespace: selectedNamespace.value, // Pass the selected namespace
//       no_cache: false,
//       output_format: 'json',
//       with_doc: false,
//     };
//     console.log('Request body:', requestBody);
 
//     const response = await axios.post(`${baseUrl}/analyze`, requestBody, { headers });
 
//     if (response.status === 200) {
//       const { status, results } = response.data;
 
//       if (status === "OK" && results === null) {
//         analysisResult.value = `<p style="color: green;">No issues found for ${resourceType} in namespace ${selectedNamespace.value}.</p>`;
//       } else if (status === "ProblemDetected" && results) {
//         let errorMessages = results.map((result, index) => {
//           let errorText = result.error?.map(err => `<span style="color: red;">${err.Text}</span>`).join('<br>') || 'No error details available';
//           let solutionText = result.details?.split('Solution:')[1]?.trim()?.split('\n')?.map((solution, idx) => `<li style="list-style-type: none; color: green;">${solution}</li>`).join('') || 'No solution details available';
 
//           return `
//             <div>
//               <h4><strong>Problem ${index + 1}: ${result.name}</strong></h4>
//               <p><strong>Error:</strong><br> ${errorText}</p>
//               <p><strong>Solution:</strong>
//                 <ol>${solutionText}</ol>
//               </p>
//               <hr>
//             </div>
//           `;
//         }).join('');
 
//         analysisResult.value = `
//           <h3 style="color: red;">Problems Detected (${response.data.problems}):</h3>
//           ${errorMessages}
//         `;
//       } else {
//         analysisResult.value = `<p style="color: orange;">Unknown response status.</p>`;
//       }
 
//       showAnalysisResult.value = true;
//     } else {
//       analysisResult.value = `<p style="color: red;">Something went wrong. Please try again.</p>`;
//       showAnalysisResult.value = true;
//     }
//   } catch (error) {
//     console.error(`Error analyzing ${resourceType}:`, error);
//     analysisResult.value = `<p style="color: red;">Error: ${error.message}</p>`;
//     showAnalysisResult.value = true;
//   }
// };
const analyzeK8sResource = async (resourceType) => {
  if (!selectedNamespace.value) {
    alert("Please select a namespace first.");
    return;
  }
 
  try {
    const headers = getAuthHeaders(); // Get authentication headers
 
    // Define query parameters
    const params = {
      backend: "ollama",
      explain: true,
      filter: resourceType, // Send resource type as filter
      "max-concurrency": 5,
      namespace: selectedNamespace.value, // Namespace from selection
      output: "json"
      // kubeconfig: "uploaded_kubeconfigs/0ea9a8d6-86de-4979-ba6d-f137f096c208.yaml",
    };
 
    console.log("Query Parameters:", params);
 
    // Axios POST request with query parameters
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
/* Add custom styles here */
.n-card {
  margin-bottom: 20px;
}
</style>
 