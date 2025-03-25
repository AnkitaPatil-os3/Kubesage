<template>
    <n-config-provider>
        <n-layout>
            <n-layout-header class="dashboard-header">
                <div class="header-content">
                    <h2 class="dashboard-title">Backend Provider Management</h2>
                    <n-button type="primary" @click="openModal">
                        <template #icon>
                            <n-icon><plus-icon /></n-icon>
                        </template>
                        Add New Provider
                    </n-button>
                </div>
            </n-layout-header>
 
            <n-layout-content class="provider-dashboard">
                <n-alert v-if="showNotification" :type="notificationType" :title="notificationMessage" closable
                    @close="showNotification = false" />
 
                <n-card class="provider-table-container">
                    <n-data-table :columns="columns" :data="activeList" :pagination="pagination" :bordered="false" />
                </n-card>
 
                <!-- Updated Modal for Adding New Provider -->
                <n-modal v-model:show="showModal" title="Add Provider" preset="dialog">
                    <n-form :model="formData">
                        <n-form-item label="Provider Name">
                            <n-input v-model:value="formData.backend_type" placeholder="Enter provider name" />
                        </n-form-item>
                        <n-form-item label="Base URL">
                            <n-input v-model:value="formData.baseurl" placeholder="Enter base URL" />
                        </n-form-item>
                        <n-form-item label="Model">
                            <n-input v-model:value="formData.model" placeholder="Enter model" />
                        </n-form-item>
                    </n-form>
                    <template #action>
                        <n-space>
                            <n-button @click="closeModal">Cancel</n-button>
                            <n-button type="primary" @click="handleConnect">Connect</n-button>
                        </n-space>
                    </template>
                </n-modal>
            </n-layout-content>
        </n-layout>
    </n-config-provider>
</template>
 
<script setup>
import { ref, onMounted, h, nextTick } from 'vue';
import axios from 'axios';
import { NConfigProvider, NLayout, NLayoutHeader, NLayoutContent, NButton, NIcon, NAlert, NCard, NDataTable, NModal, NForm, NFormItem, NInput, NSpace } from 'naive-ui';
import { Add as PlusIcon } from '@vicons/ionicons5';
 
const host = 'https://10.0.34.129:8008/';
const showModal = ref(false);
const showNotification = ref(false);
const notificationMessage = ref('');
const notificationType = ref('success');
const activeList = ref([]); // Removed hardcoded data
const defaultProvider = ref('');
 
const formData = ref({
    backend_type: '',
    name: '',
    engine: 'n_user_db',
    api_key : 'nfkshdkfkdnkjdsnfksfjshfsdhk',
    baseurl: '',
    model: '',
    maxtokens: 2048,
    temperature: 0.7,
    topp: 0.5,
    is_default : true
});
 
const columns = [
    {
        title: 'Provider Name',
        key: 'name',
    },
    {
        title: 'Status',
        key: 'status',
        render: (row) => {
            return h(
                'span',
                { class: isDefaultProvider(row.name) ? 'status-badge active' : 'status-badge' },
                isDefaultProvider(row.name) ? 'Default' : 'Active'
            );
        },
    },
    {
        title: 'Actions',
        key: 'actions',
        render: (row) => {
            return h(
                'div',
                { class: 'actions-cell' },
                [
                    h(
                        NButton,
                        {
                            type: 'primary',
                            disabled: isDefaultProvider(row.name),
                            onClick: () => setDefaultProvider(row.name),
                            class: 'action-button',
                        },
                        'Set Default'
                    ),
                    h(
                        NButton,
                        {
                            type: 'error',
                            onClick: () => deleteProvider(row.name),
                            class: 'action-button',
                        },
                        'Remove'
                    ),
                ]
            );
        },
    },
];
 
const pagination = ref({
    pageSize: 10,
});
 
const openModal = () => {
    showModal.value = true;
};
 
// Get auth token from localStorage
const getAuthHeaders = () => {
    try {
        const token = JSON.parse(localStorage.getItem('accessToken')).value;
        return { Authorization: `Bearer ${token}` };
    } catch (error) {
        console.error('Authentication error. Please login again.');
        return {};
    }
};
 
