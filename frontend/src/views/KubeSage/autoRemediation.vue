<template>
  <div class="bg-gray-50 dark:bg-gray-900 min-h-screen bg-gradient-to-br from-gray-50 to-green-50 dark:from-gray-900 dark:to-green-900/20">
    <div class="p-5">
      <!-- Header -->
      <div class="flex justify-between items-center p-4 bg-white dark:bg-gray-800 rounded-xl shadow-md border-l-4 border-[#10BC3B] mb-6">
        <h2 class="text-xl font-semibold text-[#10BC3B]">KubeSage Auto Remediation</h2>
        <div class="flex items-center gap-4">
          <!-- <select
            v-model="statusFilter"
            class="px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-[#10BC3B] focus:border-transparent"
            @change="fetchRemediations"
          >
            <option value="">All Statuses</option>
            <option value="SUCCESS">Success</option>
            <option value="FAILURE">Failure</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="ANALYZING">Analyzing</option>
            <option value="REASONING">Reasoning</option>
            <option value="ENFORCING">Enforcing</option>
          </select> -->
         
        </div>
      </div>

      <!-- Main Content Area -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        <!-- Vertical Stepper -->
<div class="lg:col-span-1">
<div class="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 border-b-3 border-[#10BC3B] bg-gradient-to-br from-white to-green-50 dark:from-gray-800 dark:to-green-900/10 h-full relative">
  <h3 class="text-lg font-semibold text-gray-800 dark:text-white mb-6">Remediation Process</h3>
  
   <!-- Stepper -->
   <div class="relative h-full">
    <!-- Vertical line that runs through all steps and extends to full height -->
    <div class="absolute left-5 top-0 bottom-0 w-0.5 bg-gray-200 dark:bg-gray-700 h-[calc(100%-2rem)]"></div>
    
    <!-- Step 1: Analyzer -->
    <div class="flex mb-24 relative">
      <div class="flex flex-col items-center mr-4">
        <div
          class="w-10 h-10 rounded-full flex items-center justify-center z-10 shadow-md"
          :class="[
            currentStep >= 1
              ? 'bg-[#10BC3B] text-white shadow-green-200 dark:shadow-green-900/30'
              : 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
          ]"
          @click="filterLogsByStep('ANALYZING')"
        >
          <i class="fas fa-search"></i>
        </div>
      </div>
      <div class="flex-1">
        <h4
          class="text-base font-medium mb-1 cursor-pointer hover:text-[#10BC3B] transition-colors"
          :class="[
            currentStep >= 1
              ? 'text-gray-800 dark:text-white'
              : 'text-gray-500 dark:text-gray-400'
          ]"
          @click="filterLogsByStep('ANALYZING')"
        >
          Analyzer
        </h4>
        <p class="text-sm text-gray-500 dark:text-gray-400">Scanning resources for issues</p>
      </div>
    </div>

    <!-- Step 2: Reasoner -->
    <div class="flex mb-24 relative">
      <div class="flex flex-col items-center mr-4">
        <div
          class="w-10 h-10 rounded-full flex items-center justify-center z-10 shadow-md"
          :class="[
            currentStep >= 2
              ? 'bg-[#10BC3B] text-white shadow-green-200 dark:shadow-green-900/30'
              : 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
          ]"
          @click="filterLogsByStep('REASONING')"
        >
          <i class="fas fa-brain"></i>
        </div>
      </div>
      <div class="flex-1">
        <h4
          class="text-base font-medium mb-1 cursor-pointer hover:text-[#10BC3B] transition-colors"
          :class="[
            currentStep >= 2
              ? 'text-gray-800 dark:text-white'
              : 'text-gray-500 dark:text-gray-400'
          ]"
          @click="filterLogsByStep('REASONING')"
        >
          Reasoner
        </h4>
        <p class="text-sm text-gray-500 dark:text-gray-400">Determining optimal solutions</p>
      </div>
    </div>

    <!-- Step 3: Enforcer -->
    <div class="flex mb-24 relative">
      <div class="flex flex-col items-center mr-4">
        <div
          class="w-10 h-10 rounded-full flex items-center justify-center z-10 shadow-md"
          :class="[
            currentStep >= 3
              ? 'bg-[#10BC3B] text-white shadow-green-200 dark:shadow-green-900/30'
              : 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
          ]"
          @click="filterLogsByStep('ENFORCING')"
        >
          <i class="fas fa-shield-alt"></i>
        </div>
      </div>
      <div class="flex-1">
        <h4
          class="text-base font-medium mb-1 cursor-pointer hover:text-[#10BC3B] transition-colors"
          :class="[
            currentStep >= 3
              ? 'text-gray-800 dark:text-white'
              : 'text-gray-500 dark:text-gray-400'
          ]"
          @click="filterLogsByStep('ENFORCING')"
        >
          Enforcer
        </h4>
        <p class="text-sm text-gray-500 dark:text-gray-400">Preparing remediation actions</p>
      </div>
    </div>

    <!-- Step 4: Executor -->
    <div class="flex relative">
      <div class="flex flex-col items-center mr-4">
        <div
          class="w-10 h-10 rounded-full flex items-center justify-center z-10 shadow-md"
          :class="[
            currentStep >= 4
              ? 'bg-[#10BC3B] text-white shadow-green-200 dark:shadow-green-900/30'
              : 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
          ]"
          @click="filterLogsByStep('EXECUTING')"
        >
          <i class="fas fa-play"></i>
        </div>
      </div>
      <div class="flex-1">
        <h4
          class="text-base font-medium mb-1 cursor-pointer hover:text-[#10BC3B] transition-colors"
          :class="[
            currentStep >= 4
              ? 'text-gray-800 dark:text-white'
              : 'text-gray-500 dark:text-gray-400'
          ]"
          @click="filterLogsByStep('EXECUTING')"
        >
          Executor
        </h4>
        <p class="text-sm text-gray-500 dark:text-gray-400">Applying changes to cluster</p>
      </div>
    </div>
  </div>
