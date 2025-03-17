<template>
  <div class="flex flex-wrap gap-4 p-4">
    <!-- First Box: Plugins -->
    <n-card class="p-4 w-full md:w-4/4 shadow-md rounded-lg">
      <n-text class="text-lg font-bold">Plugins</n-text>

      <!-- Success Message -->
      <div v-if="successMessage" class="mt-4 p-4 bg-green-500 text-white rounded-lg">
        {{ successMessage }}
      </div>

      <!-- Error Message -->
      <div v-if="errorMessage" class="mt-4 p-4 bg-red-500 text-white rounded-lg">
        {{ errorMessage }}
      </div>

      <div class="card-container mt-4 w-80">
        <n-card v-for="card in cards" :key="card" class="hover-card"
          :class="{ 'selected-card': selectedCards.includes(card), 'activated-card': activatedPlugins.includes(card) }"
          @click="toggleCard(card)">
          <!-- Add Wazuh Logo (SVG) in front of each plugin -->
          <div class="flex items-center">
            <!-- Wazuh Logo SVG -->
            <img src="https://upload.wikimedia.org/wikipedia/commons/6/6c/Wazuh_blue.png" class="sFlh5c FyHeAf iPVvYb" style="max-width: 225px; height: 30px; margin: 0px; width: 30px;" alt="File:Wazuh blue.png - Wikimedia Commons">
            <div class="font-semibold ml-2">{{ card }}</div>
          </div>

          <!-- Activate/Deactivate Button -->
          <div class="flex justify-end mt-2">
            <n-button
              v-if="!activatedPlugins.includes(card)"
              type="success"
              @click="activatePlugin(card)"
            >
              Activate
            </n-button>
            <n-button
              v-if="activatedPlugins.includes(card)"
              type="error"
              @click="deactivatePlugin(card)"
            >
              Deactivate
            </n-button>
          </div>
        </n-card>
      </div>

    </n-card>
  </div>

  <!-- Categories Section with Transition -->
  <transition
        name="category-transition"
        @before-enter="beforeEnter"
        @enter="enter"
        @leave="leave"
      >
        <n-card class="p-4 w-full shadow-md rounded-lg mt-10">
          <n-text class="text-lg font-bold">Categories</n-text>
          <!-- Category Cards -->
          <div class="category-container flex flex-wrap gap-4 mt-4">
            <n-card
              v-for="(category, index) in categories"
              :key="index"
              class="category-card hover-card p-4 shadow-md rounded-lg w-125"
              hoverable
              @click="navigateToCategory(category.url)"
            >
              <n-text class="text-md font-semibold">{{ category.name }}</n-text>
            </n-card>
          </div>
        </n-card>
      </transition>
</template>

<script setup>
import { ref, onMounted } from "vue";
import axios from "axios";
import { useRouter } from 'vue-router';  // Assuming you're using Vue Router for navigation
  
const router = useRouter(); // Access the router instance

// List of cards and activated plugins
const cards = ref(['SIEM']);
const activatedPlugins = ref([]); // Tracks the activated plugins

// Success and error messages
const successMessage = ref('');
const errorMessage = ref('');

// Selected cards
const selectedCards = ref([]);

// Track the state for Enable/Disable
const isEnabled = ref(false);

const categories = [
    { name: "Compliance", url: "/compliance" },
    { name: "File Integrity Monitoring", url: "/fileIntegrity" },
    { name: "Mitre Attack", url: "/mitreAttack" },
    { name: "Windows Event Logs", url: "/windowsEvent" },
    { name: "Summary", url: "/summary" },
  ];

// Toggle card selection
const toggleCard = (card) => {
  if (selectedCards.value.includes(card)) {
    selectedCards.value = selectedCards.value.filter((c) => c !== card);
  } else {
    selectedCards.value.push(card);
  }
};

// Function to navigate to a specific category's URL
const navigateToCategory = (categoryUrl) => {
    router.push(categoryUrl);  // Navigate to the category page
  };

// Enable/Disable functionality
const toggleEnableDisable = () => {
  isEnabled.value = !isEnabled.value;
  console.log(isEnabled.value ? "Enabled" : "Disabled");
};

// Fetch activated plugins from the backend
const fetchActivatedPlugins = async () => {
  try {
    const response = await axios.get(`/api/v1/plugins/`);
    // Filter only activated plugins
    activatedPlugins.value = response.data.filter(plugin => plugin.activated).map(plugin => plugin.name);
  } catch (error) {
    console.error("Error fetching activated plugins:", error);
    errorMessage.value = "Failed to fetch plugins.";
  }
};

// Activate a plugin
const activatePlugin = async (plugin) => {
  try {
    const response = await axios.post(
      `/api/v1/plugins/activate/`,
      { plugin },
      {
        headers: {
          "Content-Type": "application/json",
        }
      }
    );
    successMessage.value = response.data.message;  // Set the success message
    fetchActivatedPlugins();  // Refresh the list of activated plugins
  } catch (error) {
    console.error("Error activating plugin:", error);
    errorMessage.value = "Failed to activate plugin.";
  }

  // Clear the success/error message after 3 seconds
  setTimeout(() => {
    successMessage.value = '';
    errorMessage.value = '';
  }, 3000);
};

// Deactivate a plugin
const deactivatePlugin = async (plugin) => {
  try {
    const response = await axios.delete(
      `/api/v1/plugins/delete_by_name/`,
      {
        data: { plugin }, // Pass the plugin name as a parameter in the request body
        headers: {
          "Content-Type": "application/json",
        }
      }
    );
    successMessage.value = response.data.message;  // Set the success message
    fetchActivatedPlugins();  // Refresh the list of activated plugins
  } catch (error) {
    console.error("Error deactivating plugin:", error);
    errorMessage.value = "Failed to deactivate plugin.";
  }

  // Clear the success/error message after 3 seconds
  setTimeout(() => {
    successMessage.value = '';
    errorMessage.value = '';
  }, 3000);
};

// Fetch the activated plugins when the component mounts
onMounted(() => {
  fetchActivatedPlugins();
});
</script>

<style scoped>
/* Optional custom styles */
.card-container {
  display: flex;
  flex-direction: row;
  gap: 1rem;
}

.hover-card {
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}

.hover-card:hover {
  transform: translateY(-10px);
  box-shadow: 0 8px 15px rgba(0, 0, 0, 0.3);
  cursor: pointer;
}

.selected-card {
  border: 1px solid black;
  background-color: lightgray;
}

.activated-card {
  background-color: #ffff !important;
}
</style>
