<template>
    <n-card title="Kubeconfig Management" class="p-4 shadow-md rounded-2xl">
        <n-upload :action="uploadUrl" :headers="headers" :on-success="handleUploadSuccess" :on-error="handleUploadError"
            directory-dnd :max="1" :show-file-list="false">
            <n-upload-dragger>
                <n-icon :component="UploadCloudIcon" size="48" color="#409EFF" />
                <div style="font-size: 16px; margin-top: 10px;">Click, browse, or drag files to upload</div>
                <div style="color: #888; margin-top: 4px;">Only kubeconfig files are allowed</div>
            </n-upload-dragger>
        </n-upload>

        <n-data-table :columns="columns" :data="tableData" :loading="loading" class="mt-6" bordered striped>
            <template #action="{ row }">
                <n-space>
                    <n-button size="small" type="success" @click="activateKubeconfig(row.filename)">Activate</n-button>
                    <n-button size="small" type="warning" @click="deactivateKubeconfig(row.filename)">Deactivate</n-button>
                    <n-button size="small" type="error" @click="deleteKubeconfig(row.filename)">Delete</n-button>
                </n-space>
            </template>
        </n-data-table>

        <div class="mt-4" v-if="activeKubeconfig">
            <n-button type="primary" @click="installOperator">Install Operator</n-button>
        </div>
    </n-card>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useMessage } from 'naive-ui';
import { CloudUploadOutline as UploadCloudIcon } from '@vicons/ionicons5';

const message = useMessage();
const tableData = ref([]);
const activeKubeconfig = ref(null);
const loading = ref(false);
const uploadUrl = 'https://10.0.34.129:8001/kubeconfig/upload';
const token = JSON.parse(localStorage.getItem('accessToken')).value;
const headers = { Authorization: `Bearer ${token}` };

// Updated columns configuration to show cluster_name instead of filename
const columns = [
    { title: 'S.No.', key: 'serial', render: (row, index) => index + 1 },
    { title: 'Cluster Name', key: 'cluster_name' }, // Changed from 'filename' to 'cluster_name'
    { title: 'Actions', key: 'action' },
];

const fetchKubeconfigs = async () => {
    loading.value = true;
    try {
        const response = await fetch('https://10.0.34.129:8001/kubeconfig/list', { headers });
        const data = await response.json();
        tableData.value = data.kubeconfigs;
        console.log('Fetched Kubeconfigs:', data.kubeconfigs);  // Debug log
        activeKubeconfig.value = data.active_kubeconfig || null;
    } catch (error) {
        message.error('Failed to fetch kubeconfigs');
    } finally {
        loading.value = false;
    }
};

const handleUploadSuccess = (response) => {
    message.success('File uploaded successfully');
    console.log('Upload Success:', response);  // Debug log
    fetchKubeconfigs();
};

const handleUploadError = (error) => {
    message.error('File upload failed');
    console.error('Upload Error:', error);  // Debug log
};

const activateKubeconfig = async (filename) => {
    console.log('Activating Kubeconfig:', filename); // Log the filename being activated
    try {
        await fetch(`https://10.0.34.129:8001/kubeconfig/activate/${filename}`, { method: 'PUT', headers });
        message.success(`${filename} activated`);
        fetchKubeconfigs();
    } catch (error) {
        message.error('Activation failed');
    }
};

const deactivateKubeconfig = async (filename) => {
    try {
        await fetch(`https://10.0.34.129:8001/kubeconfig/deactivate/${filename}`, { method: 'PUT', headers });
        message.success(`${filename} deactivated`);
        fetchKubeconfigs();
    } catch (error) {
        message.error('Deactivation failed');
    }
};

const deleteKubeconfig = async (filename) => {
    try {
        await fetch(`https://10.0.34.129:8001/kubeconfig/remove?filename=${filename}`, { method: 'DELETE', headers });
        message.success(`${filename} deleted`);
        fetchKubeconfigs();
    } catch (error) {
        message.error('Delete failed');
    }
};

const installOperator = async () => {
    try {
        await fetch('https://10.0.34.129:8001/kubeconfig/install-operator', { method: 'POST', headers });
        message.success('Operator installed successfully');
    } catch (error) {
        message.error('Operator installation failed');
    }
};

onMounted(fetchKubeconfigs);
</script>

<style scoped>
.n-upload-dragger {
    padding: 30px;
    border: 2px dashed #409eff;
    border-radius: 16px;
    cursor: pointer;
    background-color: #f9fbff;
    text-align: center;
}
</style>
