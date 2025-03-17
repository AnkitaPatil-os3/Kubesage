<template>
  <div>
    <!-- Dropdown Section -->
    <div class="dropdown-container">
      <!-- Job Dropdown -->
      <div class="dropdown-item">
        <div class="label-box">Job:</div>
        <n-select v-model="selectedJob" :options="jobOptions" placeholder="Select Job"
          style="width: 200px;" @update:value="onJobSelect"></n-select>
      </div>

      <!-- Host Dropdown -->
      <div class="dropdown-item">
        <div class="label-box">Host:</div>
        <n-select v-model="selectedHost" :options="filteredHostOptions" placeholder="Select Host"
          style="width: 200px;" @update:value="onHostSelect"></n-select>
      </div>
    </div>

    <!-- Gauge Chart Section for CPU Usage and Sys Load -->
    <n-card >
      <div class="panel-row">
        <!-- Panel 1: CPU Usage -->
        <div class="panel-container">
          <div class="panel-title">CPU Busy</div> <!-- Panel Title -->
          <div ref="gaugeChartCpu" class="gauge-chart"></div>
        </div>

        <!-- Panel 2: Sys Load -->
        <div class="panel-container">
          <div class="panel-title">Sys Load</div> <!-- Panel Title -->
          <div ref="gaugeChartSysLoad" class="gauge-chart"></div>
        </div>

        <!-- Panel 3: RAM Load -->
        <div class="panel-container">
          <div class="panel-title">RAM Load</div> <!-- Panel Title -->
          <div ref="gaugeChartRamLoad" class="gauge-chart"></div>
        </div>

        <!-- Panel 4: Root fs Used -->
        <div class="panel-container">
          <div class="panel-title">Root fs Used</div> <!-- Panel Title -->
          <div ref="gaugeChartRootUsed" class="gauge-chart"></div>
        </div>

       
        

        
       
      </div>
    </n-card>

    <!-- 2nd Row: Bar Chart -->
    <n-card>
      <div class="panel-row">
        <div class="panel-container">
          <div class="panel-title">CPU Basic </div>
          <div ref="barChartCpu" class="bar-chart"></div>
        </div>
        <div class="panel-container">
          <!-- <div class="panel-title">CPU Pressure Line Chart</div> -->
          <div ref="lineChartCpu" class="line-chart"></div>
        </div>
        

        <div class="panel-container">
          <div class="panel-title">CPU Cores Count</div> <!-- Panel Title -->
          <div class="core-count-display">{{ cpuCoreCount }}</div> <!-- Display CPU Core Count -->
        </div>

        
      </div>
    </n-card>

    


  </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue';
import * as echarts from 'echarts'; // Import ECharts
import { NSelect, NCard } from 'naive-ui';  // Import Naive UI components
import axios from 'axios'