</div>
</div>


        <!-- Logs Container -->
        <div class="lg:col-span-2">
          <div class="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 border-b-3 border-[#10BC3B] bg-gradient-to-br from-white to-green-50 dark:from-gray-800 dark:to-green-900/10">
            <div class="flex justify-between items-center mb-6">
              <h3 class="text-lg font-semibold text-gray-800 dark:text-white">
                {{ getStepTitle() }} Logs
              </h3>
              <div class="flex items-center gap-2">
                <span class="text-sm text-gray-500 dark:text-gray-400">
                  {{ filteredLogs.length }} entries
                </span>
                <button
                  @click="clearStepFilter"
                  class="text-sm text-[#10BC3B] hover:underline"
                  v-if="stepFilter"
                >
                  Clear filter
                </button>
              </div>
            </div>

            <!-- Loading State -->
            <div v-if="loading" class="flex flex-col items-center justify-center py-12">
              <div class="w-12 h-12 border-4 border-gray-200 dark:border-gray-700 border-t-[#10BC3B] rounded-full animate-spin mb-4"></div>
              <p class="text-gray-500 dark:text-gray-400">Loading remediation logs...</p>
            </div>

            <!-- Empty State -->
            <div v-else-if="filteredLogs.length === 0" class="flex flex-col items-center justify-center py-12">
              <div class="w-16 h-16 flex items-center justify-center text-gray-400 dark:text-gray-600 mb-4">
                <i class="fas fa-clipboard-list text-3xl"></i>
              </div>
              <p class="text-gray-500 dark:text-gray-400 mb-2">No remediation logs found</p>
              <p class="text-sm text-gray-400 dark:text-gray-500">Auto remediation events will appear here when they occur</p>
            </div>

            <!-- Logs List -->
            <div v-else class="space-y-4 max-h-[600px] overflow-y-auto pr-2">
              <div
                v-for="(log, index) in filteredLogs"
                :key="index"
                class="p-4 rounded-lg border border-gray-100 dark:border-gray-700 hover:shadow-md transition-shadow duration-200"
                :class="getLogBackgroundClass(log.event_type)"
              >
                <div class="flex items-start gap-3">
                  <div
                    class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1"
                    :class="getEventIconClass(log.event_type)"
                  >
                    <i :class="getEventIcon(log.event_type)"></i>
                  </div>
                  <div class="flex-1">
                    <div class="flex justify-between items-start mb-1">
                      <h4 class="font-medium text-gray-800 dark:text-white">
                        {{ formatEventType(log.event_type) }}
                      </h4>
                      <span class="text-xs text-gray-500 dark:text-gray-400">
                        {{ formatTime(log.timestamp) }}
                      </span>
                    </div>
                    <p class="text-gray-600 dark:text-gray-300 mb-2">{{ log.message }}</p>
                    
                    <!-- Log Details (if any) -->
                    <div
                      v-if="log.details && hasDetails(log.details)"
                      class="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700"
                    >
                      <div class="grid grid-cols-1 gap-2">
                        <div
                          v-for="(value, key) in log.details"
                          :key="key"
                          class="flex flex-col sm:flex-row sm:items-start "
                        >
                          <div class="text-sm font-medium text-gray-500 dark:text-gray-400 ">
                            {{ formatDetailKey(key) }}:
                          </div>
                          <div class="text-sm text-gray-700 dark:text-gray-300 sm:w-2/3 group ml-5 relative">
                            <div v-if="typeof value === 'object'">
                              <pre class="text-sm font-medium text-gray-500 dark:text-gray-400 sm:w-1/3">Status:{{ value[0].status}}</pre>
                              <pre class="text-sm font-medium text-gray-500 dark:text-gray-400 w-full  ">Message:{{ value[0].message}}</pre>
                              
                            </div>
                            
                            <div v-else-if="key.includes('command') || key.includes('patch')" class="relative">
                              <pre class="bg-gray-50 dark:bg-gray-900 p-2 rounded text-xs overflow-x-auto">{{ value }}</pre>
                              <button
                                @click="copyToClipboard(value)"
                                class="absolute top-2 right-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 opacity-0 group-hover:opacity-100 transition-opacity"
                                title="Copy to clipboard"
                              >
                                <i class="far fa-copy"></i>
                              </button>
                            </div>
                            <div v-else>
                              {{ value }}
                            </div>
                          </div>
                        </div>
                        

                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

         <!-- Remediations List -->
