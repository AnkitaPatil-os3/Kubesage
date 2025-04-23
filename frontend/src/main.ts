import { createApp } from 'vue';
import { installPinia } from '@/store';
import { installRouter } from '@/router';
import AppVue from './App.vue';
import AppLoading from './components/common/AppLoading.vue';
// import keycloak, { initializeKeycloak } from './plugins/keycloak';
import { App as VueApp } from 'vue';

async function setupApp() {
  // Show loading animation during initialization
  const appLoading = createApp(AppLoading);
  appLoading.mount('#appLoading'); // Ensure you have an element with id="appLoading" in your HTML

  // Initialize Keycloak and setup the app only if authenticated
  try {
    // If authenticated, create the Vue app
    const app = createApp(AppVue);

    // Provide Keycloak globally for access in components
    // app.provide('keycloak', keycloak);

    // Install Pinia and Vue Router (ensure they are installed in the right order)
    await installPinia(app); // Pinia first, since it's state management
    await installRouter(app); // Then router, to handle routes

    // Dynamically import and install modules
    Object.values(
      import.meta.glob<{ install: (app: VueApp) => void }>('./modules/*.ts', {
        eager: true,
      }),
    ).map(i => i.install(app));

    // Unmount the loading animation and mount the app
    appLoading.unmount(); // Ensure loading component is unmounted before mounting main app
    app.mount('#app'); // Mount the main Vue app

    // Optionally log confirmation that the app has been mounted
    console.log('Vue app has been mounted successfully!');
  } catch (error) {
    console.error('Failed to initialize app:', error);
    appLoading.unmount();
  }
}

setupApp();