export default {
  name: 'CpuAndSysLoadGaugeChart',
  components: {
    NSelect,
    NCard,
  },
  setup() {
    const gaugeChartCpu = ref(null);
    const gaugeChartSysLoad = ref(null);
    const gaugeChartRamLoad = ref(null);
    const gaugeChartRootUsed = ref (null);
    const barChartCpu = ref(null); // Bar chart ref for 2nd row

    const lineChartCpu = ref(null);
    const chartInstanceCpupressure = ref(null);

    const cpuPercent = ref(0);
    const memPercent = ref(0);
    const ioPercent = ref(0);

    let chartInstanceCpu = null;
    let chartInstanceSysLoad = null;
    let chartInstanceRamLoad = null;
    let chartInstanceRootLoad = null;
    let chartInstanceBarCpu = null; // Bar chart instance



    const selectedJob = ref(null);   // Selected Job
    const selectedHost = ref(null);  // Selected Host
    const jobOptions = ref([]);      // Options for Jobs
    const hostOptions = ref([]);     // Options for Hosts (All Hosts)
    const filteredHostOptions = ref([]); // Filtered Hosts based on Job
    const cpuCoreCount = ref(0);     // New ref for CPU core count

    // Initialize the ECharts instance
    const initCpuLineChart = () => {
    if (lineChartCpu.value) {
      chartInstanceCpupressure.value = echarts.init(lineChartCpu.value);
    }
  };

    // Fetch pressure data (CPU, memory, IO)
    const fetchData = async () => {
    try {
      const cpuResponse = await axios.get('http://172.16.1.119:9090/api/v1/query?query=irate(node_pressure_cpu_waiting_seconds_total{instance="development-server-ashish",job="integrations/unix"}[5m])');
      const memResponse = await axios.get('http://172.16.1.119:9090/api/v1/query?query=irate(node_pressure_memory_waiting_seconds_total{instance="development-server-ashish",job="integrations/unix"}[5m])');
      const ioResponse = await axios.get('http://172.16.1.119:9090/api/v1/query?query=irate(node_pressure_io_waiting_seconds_total{instance="development-server-ashish",job="integrations/unix"}[5m])');

      if (cpuResponse.data.status === 'success') {
        cpuPercent.value = parseFloat(cpuResponse.data.data.result[0].value[1]);
      }
      if (memResponse.data.status === 'success') {
        memPercent.value = parseFloat(memResponse.data.data.result[0].value[1]);
      }
      if (ioResponse.data.status === 'success') {
        ioPercent.value = parseFloat(ioResponse.data.data.result[0].value[1]);
      }

      // Update the line chart with the fetched data
      updateCpuLineChart([
        { type: 'CPU Pressure', value: cpuPercent.value },
        { type: 'Memory Pressure', value: memPercent.value },
        { type: 'IO Pressure', value: ioPercent.value }
      ]);
    } catch (error) {
      console.error('Error fetching pressure data:', error);
    }
  };

  const updateCpuLineChart = (data) => {
    if (chartInstanceCpupressure.value) {
      const option = {
        title: {
          text: 'CPU Pressure Over Time',
          left: 'center',
          textStyle: {
            color: '#4CAF50',
            fontWeight: 'bold',
            fontSize: 18
          }
        },
        tooltip: {
          trigger: 'axis',
          formatter: '{b}: {c}%'
        },
        xAxis: {
          type: 'category',
          data: data.map(item => item.type),
          axisLabel: {
            rotate: 45,
            color: '#888',
          },
        },
        yAxis: {
          type: 'value',
          axisLabel: {
            formatter: '{value}%',
            color: '#888',
          },
        },
        series: [
          {
            data: data.map(item => item.value),
            type: 'line',
            smooth: true,
            itemStyle: {
              color: '#4CAF50',
            },
            areaStyle: {
              color: 'rgba(76, 175, 80, 0.2)', // Green area under line
            },
          },
        ],
      };
      chartInstanceCpupressure.value.setOption(option);
    } else {
      console.error('chartInstanceCpupressure is not initialized.');
    }
  };

    // Fetch CPU core count data based on the selected host
    const fetchCpuCoreCount = async (host) => {
      try {
        const response = await fetch(`http://172.16.1.119:9090/api/v1/query?query=count(count(node_cpu_seconds_total{instance="${host}"}) by (cpu))`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();

        if (data.status === 'success') {
          const coreCount = parseInt(data.data.result[0].value[1]); // Extract CPU core count value
          cpuCoreCount.value = coreCount; // Update the CPU core count display
        }
      } catch (error) {
        console.error('Error fetching CPU core count data:', error);
      }
    };

    // Fetch CPU data based on the selected host
    const fetchCpuData = async (host) => {
      try {
        const response = await fetch(`http://172.16.1.119:9090/api/v1/query?query=100 * (1 - avg(rate(node_cpu_seconds_total{mode="idle", instance="${host}"}[5m])))`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();

        if (data.status === 'success') {
          const cpuUsage = parseFloat(data.data.result[0].value[1]); // Extract CPU usage value
          updateGauge(chartInstanceCpu, cpuUsage, 'CPU Usage'); // Update CPU gauge chart with the fetched value
        }
      } catch (error) {
        console.error('Error fetching CPU data:', error);
      }
    };

    // Fetch Sys Load data based on the selected host
    const fetchSysLoadData = async (host) => {
      try {
        const response = await fetch(`http://172.16.1.119:9090/api/v1/query?query=scalar(node_load1{instance="${host}"}) * 100 / count(count(node_cpu_seconds_total{instance="${host}"}) by (cpu))`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();

        if (data.status === 'success') {
          const sysLoad = parseFloat(data.data.result[0].value[1]); // Extract Sys Load value
          updateGauge(chartInstanceSysLoad, sysLoad, 'Sys Load'); // Update Sys Load gauge chart with the fetched value
        }
      } catch (error) {
        console.error('Error fetching Sys Load data:', error);
      }
    };

        // Fetch Ram Load data based on the selected host

    const fetchRamData = async (host) => {
      try {
        const response = await fetch(`http://172.16.1.119:9090/api/v1/query?query=((node_memory_MemTotal_bytes{instance="${host}"} - node_memory_MemFree_bytes{instance="${host}"}) / node_memory_MemTotal_bytes{instance="${host}"}) * 100`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();

        if (data.status === 'success') {
          const ramLoad = parseFloat(data.data.result[0].value[1]); // Extract Sys Load value
          updateGauge(chartInstanceRamLoad, ramLoad, 'Ram Load'); // Update Sys Load gauge chart with the fetched value
        }
      } catch (error) {
        console.error('Error fetching Ram Load data:', error);
      }
    };


    // Fetch Root Load data based on the selected host
    const fetchRootLoadData = async (host) => {
      try {
        const response = await fetch(`http://172.16.1.119:9090/api/v1/query?query=100 - ((node_filesystem_avail_bytes{instance="${host}",mountpoint="/",fstype!="rootfs"} * 100) / node_filesystem_size_bytes{instance="${host}",mountpoint="/",fstype!="rootfs"})`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();
        console.log(data)

        if (data.status === 'success') {
          const rootLoad = parseFloat(data.data.result[0].value[1]); // Extract Sys Load value
          updateGauge(chartInstanceRootLoad, rootLoad, 'Root fs Used'); // Update Sys Load gauge chart with the fetched value
        }
      } catch (error) {
        console.error('Error fetching Sys Load data:', error);
      }
    };

    //s
    const fetchCpuBarChartData = async (host) => {
      try {
        const response = await fetch(`http://172.16.1.119:9090/api/v1/query?query=sum(irate(node_cpu_seconds_total{instance="${host}", mode="system"}[5m])) / scalar(count(count(node_cpu_seconds_total{instance="${host}"}) by (cpu)))`);
        const data = await response.json();

        if (data.status === 'success') {
          const cpuUsageData = data.data.result.map((item) => ({
            cpu: `CPU ${item.metric.cpu}`,
            value: item.value[1],
          }));
          updateBarChart(chartInstanceBarCpu, cpuUsageData);
        }
      } catch (error) {
        console.error('Error fetching CPU bar chart data:', error);
      }
    };

    const updateBarChart = (chartInstance, data) => {
      const option = {
        xAxis: {
          type: 'category',
          data: data.map((item) => item.cpu), // CPU cores
        },
        yAxis: {
          type: 'value',
        },
        series: [
          {
            data: data.map((item) => item.value), // CPU usage values
            type: 'bar',
          },
        ],
      };
      chartInstance.setOption(option);
    };



    // Fetch job and host data for the dropdowns
    const fetchJobAndHostData = async () => {
      try {
        const response = await fetch('http://172.16.1.119:9090/api/v1/query?query=node_uname_info');
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();

        if (data.status === 'success') {
          const uniqueJobs = new Set();
          const hosts = [];

          data.data.result.forEach(item => {
            uniqueJobs.add(item.metric.job); // Add Job to Set
            hosts.push({ label: item.metric.instance, value: item.metric.instance, job: item.metric.job }); // Add Host with Job reference
          });

          jobOptions.value = Array.from(uniqueJobs).map(job => ({
            label: job,
            value: job,
          }));

          hostOptions.value = hosts;
        }
      } catch (error) {
        console.error('Error fetching job and host data:', error);
      }
    };

    // Create Gauge Chart for both CPU and Sys Load
    const createGauge = (chartInstance, name) => {
      const option = {
        series: [
          {
            type: 'gauge',
            detail: {
              formatter: '{value}%',   // Show percentage
              fontSize: 20,
              color: '#008000', // green color
            },
            axisLine: {
              lineStyle: {
                color: [
                  [0.3, '#67e0e3'],   // Blue for 0-30%
                  [0.7, '#37a2da'],   // Light blue for 30-70%
                  [1, '#fd666d'],     // Red for 70-100%
                ],
                width: 20,
              },
            },
            pointer: {
              width: 5,              // Pointer width
              length: '60%',
            },
            data: [{ value: 0, name }],
          },
        ],
      };
      chartInstance.setOption(option);
    };

    // Update Gauge Chart with the new value
    const updateGauge = (chartInstance, value, name) => {
      chartInstance.setOption({
        series: [
          {
            data: [{ value: value.toFixed(2), name }],
          },
        ],
      });
    };

    // Filter hosts based on the selected job
    const onJobSelect = (job) => {
      filteredHostOptions.value = hostOptions.value.filter(host => host.job === job); // Filter hosts by selected job
      selectedHost.value = null; // Reset selected host when job changes
    };

    // Fetch data for both CPU and Sys Load when a host is selected
    const onHostSelect = (host) => {
      fetchCpuData(host);
      fetchSysLoadData(host);
      fetchRamData(host);
      fetchRootLoadData(host);
      fetchCpuBarChartData(host); 
      fetchCpuCoreCount(host); // Fetch CPU core count when host is selected
      // fetchData(host);

    };
    onMounted(() => {
      chartInstanceCpu = echarts.init(gaugeChartCpu.value);   // Initialize CPU gauge chart
      chartInstanceSysLoad = echarts.init(gaugeChartSysLoad.value); // Initialize Sys Load gauge chart
      chartInstanceRamLoad = echarts.init(gaugeChartRamLoad.value); // Initialize Sys Load gauge chart
      chartInstanceRootLoad = echarts.init(gaugeChartRootUsed.value); // Initialize Sys Load gauge chart
      chartInstanceBarCpu = echarts.init(barChartCpu.value); // Initialize bar
      
      createGauge(chartInstanceCpu, '');             // Create the initial CPU gauge chart
      createGauge(chartInstanceSysLoad, '');          // Create the initial Sys Load gauge chart
      createGauge(chartInstanceRamLoad, '');          // Create the initial Sys Load gauge chart

      createGauge(chartInstanceRootLoad, '');          // Create the initial Sys Load gauge chart
      



      fetchJobAndHostData();
      initCpuLineChart();
      fetchData();

    });

    return {
      gaugeChartCpu,
      gaugeChartSysLoad,
      gaugeChartRamLoad,
      gaugeChartRootUsed,
      barChartCpu, // Return ref for bar chart
      cpuCoreCount, // Expose cpuCoreCount to template
      

      selectedJob,
      selectedHost,
      jobOptions,
      filteredHostOptions,
      onJobSelect,
      onHostSelect,

      lineChartCpu,
      cpuPercent,
      memPercent,
      ioPercent,
      fetchData, 
    };
  },
};
</script>

<style scoped>
/* Dropdown container styling */
.dropdown-container {
  display: flex;
  margin-bottom: 20px;
  gap: 20px;
}
.time-series-chart {
  width: 100%;
  height: 300px;
  margin: 0 auto;
}

/* Individual dropdown-item */
.dropdown-item {
  display: flex;
  align-items: center;
}

/* Label box styling */
.label-box {
  width: 50px;
  text-align: right;
  margin-right: 10px;
  padding: 5px;
  font-weight: bold;
}
.bar-chart {
  width: 100%;
  height: 300px;
  margin: 0 auto;
}

.core-count-display {
  font-size: 60px;
  color: #0c6e14; /* Green color for text */
  text-align: center;
  margin-top: 30px;
  font-weight: bold;
  background-color: #eff0f5; /* Green background for square */
  height: 220px; /* Equal height */
  width: 220px; /* Equal width */
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  border-radius: 10px; /* Optional: Add border-radius for smooth edges */
  margin-left: 180px;
}


/* Chart container */
.chart-container {
  width: 400px;
  height: 300px;
}

/* Panel row layout */
.panel-row {
  display: flex;
  /* justify-content: space-between; */
  /* gap: 20px; */
}

/* Panel container */
.panel-container {
  flex: 1;  /* Allow panels to be of equal size */
  min-width: 250px; /* Set a minimum width so panels are not too small */
  height: 300px;    /* Set height for the charts */
  text-align:center;
}

.line-chart {
  width: 100%;
  height: 300px;
}

.pressure-values {
  display: flex;
  justify-content: space-around;
  width: 100%;
  margin-bottom: 10px;
}

.gauge-chart {
  width: 100%;
  height: 100%;
  /* margin-bottom: 10px; */
;}

/* Row layout for the charts */
.chart-row {
  display: flex;
  justify-content: space-between;
  /* gap: 20px; */
}
.panel-title {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 10px;
}


</style>