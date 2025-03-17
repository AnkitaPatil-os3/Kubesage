<template>
    <div class="pr-5 iframe-container">
      <!-- Left and right overlays to hide headers -->
      <n-card class="overlay-text">
        <div class="heading-text p-7">
          <n-text class="text-lg font-bold">Java Dashboard</n-text>
        </div>
      </n-card>
  
      <iframe :src="iframeSrc" width="100%" height="100%" frameborder="0" allowfullscreen
        class="m-5 dashboard-iframe"></iframe>
    </div>
  </template>
  
  <script setup>
  import { ref, computed, watchEffect } from "vue";
  
  // Reactive state for the iframe URL
  const iframeSrc = ref("");
  
  // Computed property to read dark mode state dynamically from localStorage
  const isDark = computed(() => {
    return localStorage.getItem("vueuse-color-scheme") === "dark";
  });
  
  // Computed property for iframe URL
  const iframeUrl = computed(() => {
    const theme = isDark.value ? "dark" : "light";
    return `https://10.0.34.212:3000/d/X034JGT7Gz/apm-java?orgId=1&from=now-5m&to=now&theme=${theme}`;
  });
  
  // Watch the computed value to update iframe source reactively
  watchEffect(() => {
    iframeSrc.value = iframeUrl.value; // Update iframe source on theme change
  });
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
  </style>
  