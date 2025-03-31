<template>
  <div class="flex flex-wrap gap-4 p-4">
    <!-- First Box: Plugins -->
    <n-card class="p-4 w-full md:w-4/4 shadow-md rounded-lg">
      <n-text class="text-lg font-bold"> Plugins </n-text>
      <n-card class="p-4 md:w-4/4 shadow-md rounded-lg mt-4">
        <div class="mt-2">
          <!-- Content inside Plugins box -->
          <n-button type="success" size="large" ghost> Wazuh </n-button>
        </div>
      </n-card>
    </n-card>

    <!-- Second Box: Details -->
    <n-card class="p-4 w-full md:w-4/4 shadow-md rounded-lg">
      <n-text class="text-lg font-bold"> Details </n-text>
      <div class="mt-2">
        <!-- Content inside Details box -->
        <p>Add your details-related content here.</p>
      </div>

      <!-- Buttons at the bottom -->
      <div class="flex gap-4 mt-18">
        <!-- Enable/Disable Button -->
        <n-button
          :type="isEnabled ? 'error' : 'success'"
          @click="toggleEnableDisable"
        >
          {{ isEnabled ? "Disable" : "Enable" }}
        </n-button>

        <!-- Activate/Deactivate Button -->
        <n-button
          :type="isActivated ? 'info' : 'warning'"
          ghost
          @click="toggleActivateDeactivate"
        >
          {{ isActivated ? "Deactivate" : "Activate" }}
        </n-button>
      </div>
    </n-card>
  </div>
</template>

<script setup>
import { ref } from "vue";

// State variables for buttons
const isEnabled = ref(false); // Track Enable/Disable state
const isActivated = ref(false); // Track Activate/Deactivate state

// Toggle logic for Enable/Disable
const toggleEnableDisable = () => {
  isEnabled.value = !isEnabled.value;
};

// Toggle logic for Activate/Deactivate
const toggleActivateDeactivate = () => {
  isActivated.value = !isActivated.value;
};
</script>

<style scoped>
/* Optional custom styles */
</style>