<div class="mt-6 bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 border-b-3 border-[#10BC3B] bg-gradient-to-br from-white to-green-50 dark:from-gray-800 dark:to-green-900/10">
<div class="flex justify-between items-center mb-6">
  <h3 class="text-lg font-semibold text-gray-800 dark:text-white">Recent Remediations</h3>
  <div class="text-sm text-gray-500 dark:text-gray-400">
    Showing {{ paginatedRemediations.length ? (currentPage - 1) * pageSize + 1 : 0 }} - {{ Math.min(currentPage * pageSize, remediations.length) }} of {{ remediations.length }}
  </div>
</div>

<!-- Loading State -->
<div v-if="loading" class="flex flex-col items-center justify-center py-12">
  <div class="w-12 h-12 border-4 border-gray-200 dark:border-gray-700 border-t-[#10BC3B] rounded-full animate-spin mb-4"></div>
  <p class="text-gray-500 dark:text-gray-400">Loading remediation history...</p>
</div>

<!-- Empty State -->
<div v-else-if="remediations.length === 0" class="flex flex-col items-center justify-center py-12">
  <div class="w-16 h-16 flex items-center justify-center text-gray-400 dark:text-gray-600 mb-4">
    <i class="fas fa-history text-3xl"></i>
  </div>
  <p class="text-gray-500 dark:text-gray-400 mb-2">No remediation history found</p>
  <p class="text-sm text-gray-400 dark:text-gray-500">Completed remediations will appear here</p>
</div>

