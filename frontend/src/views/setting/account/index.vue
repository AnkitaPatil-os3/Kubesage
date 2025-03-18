<template>
  <div class="flex flex-wrap gap-4 p-4">
    <!-- Heading: Agents -->
    <n-card class="p-4 w-full md:w-4/4 shadow-md rounded-lg">
      <n-text class="text-lg font-bold">Agents</n-text>

      <!-- Buttons for Linux, Windows, Kubernetes, and other new agents -->
      <div class="flex flex-col gap-6 w-full mt-4">
          <div v-for="(agents, category) in categorizedAgents" :key="category">
            <h2 class="text-lg font-bold mb-2">{{ category }}</h2>
            <div class="flex flex-wrap gap-4">
              <div v-for="(agent, index) in agents" :key="index">
                <n-card class="hover-card w-70" :class="{
                  'selected-card': selectedAgent === agent.name,
                  'activated-card': selectedAgent === agent.name
                }" @click="selectAgent(agent.name)">
                  <div class="d-flex">
                    <img :src="agent.icon" alt="Agent Icon" class="mr-2" style="width: 40px; height: 40px;" />
                    <span class="font-semibold">{{ agent.name }}</span>
                  </div>
                </n-card>
              </div>
            </div>
          </div>
      </div>


      <!-- Agent-specific input form for DB agents (as a pop-up modal) -->
      <div v-if="showForm" class="modal-overlay">
        <div class="modal-container">
          <n-card class="p-4 shadow-md rounded-lg">
            <n-text class="text-lg font-bold">Enter Database Details</n-text>
            <!-- Close button in the top-right corner -->
            <button class="close-modal-btn" @click="closeModal">&#x2716;</button>

            <form >
              <div class="mt-4">
                <div class="mb-4 d-flex">
                  <label for="dbName" class="block text-sm font-medium w-1/3">Database Name</label>
                  <n-input v-model:value="formData.dbName" id="dbName" placeholder="Enter Database Name" required
                    class="w-2/3" />
                </div>
                <div class="mb-4 d-flex">
                  <label for="dbIp" class="block text-sm font-medium w-1/3">DB Server Address</label>
                  <n-input v-model:value="formData.dbIp" id="dbIp" placeholder="Enter Database IP" required
                    class="w-2/3" />
                </div>
                <div class="mb-4 d-flex">
                  <label for="dbPort" class="block text-sm font-medium w-1/3">DB IP Port</label>
                  <n-input v-model:value="formData.dbPort" id="dbPort" placeholder="Enter Database Port" required
                    class="w-2/3" />
                </div>
                <div class="mb-4 d-flex">
                  <label for="dbUsername" class="block text-sm font-medium w-1/3">Username</label>
                  <n-input v-model:value="formData.dbUsername" id="dbUsername" placeholder="Enter Username" required
                    class="w-2/3" />
                </div>
                <div class="mb-4 d-flex">
                  <label for="dbPassword" class="block text-sm font-medium w-1/3">Password</label>
                  <n-input v-model:value="formData.dbPassword" id="dbPassword" placeholder="Enter Password" required
                    type="password" class="w-2/3" />
                </div>
              </div>
              <n-button type="primary" html-type="submit" class="mt-4" @click="generateCommandFromForm()">Generate
                Command</n-button>

            </form>
          </n-card>
        </div>
      </div>

      <!-- Add the Application Java form in the modal -->
<div v-if="isJava" class="modal-overlay">
  <div class="modal-container">
    <n-card class="p-4 shadow-md rounded-lg">
      <n-text class="text-lg font-bold">Enter Java Application Details</n-text>
      <!-- Close button -->
      <button class="close-modal-btn" @click="closeModal">&#x2716;</button>

      <form >
        <div class="mt-4">
          <div class="mb-4 d-flex">
            <label for="appName" class="block text-sm font-medium w-1/3">Application Name</label>
            <n-input v-model:value="formData.appName" id="appName" placeholder="Enter Application Name" required class="w-2/3" />
          </div>
          <div class="mb-4 d-flex">
            <label for="appIp" class="block text-sm font-medium w-1/3">Application IP</label>
            <n-input v-model:value="formData.appIp" id="appIp" placeholder="Enter Application IP" required class="w-2/3" />
          </div>
          <div class="mb-4 d-flex">
            <label for="appPort" class="block text-sm font-medium w-1/3">Application Port</label>
            <n-input v-model:value="formData.appPort" id="appPort" placeholder="Enter Application Port" required class="w-2/3" />
          </div>
        </div>
        <n-button type="primary" html-type="submit" class="mt-4" @click="generateJavaCommand()">Generate Command</n-button>
      </form>
    </n-card>
  </div>
