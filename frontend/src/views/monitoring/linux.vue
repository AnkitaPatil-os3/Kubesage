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
        <n-text class="text-lg font-bold">Linux Dashboard</n-text>
      </div>
    </n-card>

    <iframe :src="iframeSrc" width="100%" height="100%" frameborder="0" allowfullscreen
      class="m-5 dashboard-iframe"></iframe>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

// Reactive state for the iframe URL
const iframeSrc = ref("");

// Computed property to read dark mode state dynamically from localStorage
const isDark = computed(() => {
  return localStorage.getItem("vueuse-color-scheme") === "dark";
});

// Computed property for iframe URL
const iframeUrl = computed(() => {
  const theme = isDark.value ? "dark" : "light";
  return `https://10.0.34.212:3000/d/rYdddlPWk/node-exporter-full?from=now-30m&to=now&timezone=browser&var-datasource=fe4eeqvcnhce8a&theme=${theme}`;
});

// Watch the computed value to update iframe source reactively
watchEffect(() => {
  iframeSrc.value = iframeUrl.value; // Update iframe source on theme change
});

function goBack() {
  router.push("/dashboard");
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
  left: 1.2%;
  width: 98.8%;
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

.theme-toggle-button {
  padding: 10px 15px;
  font-size: 16px;
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

.theme-toggle-button:hover {
  background-color: #218838;
}

.header-nav {
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 10;
}
</style>
