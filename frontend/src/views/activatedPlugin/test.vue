<template>
    <div class="flex flex-wrap gap-4 p-4">
      <!-- Display the activated plugins -->
      <n-card class="p-4 w-full shadow-md rounded-lg">
        <n-text class="text-lg font-bold">Currently Activated Plugins</n-text>
  
        <!-- Success Message -->
        <div v-if="successMessage" class="mt-4 p-4 bg-green-500 text-white rounded-lg">
          {{ successMessage }}
        </div>
  
        <div v-if="activatedPlugins.length > 0">
          <div class="card-container flex flex-col gap-4 mt-10">
            <n-card
              class="hover-card p-4 shadow-md rounded-lg w-100"
              v-for="plugin in activatedPlugins"
              :key="plugin.id"
              hoverable
              
            >
              <div class="flex justify-between items-center">
                <n-text class="text-lg font-bold" @click="openCard">{{ plugin.name }}</n-text>
                <n-button type="warning" @click="deactivatePlugin(plugin.id)">Deactivate</n-button>
              </div>
            </n-card>
          </div>
        </div>
  
        <div v-else>
          <p>No plugins are activated.</p>
        </div>
      </n-card>
  
      <!-- Categories Section with Transition -->
      <transition
        name="category-transition"
        @before-enter="beforeEnter"
        @enter="enter"
        @leave="leave"
      >
        <n-card v-if="showAdditionalCard" class="p-4 w-full shadow-md rounded-lg mt-10">
          <n-text class="text-lg font-bold">Categories</n-text>
          <!-- Category Cards -->
          <div class="category-container flex flex-wrap gap-4 mt-4">
            <n-card
              v-for="(category, index) in categories"
              :key="index"
              class="category-card hover-card p-4 shadow-md rounded-lg w-1/3"
              hoverable
              @click="navigateToCategory(category.url)"
            >
              <n-text class="text-md font-semibold">{{ category.name }}</n-text>
            </n-card>
          </div>
        </n-card>
      </transition>
    </div>
  </template>
  
  <script setup>
  import { ref, onMounted } from "vue";
  import axios from "axios";
  import { useRouter } from 'vue-router';  // Assuming you're using Vue Router for navigation
  
  const router = useRouter(); // Access the router instance
  const activatedPlugins = ref([]);
  const successMessage = ref('');
  const showAdditionalCard = ref(false); // Flag to control the visibility of the additional card
  
  const categories = [
    { name: "Compliance", url: "/compliance" },
    { name: "File Integrity Monitoring", url: "/fileIntegrity" },
    { name: "Mitre Attack", url: "/mitreAttack" },
    { name: "Windows Event Logs", url: "/windowsEvent" },
    { name: "Summary", url: "/summary" },
  ];
  
  const fetchActivatedPlugins = async () => {
    try {
      const response = await axios.get(`/api/v1/plugins/`);
      activatedPlugins.value = response.data.filter(plugin => plugin.activated);
    } catch (error) {
      console.error("Error fetching activated plugins:", error);
    }
  };
  
  const deactivatePlugin = async (pluginId) => {
    try {
      const response = await axios.delete(`/api/v1/plugins/${pluginId}/deactivate/`);
      successMessage.value = response.data.message;
      // Refresh the activated plugins list
      fetchActivatedPlugins();
    } catch (error) {
      console.error("Error deactivating plugin:", error);
    } finally {
      setTimeout(() => {
        successMessage.value = '';
      }, 5000);
    }
  };
  
  // Function to navigate to a specific category's URL
  const navigateToCategory = (categoryUrl) => {
    router.push(categoryUrl);  // Navigate to the category page
  };
  
  // Function to toggle the visibility of the additional card
  const openCard = () => {
    showAdditionalCard.value = !showAdditionalCard.value;
  };
  
  onMounted(() => {
    fetchActivatedPlugins();
  });
  </script>
  
  <style>
  .card-container {
    display: flex;
    flex-direction: row;
    gap: 1rem;
  }
  
  .hover-card {
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
    cursor: pointer; /* Hand cursor for hover */
  }
  
  .hover-card:hover {
    transform: translateY(-10px);
    box-shadow: 0 8px 15px rgba(0, 0, 0, 0.3);
  }
  
  .category-container {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
  }
  
  .category-card {
    width: 30%; /* Three cards per row */
    cursor: pointer;
  }
  
  .category-card:hover {
    transform: translateY(-5px); /* Slight lift */
    box-shadow: 0 8px 15px rgba(0, 0, 0, 0.2); /* Stronger shadow on hover */
  }
  
  /* Transition for category section */
  .category-transition-enter-active, .category-transition-leave-active {
    transition: opacity 0.5s ease, transform 0.5s ease;
  }
  
  .category-transition-enter, .category-transition-leave-to /* .category-transition-leave-active in <2.1.8 */ {
    opacity: 0;
    transform: translateY(20px); /* Slide from below */
  }
  
  /* Before enter hook - initial state */
  .category-transition-before-enter {
    opacity: 0;
    transform: translateY(20px); /* Start from below */
  }
  </style>
  