</div>
      <!-- Command Input Box and URL Button -->
      <div v-if="generatedCommand" class="flex mt-6 w-full ">
        <!-- Input Box (textarea-like) -->
        <n-input v-model="generatedCommand"
          class=" dark:text-gray-800 border-gray-400 resize-none  placeholder-gray-800" type="textarea"
          readonly :placeholder="generatedCommand" :style="{ '--n-placeholder-color': '#6b7280', width: '100%', height: '120px' }"  
          @click="copyCommand" />
      </div>

      <!-- Success/Error Message -->
      <!-- <div v-if="commandCopied" class="w-75 mt-4 p-2 text-center text-gray-500 rounded-lg w-200 bg-green-100 text-green-700">
        <span>Command copied to clipboard!</span>
        <span class="ml-2 text-xl">&#x2714;</span>
      </div> -->
    </n-card>

    <!-- Agent Details Card -->
    <n-card class="p-4 w-full md:w-4/4 shadow-md rounded-lg mt-6">
      <n-text class="text-lg font-bold">Agent Details</n-text>
      <div class="mt-4">
        <table class="w-full table-auto border-collapse">
          <thead>
            <tr>
              <th class="border p-2">Host Name</th>
              <th class="border p-2">IP Address</th>
              <th class="border p-2">Agent Name</th>
              <th class="border p-2">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(agent, index) in agentDetails" :key="index">
              <td class="border p-2">{{ agent.host_name }}</td>
              <td class="border p-2">{{ agent.ip_port }}</td>
              <td class="border p-2">{{ agent.agent_name }}</td>
              <td class="border p-2">{{ agent.status }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </n-card>
  </div>
</template>


<script setup>
import { ref, onMounted } from "vue";
import { NCard, NButton, NText, NInput } from 'naive-ui';
import axios from "axios";
import { useMessage } from 'naive-ui';
import { useAuthStore } from '@/store';

// Retrieve userInfo from localStorage
const userInfo = JSON.parse(localStorage.getItem('keycloakId'));
const keycloakId = userInfo.value; // If userInfo exists, use the id (keycloak_id)
const message = useMessage();

console.log('Keycloak ID:', keycloakId);

// List of available agents with their corresponding FontAwesome icons
const categorizedAgents = {
  "Operating Systems": [
    { name: "Linux", icon: "https://img.icons8.com/color/48/linux--v1.png" },
    { name: "Windows", icon: "https://img.icons8.com/color/48/windows-10.png" }
  ],
  "Containers & Orchestration": [
    { name: "Kubernetes", icon: "https://img.icons8.com/color/48/kubernetes.png" },
    { name: "Docker", icon: "https://img.icons8.com/fluency/48/docker.png" }
  ],
  "Databases": [
    { name: "PostgreSQL", icon: "https://img.icons8.com/color/48/postgreesql.png" },
    { name: "MySQL", icon: "https://img.icons8.com/fluency/48/mysql-logo.png" },
    { name: "Microsoft SQL Server", icon: "https://img.icons8.com/color/48/microsoft-sql-server.png" },
    { name: "Oracle DB", icon: "https://img.icons8.com/color/48/oracle-logo.png" },
    { name: "MongoDB", icon: "https://img.icons8.com/color/48/mongodb.png" }
  ],
  "Applications": [
    { name: "Application - Java", icon: "https://img.icons8.com/fluency/48/java-coffee-cup-logo.png" }
  ]
};

const kubeSageIp = import.meta.env.VITE_kubeSage_IP;
const lgtmIp = import.meta.env.VITE_LGTM_IP;
const agentIp = import.meta.env.VITE_AGENT_IP;

// Reactive variables
const selectedAgent = ref('');
const showForm = ref(false);
const isJava = ref(false);
const commandCopied = ref(false);
const agentDetails = ref([]);
const generatedCommand = ref('');
const formData = ref({
  dbName: '',
  dbIp: '',
  dbPort: '',
  dbUsername: '',
  dbPassword: ''
});

// Predefined commands for non-DB agents
const predefinedCommands = {
  Linux: `curl -o kubeSage-agent_linux-v3.sh http://${agentIp}/kubeSage-agent_linux-v3.sh && kubeSage_UID=${keycloakId} METRIC_SRV="http://${lgtmIp}:9090/api/v1/write" LOGS_SRV="http://${lgtmIp}:3100/loki/api/v1/push" kubeSage_BACK_SRV="https://${kubeSageIp}:8000/api/v1/agents/" bash ./kubeSage-agent_linux-v3.sh`,

  Windows: `curl -o "$env:USERPROFILE/Downloads/kubeSage-agent_windows-v2.ps1" http://${agentIp}/kubeSage-agent_windows-v2.ps1; if (Test-Path "$env:USERPROFILE/Downloads/kubeSage-agent_windows-v2.ps1") { & "$env:USERPROFILE/Downloads/kubeSage-agent_windows-v2.ps1" -KeycloakId "${keycloakId}" -AgentName "Windows" -IPAddress "${kubeSageIp}" -prometheus "${lgtmIp}" -loki "${lgtmIp}" } else { Write-Host "Failed to download kubeSage-agent_windows-v2.ps1." }`,

  Kubernetes: `helm repo add kubeSage-stable http://${agentIp}/kubeSage-k8s-monitoring/ && helm repo update && helm install kubeSage-k8s-monitoring --namespace kubeSage-monitoring --create-namespace --set agentDeployment.kubeSageUid="${keycloakId}" --set cluster.name="MyCluster" --set agentDeployment.agentName="Kubernetes" --set agentDeployment.apiEndpoint="https://${kubeSageIp}/api/v1/agents/" --set externalServices.prometheus.host="http://${lgtmIp}:9090" --set externalServices.loki.host="http://${lgtmIp}:3100" --set externalServices.tempo.host="http://${lgtmIp}:3200" kubeSage-stable/kubeSage-k8s-monitoring`,

  Docker: `curl -o kubeSage-agent_docker-v1.sh http://${agentIp}/kubeSage-agent_docker-v1.sh && kubeSage_UID=${keycloakId} kubeSage_BACK_SRV="https://${kubeSageIp}:8000/api/v1/agents/"   METRIC_SRV="http://${lgtmIp}:9090/api/v1/write" LOGS_SRV="http://${lgtmIp}:3100/loki/api/v1/push" bash ./kubeSage-agent_docker-v1.sh`
};

// Select an agent and show the form if it's a DB agent, otherwise generate the command directly for non-DB agents
const selectAgent = (agentName) => {
  selectedAgent.value = agentName;
  console.log("Selected Agent:", agentName);

  const dbAgents = ['PostgreSQL', 'MySQL', 'Microsoft SQL Server', 'Oracle DB', 'MongoDB'];
  const osAgents = ['Linux', 'Windows', 'Kubernetes', 'Docker'];

  // Handle showForm visibility for databases
  if (dbAgents.includes(agentName)) {
    showForm.value = true;
  } else {
    showForm.value = false;
  }

  // Handle OS-based command generation
  if (osAgents.includes(agentName)) {
    generatedCommand.value = predefinedCommands[agentName];
    isJava.value = false; // Assume OS agents are not Java-based
  } 
  // Handle Java-based condition
  else if (agentName.includes('Java') || agentName === 'JVM' || agentName === 'Spring Boot') {
    isJava.value = true;
    generatedCommand.value = ''; // No predefined command for Java
  } 
  // Default case for other agents
  else {
    isJava.value = false;
    generatedCommand.value = '';
  }

  // console.log("showForm:", showForm.value);
  // console.log("isJava:", isJava.value);
  // console.log("generatedCommand:", generatedCommand.value);
};


// Generate the command based on the form data for DB agents
const generateCommandFromForm = () => {
  const { dbName, dbIp, dbPort, dbUsername, dbPassword, appName, appIp, appPort } = formData.value;

  const kubeSageBackSrv = `https://${kubeSageIp}:8000/api/v1/agents/`;
  const metricSrv = `http://${lgtmIp}:9090/api/v1/write`;
  const logsSrv = `http://${lgtmIp}:3100/loki/api/v1/push`;
  const traceSrv = `http://${lgtmIp}:4317`;

  // Handle Database Agents
  if (selectedAgent.value === 'PostgreSQL') {
    generatedCommand.value = `curl -o kubeSage-agent_postgresql-v1.sh http://${agentIp}/kubeSage-agent_postgresql-v1.sh && \
kubeSage_UID=${keycloakId} \
kubeSage_BACK_SRV="${kubeSageBackSrv}" \
METRIC_SRV="${metricSrv}" \
LOGS_SRV="${logsSrv}" \
PSQL_USERNAME="${dbUsername}" \
PSQL_PASSWORD="${dbPassword}" \
PSQL_DB_NAME="${dbName}" \
PSQL_IP="${dbIp}" \
PSQL_PORT="${dbPort}" \
bash ./kubeSage-agent_postgresql-v1.sh`;
  } else if (selectedAgent.value === 'MySQL') {
    generatedCommand.value = `curl -o kubeSage-agent_mysql-v1.sh http://${agentIp}/kubeSage-agent_mysql-v1.sh && \
kubeSage_UID=${keycloakId} \
kubeSage_BACK_SRV="${kubeSageBackSrv}" \
METRIC_SRV="${metricSrv}" \
LOGS_SRV="${logsSrv}" \
MY_SQL_USERNAME="${dbUsername}" \
MY_SQL_PASSWORD="${dbPassword}" \
MY_SQL_DB_NAME="${dbName}" \
MY_SQL_IP="${dbIp}" \
MY_SQL_PORT="${dbPort}" \
bash ./kubeSage-agent_mysql-v1.sh`;
  } else if (selectedAgent.value === 'Microsoft SQL Server') {
    generatedCommand.value = `curl -o kubeSage-agent_ms-sql-v1.sh http://${agentIp}/kubeSage-agent_ms-sql-v1.sh && \
kubeSage_UID=${keycloakId} \
kubeSage_BACK_SRV="${kubeSageBackSrv}" \
METRIC_SRV="${metricSrv}" \
LOGS_SRV="${logsSrv}" \
MS_SQL_USERNAME="${dbUsername}" \
MS_SQL_PASSWORD="${dbPassword}" \
MS_SQL_DB_NAME="${dbName}" \
MS_SQL_IP="${dbIp}" \
MS_SQL_PORT="${dbPort}" \
bash ./kubeSage-agent_ms-sql-v1.sh`;
  } else if (selectedAgent.value === 'Oracle DB') {
    generatedCommand.value = `curl -o kubeSage-agent_oracle_db-v1.sh http://${agentIp}/kubeSage-agent_oracle_db-v1.sh && \
kubeSage_UID=${keycloakId} \
kubeSage_BACK_SRV="${kubeSageBackSrv}" \
METRIC_SRV="${metricSrv}" \
LOGS_SRV="${logsSrv}" \
ORACLE_DB_USERNAME="${dbUsername}" \
ORACLE_DB_PASSWORD="${dbPassword}" \
ORACLE_DB_NAME="${dbName}" \
ORACLE_DB_IP="${dbIp}" \
ORACLE_DB_PORT="${dbPort}" \
bash ./kubeSage-agent_oracle_db-v1.sh`;
  } else if (selectedAgent.value === 'MongoDB') {
    generatedCommand.value = `curl -o kubeSage-agent_mongo_db-v1.sh http://${agentIp}/kubeSage-agent_mongo_db-v1.sh && \
kubeSage_UID=${keycloakId} \
kubeSage_BACK_SRV="${kubeSageBackSrv}" \
METRIC_SRV="${metricSrv}" \
LOGS_SRV="${logsSrv}" \
MON_SQL_USERNAME="${dbUsername}" \
MON_SQL_PASSWORD="${dbPassword}" \
MON_SQL_DB_NAME="${dbName}" \
MON_SQL_IP="${dbIp}" \
MON_SQL_PORT="${dbPort}" \
bash ./kubeSage-agent_mongo_db-v1.sh`;
  }

  // Handle Java Application Agent
  if (selectedAgent.value === 'Application - Java') {
    generatedCommand.value = `curl -o kubeSage-agent_app-java-v1.sh http://${agentIp}/kubeSage-agent_app-java-v1.sh && \
kubeSage_UID=${keycloakId} \
METRIC_SRV="${metricSrv}" \
kubeSage_BACK_SRV="${kubeSageBackSrv}" \
LOGS_SRV="${logsSrv}" \
TRACE_SRV="${traceSrv}" \
APP_NAME="${appName}" \
APP_IP="${appIp}" \
APP_PORT="${appPort}" \
bash ./kubeSage-agent_app-java-v1.sh`;
  }

  showForm.value = false;
};

// Generate the command based on the form data for Java application agent
const generateJavaCommand = () => {
  const { appName, appIp, appPort } = formData.value;

  const kubeSageBackSrv = `https://${kubeSageIp}:8000/api/v1/agents/`;
  const metricSrv = `http://${lgtmIp}:9090/api/v1/write`;
  const logsSrv = `http://${lgtmIp}:3100/loki/api/v1/push`;
  const traceSrv = `http://${lgtmIp}:4317`;

  // Handle Java Application Agent
  if (selectedAgent.value === 'Application - Java') {
    generatedCommand.value = `curl -o kubeSage-agent_app-java-v1.sh http://${agentIp}/kubeSage-agent_app-java-v1.sh && \
kubeSage_UID=${keycloakId} \
METRIC_SRV="${metricSrv}" \
kubeSage_BACK_SRV="${kubeSageBackSrv}" \
LOGS_SRV="${logsSrv}" \
TRACE_SRV="${traceSrv}" \
APP_NAME="${appName}" \
APP_IP="${appIp}" \
APP_PORT="${appPort}" \
bash ./kubeSage-agent_app-java-v1.sh`;
  }

  isJava.value = false; // Close the modal after generating the command
};


// Copy the generated command to clipboard
const copyCommand = () => {
  const commandText = generatedCommand.value;
  if (!commandText) return;

  navigator.clipboard.writeText(commandText).then(() => {
    commandCopied.value = true;
    message.success('Command copied to clipboard!'); 
    // Update the form fields to dynamically reflect in the command
    setTimeout(() => {
      commandCopied.value = false;
    }, 3000);
  }).catch((error) => {
    message.error('Failed to copy command.');
    console.error('Error copying command:', error);
  });
};

// Close the form modal
const closeModal = () => {
  showForm.value = false;
  isJava.value = false;
};

// Fetch agent details from the API on component mount
const fetchAgentDetails = async () => {
  try {
    const response = await axios.get(`/api/v1/agents/`);
    agentDetails.value = response.data;
  } catch (error) {
    console.error("Error fetching agent details:", error);
  }
};

// Fetch the agent details when the component is mounted
onMounted(fetchAgentDetails);
</script>

<style scoped>
/* Custom styling for the modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 999;
}

.modal-container {
  background: white;
  padding: 20px;
  border-radius: 8px;
  width: 80%;
  max-width: 600px;
}

.d-flex {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.selected-card {
  border: 1px solid black;
  background-color: lightgray;
}

.activated-card {
  background-color: lightgray !important;
}

.hover-card {
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
  width: 5 00px;
}

.hover-card:hover {
  transform: translateY(-10px);
  box-shadow: 0 8px 15px rgba(0, 0, 0, 0.3);
  cursor: pointer;
}

.table-auto {
  width: 100%;
  border-collapse: collapse;
}

.table-auto th,
.table-auto td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}

.n-input textarea::placeholder {
  color: black;
}



.close-modal-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  background: none;
  border: none;
  font-size: 24px;
  color: #333;
  cursor: pointer;
}
</style>
