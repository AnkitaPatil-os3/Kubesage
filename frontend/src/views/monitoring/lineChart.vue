<template>
  <div class="chart-container">
    <h4 class="chart-title">CPU BUSY</h4>
    <canvas ref="myCanvas" class="chart-canvas"></canvas>
  </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue';
import {
  Chart,
  ArcElement,
  Tooltip,
  Legend,
  PieController,
} from 'chart.js';

// Register the necessary components for a pie chart
Chart.register(ArcElement, Tooltip, Legend, PieController);

export default {
  name: 'PieChart',
  props: {
    chartData: {
      type: Object,
      required: true,
    },
  },
  setup(props) {
    const myCanvas = ref(null);
    let chartInstance = null;

    const createChart = () => {
      const ctx = myCanvas.value.getContext('2d');
      if (chartInstance) {
        chartInstance.destroy(); // Destroy the old chart instance if it exists
      }
      chartInstance = new Chart(ctx, {
        type: 'pie',
        data: {
          labels: props.chartData.labels,
          datasets: [
            {
              data: props.chartData.datasets[0].data,
              backgroundColor: [
                'rgba(255, 99, 132, 0.8)', // Red
                'rgba(54, 162, 235, 0.8)', // Blue
                'rgba(75, 192, 192, 0.8)', // Green
              ],
              borderColor: '#000', // Black border
              borderWidth: 2, // Slightly thicker border
            },
          ],
        },
        options: {
          responsive: true,
          plugins: {
            tooltip: {
              backgroundColor: 'rgba(255, 255, 255, 0.9)', // White tooltip background
              titleColor: '#000', // Black text in tooltip
              bodyColor: '#000', // Black text for body
            },
            legend: {
              display: true,
              position: 'top',
              labels: {
                color: '#333333', // Dark legend text
                font: {
                  size: 14,
                  family: 'Arial, sans-serif',
                  weight: 'bold',
                },
                padding: 20,
              },
            },
          },
        },
      });
    };

    onMounted(() => {
      createChart();
    });

    watch(() => props.chartData, createChart);

    return {
      myCanvas,
    };
  },
};
</script>

<style scoped>
.chart-container {
  max-width: 600px;
  margin: auto;
  padding: 20px;
  border-radius: 8px;
  background-color: #ffffff; /* Light background for the container */
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.5); /* Darker shadow */
}

.chart-title {
  text-align: center;
  font-size: 24px;
  color: #333333; /* Dark title color */
  margin-bottom: 20px;
  font-family: 'Arial', sans-serif;
}

.chart-canvas {
  height: 300px;
  background: radial-gradient(circle, rgba(240, 240, 240, 1) 0%, rgba(220, 220, 220, 1) 100%);
  border: 1px solid rgba(0, 0, 0, 0.1); /* Subtle dark border */
  border-radius: 10px; /* Rounded corners for the chart canvas */
}
</style>
