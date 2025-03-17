<template>
  <div class="flex flex-wrap gap-4 p-4">
    <n-card class="p-4 w-full md:w-4/4 shadow-md rounded-lg">
      <n-text class="text-lg font-bold">Databases Dashboards </n-text>
      <div class="flex flex-col gap-6 w-full mt-4">
        <div v-for="(agents, category) in categorizedAgents" :key="category">
          <div class="flex flex-wrap gap-4">
            <div v-for="(agent, index) in agents" :key="index">
              <n-card class="hover-card w-70" :class="{ 'selected-card': selectedAgent === agent.name }"
                @click="fetchAgentDetails(agent.name)">
                <div class="d-flex">
                  <img :src="agent.icon" alt="Agent Icon" class="mr-2" style="width: 40px; height: 40px;" />
                  <span class="font-semibold">{{ agent.name }}</span>
                </div>
              </n-card>
            </div>
          </div>
        </div>
      </div>
    </n-card>

    <n-card class="p-4 w-full md:w-4/4 shadow-md rounded-lg mt-6">
      <n-text class="text-lg font-bold">Database Instances - {{ selectedAgent }}</n-text>
      <div class="mt-4">
        <table class="w-full table-auto border-collapse">
          <thead>
            <tr>
              <th class="border p-2 bg-gray-200">Instance</th>
              <th class="border p-2 bg-gray-200">Dashboard</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="agentDetails.length === 0">
              <td class="border p-2 text-center" colspan="2">No agent onboard yet</td>
            </tr>
            <tr v-for="(agent, index) in agentDetails" :key="index">
              <td class="border p-2">{{ agent.instance }}</td>
              <td class="border p-2 text-center">
                <a href="#" @click.prevent="getDashboardUrl(selectedAgent, agent.instance)"
                  class="text-blue-600 hover:underline cursor-pointer">
                  View Dashboard
                </a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </n-card>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useMessage } from 'naive-ui';
import { useRouter } from 'vue-router';
import axios from 'axios';

const router = useRouter();
const message = useMessage();
const selectedAgent = ref('');
const agentDetails = ref([]);

const dashboardPaths = {
  "PostgreSQL": "/databases/postgres",
  "MySQL": "/databases/mysql",
  "Microsoft SQL Server": "/databases/mssql",
  "Oracle DB": "/databases/oracledb",
  "MongoDB": "/databases/mongodb"
};

const getDashboardUrl = (agentName, instanceName) => {
  const path = dashboardPaths[agentName];
  if (!path) {
    message.warning("No dashboard available for this database.");
    return;
  }
  router.push({ path, query: { instance: instanceName } });
};

const categorizedAgents = {
  "Databases": [
    { name: "PostgreSQL", icon: "https://img.icons8.com/color/48/postgreesql.png" },
    { name: "MySQL", icon: "https://img.icons8.com/fluency/48/mysql-logo.png" },
    { name: "Microsoft SQL Server", icon: "https://img.icons8.com/color/48/microsoft-sql-server.png" },
    { name: "Oracle DB", icon: "https://img.icons8.com/color/48/oracle-logo.png" },
    { name: "MongoDB", icon: "https://img.icons8.com/color/48/mongodb.png" }
  ]
};

const fetchAgentDetails = async (agentName) => {
  selectedAgent.value = agentName;
  agentDetails.value = []; // Clear existing data before fetching

  let mockData = [];

  try {
    if (agentName === "PostgreSQL") {
      const response = await axios.get(
        "https://10.0.34.212:9090/api/v1/query?query=count(pg_up)by(instance)"
      );

      if (response.data.status === "success" && response.data.data.result.length > 0) {
        mockData = response.data.data.result.map((item) => ({
          instance: `postgresql://${item.metric.instance}`,
        }));
      }
    } else if (agentName === "MySQL") {
      mockData = [
        { instance: 'mysql://10.0.34.221:3306/' },
        { instance: 'mysql://10.0.34.223:3306/' }
      ];
    } else if (agentName === "Microsoft SQL Server") {
      mockData = [
        { instance: 'mssql://10.0.34.224:1433/' },
        { instance: 'mssql://10.0.34.225:1433/' }
      ];
    } else if (agentName === "Oracle DB") {
      mockData = [
        { instance: 'oracle://10.0.34.226:1521/' },
        { instance: 'oracle://10.0.34.227:1521/' }
      ];
    } else if (agentName === "MongoDB") {
      mockData = [
        { instance: 'mongodb://10.0.34.228:27017/' },
        { instance: 'mongodb://10.0.34.229:27017/' }
      ];
    }

    agentDetails.value = mockData;
  } catch (error) {
    console.error("Error fetching agent details:", error);
    message.error("Failed to fetch agent details");
  }
};
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

.selected-card {
  border: 2px solid #3b82f6;
  background-color: #e0f2fe;
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
