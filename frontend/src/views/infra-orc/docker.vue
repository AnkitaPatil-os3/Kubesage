<template>
    <div class="pr-5 iframe-container">
      <!-- Left and right overlays to hide headers -->
      <n-card class="overlay-text">
        <div class="heading-text p-7">
          <n-text class="text-lg font-bold">Docker Dashboard</n-text>
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
  
  // Detecting dark mode using Naive UI's useOsTheme
  const osTheme = useOsTheme();
  // Computed property to read dark mode state dynamically from localStorage
const isDark = computed(() => {
  return localStorage.getItem("vueuse-color-scheme") === "dark";
});
  
  // Computed property to generate the iframe URL based on the theme
  const iframeUrl = computed(() => {
    const theme = isDark.value ? "dark" : "light";
    return `https://10.0.34.212:3000/d/4dMaCsRZz/docker-monitoring?var-interval=$__auto&from=now-30m&to=now&timezone=browser&var-job=integrations%2Fcadvisor&var-node=docker-monitor&refresh=10s&theme=${theme}`;
  });
  
  // Watch the theme and update iframe source accordingly
  watchEffect(() => {
    iframeSrc.value = iframeUrl.value;
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
  