const showNotificationMessage = (message, type = 'success') => {
    notificationMessage.value = message;
    notificationType.value = type;
    showNotification.value = true;
    setTimeout(() => {
        showNotification.value = false;
    }, 3000);
};

// Watch for changes in `backend_type` and update `name` automatically
watch(() => formData.value.backend_type, (newValue) => {
    formData.value.name = newValue;
});
 
const handleConnect = async () => {
    console.log("formData.value," , formData.value,);
    
    try {
        const response = await axios.post(`${host}backends`, formData.value, {
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            }
        });
        if (response.status === 200) {
            showNotificationMessage('Provider connected successfully!');
            closeModal();
            await nextTick();
            fetchProviders();
        }
    } catch (error) {
        showNotificationMessage(error.response?.data?.detail || 'Connection failed', 'error');
    }
};
 
const setDefaultProvider = async (provider) => {
    try {
        const response = await axios.post(`${host}/backends/${provider}/default`, null, {
            headers: getAuthHeaders(),
        });
        if (response.status === 200) {
            defaultProvider.value = provider;
            showNotificationMessage(`${provider} set as default provider`);
            await nextTick();
            fetchProviders();
        }
    } catch (error) {
        console.error('Error setting default provider:', error);
        showNotificationMessage('Failed to set default provider', 'error');
    }
};
 
const deleteProvider = async (provider) => {
    try {
        const response = await axios.delete(`${host}/backends/${provider}`, {
            headers: getAuthHeaders(),
        });
        if (response.status === 200) {
            showNotificationMessage('Provider removed successfully!');
            await nextTick();
            fetchProviders();
        }
    } catch (error) {
        console.error('Error removing provider:', error);
        showNotificationMessage('Failed to remove provider', 'error');
    }
};
 
const fetchProviders = async () => {
    try {
        const response = await axios.get(`${host}backends/`, {
            headers: getAuthHeaders(),
        });
        activeList.value = response.data.map(provider => ({ name: provider.name }));
        if (response.data.length > 0) {
            defaultProvider.value = response.data.find(p => p.is_default)?.name || '';
        }
    } catch (error) {
        showNotificationMessage('Failed to fetch providers', 'error');
    }
};

 
const isDefaultProvider = (provider) => {
    return defaultProvider.value === provider;
};
 
const closeModal = async() => {
    showModal.value = false;
    await nextTick();
    formData.value = {
        backend_type: '',
        name: '',
        engine: 'n_user_db',
        api_key : 'nfkshdkfkdnkjdsnfksfjshfsdhk',
        baseurl: '',
        model: '',
        maxtokens: 2048,
        temperature: 0.7,
        topp: 0.5,
        is_default : true
    };
};
 
onMounted(() => {
    fetchProviders();
});
</script>
 
<style scoped>
.provider-dashboard {
    padding: 24px;
    background-color: #f8fafc;
    min-height: 100vh;
}
 
.dashboard-header {
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    margin-bottom: 24px;
}
 
.header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
 
.dashboard-title {
    font-size: 24px;
    font-weight: 600;
    color: #2d3748;
    margin: 0;
}
 
.status-badge {
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 0.875rem;
}
 
.status-badge.active {
    background: #dcfce7;
    color: #16a34a;
}
 
.actions-cell {
    display: flex;
    gap: 16px; /* Increased gap between buttons */
    justify-content: flex-start;
    align-items: center;
    min-width: 200px;
}
 
.action-button {
    margin: 0; /* Ensure buttons have no extra margin */
}
 
.no-data {
    text-align: center;
    color: #64748b;
    padding: 24px;
}
 
.custom-modal {
    width: 400px;
    height: 400px;
    margin: 0 auto;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    padding: 16px;
    background-color: white;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
 
.modal-form {
    display: flex;
    flex-direction: column;
    gap: 12px;
}
 
.n-form-item {
    margin-bottom: 0;
}
 
.n-input {
    width: 100%;
}
 
.n-space {
    margin-top: 12px;
}
</style>
 