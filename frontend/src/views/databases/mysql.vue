<template>
    <div class="pr-5 iframe-container">
      <!-- Left and right overlays to hide headers -->
      <n-card class="overlay-text" >
  
        <div class="heading-text p-7">
          <n-text class="text-lg font-bold">MySQL Dashboard</n-text>
        </div>
      </n-card>
  
      <iframe :src="iframeSrc" width="100%" height="100%" frameborder="0" allowfullscreen
        class="m-5 dashboard-iframe"></iframe>
    </div>
  </template>
  
  <script setup>
  import { ref, computed, watchEffect } from "vue";
  import { useRouter } from "vue-router";
  const route = useRoute();
  const instanceName = route.query.instance;
  // Reactive state for the iframe URL
  const iframeSrc = ref("");
  
  // Computed property to read dark mode state dynamically from localStorage
  const isDark = computed(() => {
    return localStorage.getItem("vueuse-color-scheme") === "dark";
  });
  
  // Computed property for iframe URL
  const iframeUrl = computed(() => {
    const theme = isDark.value ? "dark" : "light";
    return `https://10.0.34.212:3000/d/549c2bf8936f7767ea6ac47c47b00f2/mysql?orgId=1&from=now-10m&to=now&var-instance=${instanceName}&theme=${theme}`;
  });
  
  // Watch the computed value to update iframe source reactively
  watchEffect(() => {
    iframeSrc.value = iframeUrl.value; // Update iframe source on theme change
  });
  
  const router = useRouter();
  
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
  
  .back-button:hover {
    background-color: #0056b3;
  }
  </style>