<template>
  <div class="pr-5 iframe-container">
    <!-- Left and right overlays to hide headers -->
    <div class="overlay-text">
      
    
      <div class="heading-text p-7">
        <n-text class="text-lg font-bold  ">Docker Dashboard</n-text>
      </div>
    </div>
    <iframe :src="iframeSrc" width="100%" height="100%" frameborder="0" allowfullscreen
      class="m-5 dashboard-iframe"></iframe>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";
import { useOsTheme } from "naive-ui";
import { useRouter } from "vue-router";

const iframeSrc = ref("");
const router = useRouter();

function getIframeSrc(isDark) {
  const baseSrc = `https://10.0.34.212:3000/d/4dMaCsRZz/docker-monitoring?var-interval=$__auto&from=now-30m&to=now&timezone=browser&var-job=integrations%2Fcadvisor&var-node=docker-monitor&refresh=10s&theme=light
`;

  return baseSrc;
}

const osTheme = useOsTheme();
iframeSrc.value = getIframeSrc(osTheme.value === "dark");

watch(
  () => osTheme.value,
  (newTheme) => {
    iframeSrc.value = getIframeSrc(newTheme === "dark");
  }
);

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

  background-color: white;
  z-index: 2;
}

.heading-text {
  display: flex;
  justify-content: center;
  /* Center horizontally */
  align-items: center;
  /* Center vertically */
  text-align: center;
}

.dark-overlay {
  position: absolute;
  top: 0%;
  left: 0%;
  width: 99.5%;
  height: 9.5%;
  text-align: center;
  color: white;
  background-color: rgb(15, 15, 15);
  padding: 10px;
  border-radius: 8px;
  z-index: 2;
}

.iframe-container {
  position: relative;
}

/* Back button styles */
.back-button {
  position: absolute;
  top: 20px;
  /* Adjust the position as needed */
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

.back-arrow {
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 5px solid white;
  margin-right: 8px;
  /* Space between the icon and text */
}

.back-button:hover {
  background-color: #0056b3;
}
</style>