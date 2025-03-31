<template>
  <div class="pr-5 iframe-container">
    <!-- Left and right overlays to hide headers -->
    <n-card class="overlay-text" >
      <!-- Back button with a CSS arrow -->
      <button @click="goBack" class="back-button">
        <i class="fas fa-arrow-left"></i> <!-- FontAwesome left arrow icon -->
        Back
      </button>
      <div class="heading-text p-7">
        <n-text class="text-lg font-bold">Mitre Attack</n-text>
      </div>
    </n-card>

    <iframe :src="iframeSrc" width="100%" height="100%" frameborder="0" allowfullscreen
      class="m-5 dashboard-iframe"></iframe>
  </div>
</template>

<script setup>
import { ref, computed, watchEffect } from "vue";
import { useOsTheme } from "naive-ui";
import { useRouter } from "vue-router";
const router = useRouter();

// Reactive state for the iframe URL
const iframeSrc = ref("");


// Detecting dark mode using Naive UI's useOsTheme
const osTheme = useOsTheme();
// Computed property to read dark mode state dynamically from localStorage
const isDark = computed(() => {
  return localStorage.getItem("vueuse-color-scheme") === "dark";
});

// Computed property to generate the iframe URL based on the theme
const iframeUrl = computed(() => {
  const theme = isDark.value ? "dark" : "light";
  return `https://10.0.34.212:3000/d/fdnr88r7eaayoc/edr-mitre-attandck?from=2024-12-10T00:40:45.539Z&to=2024-12-10T06:40:45.539Z&var-Filters=&var-agent_name=$__all&theme=${theme}`;
});

// Watch the theme and update iframe source accordingly
watchEffect(() => {
  iframeSrc.value = iframeUrl.value;
});

// Back button functionality
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
  transition: background-color 0.3s ease;
}

.dark-overlay {
  background-color: rgb(15, 15, 15);
  color: white;
}

.heading-text {
  display: flex;
  justify-content: center;
  align-items: center;
  text-align: center;
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
