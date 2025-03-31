<template>
  <div class="pr-5 iframe-container">
    <!-- Left and right overlays to hide headers -->
    <n-card class="overlay-text">
      <!-- Back button with a CSS arrow -->
      <button @click="goBack" class="back-button">
        <i class="fas fa-arrow-left"></i> <!-- FontAwesome left arrow icon -->
        Back
      </button>
      <div class="heading-text p-7">
        <n-text class="text-lg font-bold">Windows Event Logs</n-text>
      </div>
    </n-card>

    <iframe :src="iframeSrc" width="100%" height="100%" frameborder="0" allowfullscreen
      class="m-5 dashboard-iframe"></iframe>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";
import { useOsTheme } from "naive-ui";
import { useRouter } from "vue-router";

// Reactive state for the iframe URL
const iframeSrc = ref("");
const router = useRouter();

// Computed property to read dark mode state dynamically from localStorage
const isDark = computed(() => {
  return localStorage.getItem("vueuse-color-scheme") === "dark";
});

// Computed property to generate the iframe URL based on the theme
const iframeUrl = computed(() => {
  const theme = isDark.value ? "dark" : "light";
  return `https://10.0.34.212:3000/d/ednr88jj40m4gf/edr-windows-event-logs?from=2024-12-11T04:13:47.177Z&to=2024-12-11T10:13:47.177Z&var-agent_name=$__all&var-Filters=&var-Filters-2=&theme=${theme}`;
  
});

// Detect system theme using Naive UI's useOsTheme
const osTheme = useOsTheme();


// Watch the theme and update iframe source accordingly
watchEffect(() => {
  iframeSrc.value = iframeUrl.value;
});

// Function to navigate back to the /activated-plugins route
function goBack() {
  router.push("/activated-plugins");
}
</script>

<style scoped>
html,
body {
  height: 100%;
  margin: 0;
}

#app {
  height: 100%;
}

.p-6 {
  height: calc(100vh - 12px);
  /* Adjusting for padding or other elements */
}

.dashboard-iframe {
  height: calc(100vh - 52px);
}

.overlay-text {
  position: absolute;
  top: 0;
  left: 1%;
  width: 99%;
  height: 100px;
  z-index: 2;
}

.heading-text {
  display: flex;
  justify-content: center;
  align-items: center;
  text-align: center;
}

.dark-overlay {
  background-color: rgb(15, 15, 15);
  color: white;
}

.iframe-container {
  position: relative;
}

/* Back button styles */
.back-button {
  position: absolute;
  top: 20px;
  left: 20px;
  padding: 10px 15px;
  font-size: 16px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
  display: flex;
  align-items: center;
  cursor: pointer;
}

.back-arrow {
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 5px solid white;
  margin-right: 8px;
}

.back-button:hover {
  background-color: #0056b3;
}
</style>