<!-- Remediations Table -->
<div v-else class="overflow-x-auto">
  <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
    <thead class="bg-gray-50 dark:bg-gray-800">
      <tr>
        <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
        <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Resource</th>
        <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Issue</th>
        <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Timestamp</th>
        <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Duration</th>
        <th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Actions</th>
      </tr>
    </thead>
    <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
      <tr v-for="(remediation, index) in paginatedRemediations" :key="index" class="hover:bg-gray-50 dark:hover:bg-gray-700">
        <td class="px-6 py-4 whitespace-nowrap">
          <span
            class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full"
            :class="getStatusClass(remediation.status)"
          >
            {{ remediation.status }}
          </span>
        </td>
        <td class="px-6 py-4 whitespace-nowrap">
          <div class="text-sm text-gray-900 dark:text-gray-100">{{ remediation.resourceType }}/{{ remediation.resourceName }}</div>
          <div class="text-xs text-gray-500 dark:text-gray-400">{{ remediation.namespace }}</div>
        </td>
        <td class="px-6 py-4">
          <div class="text-sm text-gray-900 dark:text-gray-100 max-w-xs truncate">{{ remediation.issue }}</div>
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
          {{ formatDate(remediation.timestamp) }}
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
          {{ remediation.duration || 'N/A' }}
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
          <button
            @click="viewRemediationDetails(remediation)"
            class="text-[#10BC3B] hover:text-[#09a431] dark:hover:text-[#0dd142]"
          >
            View Details
          </button>
        </td>
      </tr>
    </tbody>
  </table>
  
  <!-- Pagination Controls -->
  <div class="flex justify-between items-center mt-6 px-2">
    <button
      @click="prevPage"
      class="px-3 py-1 rounded-md bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
      :disabled="currentPage === 1"
    >
      <i class="fas fa-chevron-left mr-1"></i> Previous
    </button>
    
    <div class="flex items-center space-x-1">
      <button
        v-for="page in totalPages"
        :key="page"
        @click="goToPage(page)"
        class="w-8 h-8 flex items-center justify-center rounded-md text-sm"
        :class="currentPage === page
          ? 'bg-[#10BC3B] text-white'
          : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'"
      >
        {{ page }}
      </button>
    </div>
    
    <button
      @click="nextPage"
      class="px-3 py-1 rounded-md bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
      :disabled="currentPage === totalPages"
    >
      Next <i class="fas fa-chevron-right ml-1"></i>
    </button>
  </div>
