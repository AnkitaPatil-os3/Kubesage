<!-- using this code requeststorgesaccess error and not token sstore but login -->

import type { App } from 'vue';
import { createApp } from 'vue';
import { installRouter } from '@/router';
import { installPinia } from '@/store';
import AppVue from './App.vue';
import AppLoading from './components/common/AppLoading.vue';
import keycloak from '@/plugins/keycloak';

async function setupApp() {
  // Load global loading state
  const appLoading = createApp(AppLoading);

  try {
    // Initialize Keycloak and ensure login if required
    await keycloak.init({ onLoad: 'login-required' });
    appLoading.mount('#appLoading');


    // Create Vue instance
    const app = createApp(AppVue);

    // Provide Keycloak globally so components can access it
    app.provide('keycloak', keycloak);

    // Register Pinia
    await installPinia(app);

    // Register Vue-router
    await installRouter(app);

    // Register other modules/resources
    Object.values(
      import.meta.glob<{ install: (app: App) => void }>('./modules/*.ts', {
        eager: true,
      }),
    ).map(i => app.use(i));

    // Unmount the loading animation
    appLoading.unmount();

    // Mount the app
    app.mount('#app');
  } catch (error) {
    console.error('Keycloak initialization failed:', error);
    appLoading.unmount(); // Ensure the loading screen is removed even on failure
  }
}

setupApp();

#222 in this token store & 

// main.ts
import type { App } from 'vue';
import { createApp } from 'vue';
import { installRouter } from '@/router';
import { installPinia } from '@/store';
import AppVue from './App.vue';
import AppLoading from './components/common/AppLoading.vue';
import keycloak, { initializeKeycloak } from './plugins/keycloak';

async function setupApp() {
  // Show loading animation during initialization
  const appLoading = createApp(AppLoading);
  appLoading.mount('#appLoading');

  // Initialize Keycloak and setup the app only if authenticated
  initializeKeycloak(async () => {
    // If authenticated, create the Vue app
    const app = createApp(AppVue);

    // Provide Keycloak globally for access in components
    app.provide('keycloak', keycloak);

    // Install Pinia and Vue Router
    await installPinia(app);
    await installRouter(app);

    // Unmount the loading animation and mount the app
    appLoading.unmount();
    app.mount('#app');

    // Log confirmation that the app has been mounted
  });
}

setupApp();


