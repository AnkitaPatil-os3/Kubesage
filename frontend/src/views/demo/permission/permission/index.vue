<template>
  <div class="card-container">
    <n-card title="Postgres" hoverable>
      DB
    </n-card>
    <n-card title="MYSQL" hoverable>
      DB
    </n-card>
    <n-card title="Oracle" hoverable>
      DB
    </n-card>
  </div>
</template>

<style scoped>
.card-container {
  display: flex;
  gap: 10px; /* Cards ke beech mein thoda gap ke liye */
}

.n-card {
  max-width: 300px;
  max-height: 150px;
}
</style>