</div>
</div>

    
    <!-- Remediation Details Modal -->
    <div
      v-if="showDetailsModal"
      class="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm flex items-center justify-center z-1000 p-4"
      @click.self="showDetailsModal = false"
    >
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        <div class="flex justify-between items-center p-6 border-b border-gray-200 dark:border-gray-700">
          <h3 class="text-xl font-semibold text-gray-800 dark:text-white">Remediation Details</h3>
          <button
            @click="showDetailsModal = false"

            class="text-gray-500 px-1 bg-gray-200 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <i class="fas fa-times"></i>
          </button>
        </div>
        
        <div class="p-6 overflow-y-auto max-h-[calc(90vh-120px)]" v-if="selectedRemediation">
          <!-- Remediation Header -->
          <div class="flex flex-col md:flex-row md:justify-between md:items-center mb-6 gap-4">
            <div>
              <h4 class="text-lg font-medium text-gray-800 dark:text-white mb-1">
                {{ selectedRemediation.resourceType }}/{{ selectedRemediation.resourceName }}
              </h4>
              <p class="text-sm text-gray-500 dark:text-gray-400">
                Namespace: {{ selectedRemediation.namespace }} |
                Started: {{ formatDate(selectedRemediation.timestamp) }}
              </p>
            </div>
            <span
              class="px-3 py-1 inline-flex text-sm leading-5 font-semibold rounded-full self-start"
              :class="getStatusClass(selectedRemediation.status)"
            >
              {{ selectedRemediation.status }}
            </span>
          </div>
          
          <!-- Issue Details -->
          <div class="mb-6 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
            <h5 class="text-base font-medium text-gray-800 dark:text-white mb-2">Issue Details</h5>
            <p class="text-gray-700 dark:text-gray-300">{{ selectedRemediation.issue }}</p>
            <div class="mt-3 flex items-center">
              <span class="text-sm font-medium text-gray-500 dark:text-gray-400 mr-2">Severity:</span>
              <span
                class="px-2 py-0.5 text-xs font-semibold rounded"
                :class="getSeverityClass(selectedRemediation.severity)"
              >
                {{ selectedRemediation.severity }}
              </span>
            </div>
          </div>
          
          <!-- Remediation Solution -->
          <div class="mb-6">
            <h5 class="text-base font-medium text-gray-800 dark:text-white mb-2">Applied Solution</h5>
            <p class="text-gray-700 dark:text-gray-300 mb-3">{{ selectedRemediation.solution }}</p>
            <div class="bg-gray-50 dark:bg-gray-900 p-3 rounded-lg">
              <div class="flex justify-between items-center mb-2">
                <span class="text-sm font-medium text-gray-500 dark:text-gray-400">Applied Changes</span>
                <button
                  @click="copyToClipboard(selectedRemediation.changes || '')"
                  class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                  title="Copy to clipboard"
                >
                  <i class="far fa-copy"></i>
                </button>
              </div>
              <pre class="text-xs text-gray-700 dark:text-gray-300 overflow-x-auto">{{ selectedRemediation.changes || 'No changes recorded' }}</pre>
            </div>
          </div>
          
          <!-- Timeline -->
          <div>
            <h5 class="text-base font-medium text-gray-800 dark:text-white mb-4">Remediation Timeline</h5>
            <div class="relative pl-8 space-y-6 before:absolute before:top-0 before:bottom-0 before:left-3 before:w-0.5 before:bg-gray-200 dark:before:bg-gray-700">
              <div
                v-for="(event, eventIndex) in selectedRemediation.events"
                :key="eventIndex"
                class="relative"
              >
                <div
                  class="absolute left-[-30px] w-6 h-6 rounded-full flex items-center justify-center"
                  :class="getEventIconClass(event.type)"
                >
                  <i :class="getEventIcon(event.type)" class="text-xs"></i>
                </div>
                <div class="mb-1 flex justify-between items-center">
                  <h6 class="text-sm font-medium text-gray-800 dark:text-white">
                    {{ formatEventType(event.type) }}
                  </h6>
                  <span class="text-xs text-gray-500 dark:text-gray-400">
                    {{ formatTime(event.timestamp) }}
                  </span>
                </div>
                <p class="text-sm text-gray-600 dark:text-gray-300">{{ event.message }}</p>
                
                <!-- Event Details -->
                <div
                  v-if="event.details && hasDetails(event.details)"
                  class="mt-2 p-3 bg-gray-50 dark:bg-gray-900 rounded text-xs text-gray-600 dark:text-gray-400"
                >
                  <div
                    v-for="(value, key) in event.details"
                    :key="key"
                    class="mb-1 last:mb-0"
                  >
                    <span class="font-medium">{{ formatDetailKey(key) }}:</span>
                    <span v-if="typeof value === 'object'">
                      <pre class="mt-1 overflow-x-auto">{{ JSON.stringify(value, null, 2) }}</pre>
                    </span>
                    <span v-else-if="key.includes('command') || key.includes('patch')" class="block mt-1">
                      <pre class="overflow-x-auto">{{ value }}</pre>
                    </span>
                    <span v-else> {{ value }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
</template>






<script setup>
import { ref, computed, onMounted, watch} from 'vue';
import axios from 'axios';

// State variables
const isDarkMode = ref(localStorage.getItem('darkMode') === 'true');
const loading = ref(false);
const remediations = ref([]);
const logs = ref([]);
const currentStep = ref(0);// Documentation for Vertical Stepper Component Styling
const currentPage = ref(1);
const pageSize = ref(5); // Show 5 items per page


const stepFilter = ref('');
const statusFilter = ref('');
const showDetailsModal = ref(false);
const selectedRemediation = ref(null);

// API base URL
const remediationUrl = `${import.meta.env.VITE_SELF_HEALING}`;

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

// Fetch remediations from API
const fetchRemediations = async () => {
loading.value = true;
try {
  // Fetch remediations from API
  const response = await axios.get(`${remediationUrl}/remediations/?skip=0&limit=50`, {
    headers: getAuthHeaders(),
    params: {
      status: statusFilter.value || undefined
    }
  });
  
  if (response.data) {
    remediations.value = response.data.map(item => ({
      status: item.current_status,
      resourceType: item.incident_details?.affected_resources?.[0]?.kind || 'Resource',
      resourceName: item.incident_details?.affected_resources?.[0]?.name || 'Unknown',
      namespace: item.incident_details?.affected_resources?.[0]?.namespace || 'default',
      timestamp: item.start_time,
      duration: item.end_time ? getDuration(item.start_time, item.end_time) : 'In Progress',
      issue: item.incident_details?.description || 'Unknown issue',
      severity: item.incident_details?.severity || 'INFO',
      solution: item.plan_details?.summary || 'No solution details available',
      changes: item.plan_details?.steps?.map(step =>
        `${step.action_type} on ${step.target_resource.kind}/${step.target_resource.name}:\n${step.command_or_payload?.command || ''}`
      ).join('\n\n') || '',
      events: item.trace_log?.map(log => ({
        type: log.event_type,
        timestamp: log.timestamp,
        message: log.message,
        details: log.details
      })) || []
    }));
    
    // Extract logs from the trace_log of all remediations
    const allLogs = [];
    response.data.forEach(item => {
      if (item.trace_log && Array.isArray(item.trace_log)) {
        allLogs.push(...item.trace_log);
      }
    });
    
    // Sort logs by timestamp (newest first)
    logs.value = allLogs.sort((a, b) => {
      return new Date(b.timestamp) - new Date(a.timestamp);
    });
    
    // Update current step based on latest logs
    updateCurrentStep();
  }
} catch (error) {
  console.error('Error fetching remediations:', error);
  
  updateCurrentStep();
} finally {
  loading.value = false;
}
};

// Update current step based on latest logs
const updateCurrentStep = () => {
if (logs.value.length === 0) {
  currentStep.value = 1;
  return;
}

// Find the latest log entry for each step
const hasAnalyzing = logs.value.some(log => log.event_type.includes('ANALYZING'));
const hasReasoning = logs.value.some(log => log.event_type.includes('REASONING'));
const hasEnforcing = logs.value.some(log => log.event_type.includes('ENFORCING'));
const hasExecuting = logs.value.some(log => log.event_type.includes('EXECUTING'));

if (hasExecuting) {
  currentStep.value = 4;
} else if (hasEnforcing) {
  currentStep.value = 3;
} else if (hasReasoning) {
  currentStep.value = 2;
} else if (hasAnalyzing) {
  currentStep.value = 1;
} else {
  currentStep.value = 1;
}
};

// Filter logs by step
const filterLogsByStep = (step) => {
stepFilter.value = step;
};

// Clear step filter
const clearStepFilter = () => {
stepFilter.value = '';
};

// Get step title for logs section
const getStepTitle = () => {
if (!stepFilter.value) {
  return 'Remediation';
}

switch (stepFilter.value) {
  case 'ANALYZING':
  stepFilter.value = 'ANALYSIS_COMPLETED';
    return 'Analyzer';
  case 'REASONING':
  stepFilter.value = 'REASONING_STARTED';
    return 'Reasoner';
  case 'ENFORCING':
  stepFilter.value = 'ENFORCEMENT_COMPLETED';
    return 'ENFORCEMENT_COMPLETED';
  case 'EXECUTING':
  stepFilter.value = 'PLAN_GENERATED';
    return 'Executor';
  default:
    return stepFilter.value;
}
};

// Filtered logs based on step and status filters
const filteredLogs = computed(() => {
let result = logs.value;
console.log('result', result);


if (stepFilter.value) {
  result = result.filter(log => log.event_type.includes(stepFilter.value));
}
console.log("stepFilter.value", stepFilter.value);
console.log("stepresult", result);

if (statusFilter.value) {
  result = result.filter(log => log.event_type.includes(statusFilter.value));
}

return result;
});

// View remediation details
const viewRemediationDetails = (remediation) => {
selectedRemediation.value = remediation;
showDetailsModal.value = true;
};

// Format date for display
const formatDate = (timestamp) => {
if (!timestamp) return 'Unknown';

const date = new Date(timestamp);
return date.toLocaleDateString('en-US', {
  year: 'numeric',
  month: 'short',
  day: 'numeric'
});
};

// Format time for display
const formatTime = (timestamp) => {
if (!timestamp) return 'Unknown';

const date = new Date(timestamp);
return date.toLocaleTimeString('en-US', {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit'
});
};

// Get duration between two timestamps
const getDuration = (startTime, endTime) => {
if (!startTime || !endTime) return 'N/A';

const start = new Date(startTime);
const end = new Date(endTime);
const durationMs = end - start;

const seconds = Math.floor(durationMs / 1000);
if (seconds < 60) {
  return `${seconds} seconds`;
}

const minutes = Math.floor(seconds / 60);
const remainingSeconds = seconds % 60;
return `${minutes}m ${remainingSeconds}s`;
};

// Get CSS class for status
const getStatusClass = (status) => {
if (!status) return '';

switch (status.toUpperCase()) {
  case 'SUCCESS':
    return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
  case 'FAILURE':
    return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
  case 'IN_PROGRESS':
    return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
  case 'ANALYZING':
    return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
  case 'REASONING':
    return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400';
  case 'ENFORCING':
    return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
  default:
    return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400';
}
};

// Get CSS class for severity
const getSeverityClass = (severity) => {
if (!severity) return '';

switch (severity.toUpperCase()) {
  case 'CRITICAL':
    return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
  case 'WARNING':
    return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
  case 'INFO':
    return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
  default:
    return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400';
}
};

// Get background class for log entry
const getLogBackgroundClass = (eventType) => {
if (!eventType) return '';

if (eventType.includes('ERROR') || eventType.includes('FAILURE')) {
  return 'bg-red-50 dark:bg-red-900/10 border-red-100 dark:border-red-900/20';
} else if (eventType.includes('SUCCESS') || eventType.includes('COMPLETED')) {
  return 'bg-green-50 dark:bg-green-900/10 border-green-100 dark:border-green-900/20';
} else if (eventType.includes('WARNING')) {
  return 'bg-yellow-50 dark:bg-yellow-900/10 border-yellow-100 dark:border-yellow-900/20';
} else {
  return 'bg-gray-50 dark:bg-gray-900/10 border-gray-100 dark:border-gray-700/20';
}
};

// Get icon class for event type
const getEventIconClass = (eventType) => {
if (!eventType) return '';

if (eventType.includes('ERROR') || eventType.includes('FAILURE')) {
  return 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400';
} else if (eventType.includes('SUCCESS') || eventType.includes('COMPLETED')) {
  return 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400';
} else if (eventType.includes('WARNING')) {
  return 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400';
} else if (eventType.includes('ANALYZING')) {
  return 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400';
} else if (eventType.includes('REASONING')) {
  return 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400';
} else if (eventType.includes('ENFORCING')) {
  return 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400';
} else {
  return 'bg-gray-100 text-gray-600 dark:bg-gray-900/30 dark:text-gray-400';
}
};

// Get icon for event type
const getEventIcon = (eventType) => {
if (!eventType) return 'fas fa-circle';

if (eventType.includes('ERROR') || eventType.includes('FAILURE')) {
  return 'fas fa-times-circle';
} else if (eventType.includes('SUCCESS') || eventType.includes('COMPLETED')) {
  return 'fas fa-check-circle';
} else if (eventType.includes('WARNING')) {
  return 'fas fa-exclamation-triangle';
} else if (eventType.includes('STARTED')) {
  return 'fas fa-play-circle';
} else if (eventType.includes('ANALYZING')) {
  return 'fas fa-search';
} else if (eventType.includes('REASONING')) {
  return 'fas fa-brain';
} else if (eventType.includes('ENFORCING')) {
  return 'fas fa-shield-alt';
} else if (eventType.includes('EXECUTING')) {
  return 'fas fa-play';
} else {
  return 'fas fa-info-circle';
}
};

// Format event type for display
const formatEventType = (eventType) => {
if (!eventType) return 'Unknown Event';

// Replace underscores with spaces and capitalize each word
return eventType
  .split('_')
  .map(word => word.charAt(0) + word.slice(1).toLowerCase())
  .join(' ');
};

// Check if event has details to display
const hasDetails = (details) => {
return details && Object.keys(details).length > 0;
};

// Format detail key for display
const formatDetailKey = (key) => {
if (!key) return '';

// Replace underscores with spaces and capitalize each word
return key
  .split('_')
  .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
  .join(' ');
};

// Format detail value for display
const formatDetailValue = (value) => {
if (value === null || value === undefined) return 'N/A';

if (typeof value === 'object') {
  return JSON.stringify(value, null, 2);
}

return value.toString();
};

// Copy text to clipboard
const copyToClipboard = (text) => {
navigator.clipboard.writeText(text)
  .then(() => {
    console.log('Copied to clipboard');
    // Could show a toast notification here
  })
  .catch(err => {
    console.error('Failed to copy: ', err);
  });
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

const paginatedRemediations = computed(() => {
const start = (currentPage.value - 1) * pageSize.value;
const end = start + pageSize.value;
return remediations.value.slice(start, end);
});

const totalPages = computed(() => {
return Math.ceil(remediations.value.length / pageSize.value);
});

const nextPage = () => {
if (currentPage.value < totalPages.value) {
  currentPage.value++;
}
};

const prevPage = () => {
if (currentPage.value > 1) {
  currentPage.value--;
}
};

const goToPage = (page) => {
currentPage.value = page;
};

watch(remediations, () => {
currentPage.value = 1;
});


// Initialize on component mount
onMounted(() => {
updateDarkModeClasses();
fetchRemediations();
});
</script>

<style>
/* Import Font Awesome */
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');
</style>
