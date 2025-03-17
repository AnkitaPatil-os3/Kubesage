<template>
    <div class="dashboard-container">

        <!-- Linux Dashboard Card -->
        <n-card title="Linux Dashboard" hoverable>
            <div class="iframe-container my-3">
                <!-- Iframes displayed in a single row -->
                <iframe :src="getLinuxIframeSrc" width="100%" height="200" frameborder="0"></iframe>
                <iframe :src="getLinuxIframeSrc2" width="100%" height="200" frameborder="0"></iframe>
                <iframe :src="getLinuxIframeSrc3" width="100%" height="200" frameborder="0"></iframe>
            </div>
            <n-button @click="goToLinuxDashboard">See More</n-button>
        </n-card>

        <!-- Windows Dashboard Card -->
        <n-card title="Windows Dashboard" hoverable>
            <div class="iframe-container my-3">
                <!-- Iframes displayed in a single row -->
                <iframe :src="getWindowsIframeSrc1" width="100%" height="200" frameborder="0"></iframe>
                <iframe :src="getWindowsIframeSrc2" width="100%" height="200" frameborder="0"></iframe>
                <iframe :src="getWindowsIframeSrc3" width="100%" height="200" frameborder="0"></iframe>
            </div>
            <n-button @click="goToWindowsDashboard">See More</n-button>
        </n-card>

        <!-- Theme Toggle Button -->
        <n-button @click="toggleTheme" class="theme-toggle-button">
            Toggle Theme (Current: {{ theme }})
        </n-button>
    </div>
</template>

<script setup>
import { ref, computed, watchEffect } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();

// Reactive state for the iframe URLs
const iframeSrc = ref("");
// Computed property to read dark mode state dynamically from localStorage
const isDark = computed(() => {
    return localStorage.getItem("vueuse-color-scheme") === "dark";
});
// const theme = ref(localStorage.getItem("vueuse-color-scheme") || "light");
let theme = isDark.value ? "dark" : "light";

// Computed properties for iframe URLs based on theme
const getLinuxIframeSrc = computed(() => {
    return `https://10.0.34.212:3000/d-solo/rYdddlPWk/node-exporter-full?from=1734584891062&to=1734671291062&timezone=browser&var-datasource=fe4eeqvcnhce8a&var-job=integrations%2Fnode_exporter&var-node=vscode&var-diskdevices=%5Ba-z%5D%2B%7Cnvme%5B0-9%5D%2Bn%5B0-9%5D%2B%7Cmmcblk%5B0-9%5D%2B&refresh=1m&orgId=1&theme=${theme}&panelId=323&__feature.dashboardSceneSolo`;
});
const getLinuxIframeSrc2 = computed(() => {
    return `https://10.0.34.212:3000/d-solo/rYdddlPWk/node-exporter-full?from=1734584951114&to=1734671351115&timezone=browser&var-datasource=fe4eeqvcnhce8a&var-job=integrations%2Fnode_exporter&var-node=vscode&var-diskdevices=%5Ba-z%5D%2B%7Cnvme%5B0-9%5D%2Bn%5B0-9%5D%2B%7Cmmcblk%5B0-9%5D%2B&refresh=1m&orgId=1&theme=${theme}&panelId=20&__feature.dashboardSceneSolo`;
});
const getLinuxIframeSrc3 = computed(() => {
    return `https://10.0.34.212:3000/d-solo/rYdddlPWk/node-exporter-full?from=1734585011115&to=1734671411115&timezone=browser&var-datasource=fe4eeqvcnhce8a&var-job=integrations%2Fnode_exporter&var-node=vscode&var-diskdevices=%5Ba-z%5D%2B%7Cnvme%5B0-9%5D%2Bn%5B0-9%5D%2B%7Cmmcblk%5B0-9%5D%2B&refresh=1m&orgId=1&theme=${theme}&panelId=16&__feature.dashboardSceneSolo`;
});

const getWindowsIframeSrc1 = computed(() => {
    return `https://10.0.34.212:3000/d-solo/Kdh0OoSG/windows-exporter-dashboard?from=1734919888160&to=1734930688160&var-job=&var-hostname=$__all&var-instance=&var-show_hostname=&orgId=1&theme=${theme}&panelId=19&__feature.dashboardSceneSolo`;
});
const getWindowsIframeSrc2 = computed(() => {
    return `https://10.0.34.212:3000/d-solo/Kdh0OoSG/windows-exporter-dashboard?from=1734919888160&to=1734930688160&var-job=&var-hostname=$__all&var-instance=&var-show_hostname=&orgId=1&theme=${theme}&panelId=21&__feature.dashboardSceneSolo`;
});
const getWindowsIframeSrc3 = computed(() => {
    return `https://10.0.34.212:3000/d-solo/rYdddlPWk/node-exporter-full?from=1734585011115&to=1734671411115&timezone=browser&var-datasource=fe4eeqvcnhce8a&var-job=integrations%2Fnode_exporter&var-node=vscode&var-diskdevices=%5Ba-z%5D%2B%7Cnvme%5B0-9%5D%2Bn%5B0-9%5D%2B%7Cmmcblk%5B0-9%5D%2B&refresh=1m&orgId=1&theme=${theme}&panelId=16&__feature.dashboardSceneSolo`;
});

// Method to navigate to the Linux dashboard page
function goToLinuxDashboard() {
    router.push("/monitoring/linux");
}

// Method to navigate to the Windows dashboard page
function goToWindowsDashboard() {
    router.push("/monitoring/windows");
}

// Method to toggle the theme between light and dark, and save to localStorage
function toggleTheme() {
    theme = theme === "light" ? "dark" : "light";
    localStorage.setItem("vueuse-color-scheme", theme); // Save the theme to localStorage
}
</script>

<style scoped>
.dashboard-container {
    display: flex;
    gap: 20px;
    /* Gap between cards */
    flex-wrap: wrap;
    /* Allow cards to wrap if screen size is smaller */
}

.n-card {
    max-width: 45%;
    height: 50%;
    width: 100%;
    /* Make card responsive */
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    margin-bottom: 20px;
}

.iframe-container {
    display: flex;
    gap: 10px;
    /* Space between iframes */
    overflow-x: auto;
    /* Enable horizontal scrolling if the iframes overflow */
}

iframe {
    flex-shrink: 0;
    /* Prevent iframes from shrinking */
    width: 32%;
    /* Each iframe takes up 1/3rd of the card width */
    height: 200px;
    /* Set a fixed height for the iframes */
    border: none;
    /* Remove iframe borders */
}

.n-button {
    margin-top: 10px;
    align-self: flex-start;
    /* Align button to the left inside the card */
}

/* Add styles for the theme toggle button */
.theme-toggle-button {
    margin-top: 20px;
    align-self: center;
}
</style>