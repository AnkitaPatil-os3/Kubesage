<template>
  <div class="pr-5 iframe-container">
    <!-- Left and right overlays to hide headers -->
    <n-card class="overlay-text" >
      <div class="heading-text p-7">
        <n-text class="text-lg font-bold">Cluster Node Details</n-text>
      </div>
    </n-card>

    <!-- Iframe with dynamic source -->
    <iframe :src="iframeSrc" width="100%" height="100%" frameborder="0" allowfullscreen
      class="m-5 dashboard-iframe"></iframe>
  </div>
</template>

<script setup>
import { ref, computed, watchEffect } from "vue";
import { useOsTheme } from "naive-ui";
import { useRouter } from "vue-router";

// Reactive state for the iframe URL
const iframeSrc = ref("");

// Computed property to detect dark mode based on Naive UI's theme
const osTheme = useOsTheme();
// Computed property to read dark mode state dynamically from localStorage
const isDark = computed(() => {
  return localStorage.getItem("vueuse-color-scheme") === "dark";
});

// Computed property to generate iframe URL dynamically based on the current theme
const iframeUrl = computed(() => {
  const theme = isDark.value ? "dark" : "light";
  return `https://10.0.34.212:3000/d/edoqpj3c1u3uoc/kub-cluster-node-details?orgId=1&from=now-6h&to=now&var-DS=be964rwb0rbpce&theme=${theme}`;
});

// Watch the computed value to update iframe source dynamically
watchEffect(() => {
  iframeSrc.value = iframeUrl.value; // Update iframe source whenever the theme changes
});

const router = useRouter();

// Function to handle the back button click
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

.back-button:hover {
  background-color: #0056b3;
}
</style>
