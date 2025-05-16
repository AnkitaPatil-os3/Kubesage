<template>
    <div class="app-container" :class="{ 'dark-mode': isDarkMode }">
      <div class="main-content">
        <!-- Header -->
        <div class="cost-dashboard-header">
          <h2>Resource Cost Dashboard</h2>
        </div>
        
        <!-- Dashboard Container with Overlay Header -->
        <div class="dashboard-container">
          <!-- Overlay header to hide Grafana's top heading -->
          <div></div>
          
          <iframe
            :src="grafanaUrl"
            width="100%"
            height="100%"
            frameborder="0"
            allowfullscreen
          ></iframe>
        </div>
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref, onMounted, computed, watch } from 'vue';
  
  // Dark mode state
  const isDarkMode = ref(localStorage.getItem('darkMode') === 'true');
  
  // Grafana URL with parameters
  const grafanaUrl = computed(() => {
    const baseUrl = 'https://10.0.34.212:3000/grafana-monitoring/d/opencost-cost-reporter-basic-overview/opencost-cost-reporter-basic-overview';
    const params = new URLSearchParams({
      'orgId': '1',
      'from': 'now-1h',
      'to': 'now',
      'timezone': 'browser',
      'var-datasource': 'fekxeesdvhgcgb',
      'var-namespace': '$__all',
      'var-job': 'opencost',
      'theme': isDarkMode.value ? 'dark' : 'light',
      'kiosk': 'tv', // Hide navigation
      'hideControls': 'true', // Hide controls including share button
      'toolbar': 'false' // Hide toolbar
    });
    
    return `${baseUrl}?${params.toString()}`;
  });
  
  // Update dark mode classes
  const updateDarkModeClasses = () => {
    if (isDarkMode.value) {
      document.documentElement.classList.add('dark');
      document.body.style.backgroundColor = 'rgb(24 24 28)';
    } else {
      document.documentElement.classList.remove('dark');
      document.body.style.backgroundColor = '';
    }
  };
  
  // Watch for theme changes to update iframe URL
  watch(isDarkMode, () => {
    // The computed grafanaUrl will automatically update when isDarkMode changes
  });
  
  onMounted(() => {
    updateDarkModeClasses();
  });
  </script>
  
  <style scoped>
  /* Import Font Awesome */
  @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');
  
  /* Main container */
  .app-container {
    width: 100%;
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    background-color: #f8f9fa;
    background-image: linear-gradient(to bottom right, #f8f9fa, #e8f5e9);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  }
  
  .app-container.dark-mode {
    background-color: #1a1a1a;
    background-image: linear-gradient(to bottom right, #1a1a1a, #0d2d0f);
    color: #f0f0f0;
  }
  
  .main-content {
    flex: 1;
    padding: 20px;
    max-width: 100%;
    margin: 0 auto;
    width: 100%;
  }
  
  /* Header */
  .cost-dashboard-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    background-color: #ffffff;
    background-image: linear-gradient(135deg, #ffffff, #f5fff7);
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(16, 188, 59, 0.08);
    margin-bottom: 24px;
    border-left: 4px solid #10BC3B;
    z-index: 10;
  }
  
  .app-container.dark-mode .cost-dashboard-header {
    background-color: #222222;
    background-image: linear-gradient(135deg, #222222, #1a2e1d);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    border-left: 4px solid #10BC3B;
  }
  
  .cost-dashboard-header h2 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: #10BC3B;
    letter-spacing: 0.5px;
  }
  
  .app-container.dark-mode .cost-dashboard-header h2 {
    color: #10BC3B;
  }
  
  /* Dashboard Container */
  .dashboard-container {
    background-color: #ffffff;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
    height: calc(100vh - 150px);
    min-height: 600px;
    position: relative; /* For absolute positioning of overlay */
  }
  
  .app-container.dark-mode .dashboard-container {
    background-color: #222222;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.2);
  }
  
  /* Overlay header to hide Grafana's top heading */
  .overlay-header {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 48px; /* Adjust based on Grafana's header height */
    background-color: #ffffff;
    z-index: 5;
  }
  
  .app-container.dark-mode .overlay-header {
    background-color: #222222;
  }
  
  iframe {
    width: 100%;
    height: 100%;
    border: none;
    /* Negative margin to move the iframe up, hiding the Grafana header under our overlay */
    margin-top: -48px; /* Should match the overlay-header height */
    position: relative;
    z-index: 1;
  }
  
  /* Responsive adjustments */
  @media (max-width: 768px) {
    .cost-dashboard-header {
      flex-direction: column;
      gap: 16px;
      align-items: flex-start;
    }
    
    .dashboard-container {
      height: calc(100vh - 200px);
    }
  }
  </style>
  
 