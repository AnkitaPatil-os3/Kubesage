<script setup lang="ts">
import { useAppStore } from '@/store'

const appStore = useAppStore()
const options = [
  {
    label: 'English',
    value: 'enUS',
  },
  {
    label: '中文',
    value: 'zhCN',
  },
  {
    label: 'Hindi',
    value: 'hiIN',
  },
]
</script>

<template>
  <n-popselect :value="appStore.lang" :options="options" trigger="click" @update:value="appStore.setAppLang">
    <CommonWrapper>
      <icon-park-outline-translate />
    </CommonWrapper>
  </n-popselect>
</template>

<style scoped></style>
