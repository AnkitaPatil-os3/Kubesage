


export const usePluginsStore = defineStore('plugins', {
  state: () => ({
    activated_plugins: ['SOC Wazuh'] as string[],
  }),
  actions: {
    activatePlugin(pluginName: string) {
      if (!this.activated_plugins.includes(pluginName)) {
        this.activated_plugins.push(pluginName);
      }
    },
    deactivatePlugin(pluginName: string) {
      const index = this.activated_plugins.indexOf(pluginName);
      if (index !== -1) {
        this.activated_plugins.splice(index, 1);
      }
    },
  },
});


