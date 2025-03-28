<template>
    <n-config-provider>
        <n-layout>
            <n-layout-header class="dashboard-header">
                <div class="header-content">
                    <h2 class="dashboard-title">Backend Management</h2>
                    <n-button type="primary" @click="openModal">
                        <template #icon>
                            <n-icon><plus-icon /></n-icon>
                        </template>
                        Add New Backend
                    </n-button>
                </div>
            </n-layout-header>

            <n-layout-content class="backend-dashboard">
                <n-alert v-if="showNotification" :type="notificationType" :title="notificationMessage" closable
                    @close="showNotification = false" />

                <n-card class="backend-table-container">
                    <n-data-table :columns="columns" :data="activeList" :pagination="pagination" :bordered="false" />
                </n-card>

                <!-- Modal for Adding New Backend -->
                <n-modal v-model:show="showModal" title="Add Backend" preset="dialog" class="custom-modal">
                    <n-form :model="formData">
                        <n-form-item label="Provider Name" required>
                            <n-input v-model:value="formData.backend_type" placeholder="Enter your provider name" 
                            @update:value="formData.name = formData.backend_type"
                            />
                        </n-form-item>
                        
                        <n-form-item label="Base URL" required>
                            <n-input v-model:value="formData.base_url" placeholder="Enter base URL (optional)" />
                        </n-form-item>
                        <n-form-item label="Model" required>
                            <n-input v-model:value="formData.model" placeholder="Enter model (optional)" />
                        </n-form-item>
                        <n-form-item label="API Key" required>
                            <n-input v-model:value="formData.api_key" placeholder="Enter API key (if required)"
                                type="password" show-password-toggle />
                        </n-form-item>

                        <n-form-item label="Set as default">
                            <n-switch v-model:value="formData.is_default" />
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
import { ref, onMounted, h } from 'vue';
import axios from 'axios';
import { watch } from 'vue';

import {
    NConfigProvider, NLayout, NLayoutHeader, NLayoutContent, NButton, NIcon,
    NAlert, NCard, NDataTable, NModal, NForm, NFormItem, NInput, NSpace, NSelect, NSwitch
} from 'naive-ui';
import { Add as PlusIcon } from '@vicons/ionicons5';

const host = 'https://10.0.34.129:8003/';
const showModal = ref(false);
const showNotification = ref(false);
const notificationMessage = ref('');
const notificationType = ref('success');
const activeList = ref([]);


const formData = ref({
    backend_type: '',
    name: '',
    engine: 'K8sEngine',
    api_key: '',
    base_url: '',
    model: '',
    maxtokens: 2048,
    temperature: 0.7,
    topp: 0.5,
    is_default: false
});


watch(() => formData.value.backend_type, (newName) => {
    formData.value.name = newName;
});

const columns = [
    {
        title: 'Backend Type',
        key: 'backend_name',
    },
    {
        title: 'Model',
        key: 'model',
    },
    {
        title: 'Status',
        key: 'status',
        render: (row) => {
            return h(
                'span',
                {
                    class: row.is_default ? 'status-badge active' : 'status-badge',
                    style: {
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px'
                    }
                },
                [
                    h('span', {
                        class: 'status-dot',
                        style: {
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%',
                            backgroundColor: row.is_default ? '#10b981' : '#3b82f6'
                        }
                    }),
                    row.is_default ? 'Default' : 'Active'
                ]
            );
        },
    },
    {
        title: 'Actions',
        key: 'actions',
        render: (row) => {
            return h(
                'div',
                {
                    class: 'actions-cell',
                    style: {
                        display: 'flex',
                        gap: '8px',
                        alignItems: 'center'
                    }
                },
                [
                    h(
                        NButton,
                        {
                            type: row.is_default ? 'success' : 'primary',
                            disabled: row.is_default,
                            onClick: () => setDefaultBackend(row.backend_name),
                            class: 'action-button',
                            size: 'small',
                            secondary: !row.is_default,
                            ghost: row.is_default
                        },
                        {
                            default: () => row.is_default ? 'Default' : 'Set Default',
                            icon: row.is_default ? h(NIcon, null, h('i', { class: 'fas fa-check-circle' })) : null
                        }
                    ),
                    h(
                        NButton,
                        {
                            type: 'error',
                            onClick: () => deleteBackend(row.backend_name),
                            class: 'action-button',
                            size: 'small',
                            secondary: true
                        },
                        {
                            default: () => 'Remove',
                            icon: h(NIcon, null, h('i', { class: 'fas fa-trash-alt' }))
                        }
                    ),
                ]
            );
        },
    },
];

const pagination = ref({
    pageSize: 10,
});

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

const handleConnect = async () => {
    try {
        const response = await axios.post(`${host}backends`, formData.value, {
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            }
        });
        if (response.status === 200) {
            showNotificationMessage('Backend added successfully!');
            closeModal();
            await fetchBackends();
        }
    } catch (error) {
        showNotificationMessage(error.response?.data?.detail || 'Failed to add backend', 'error');
    }
};

const setDefaultBackend = async (backend_name) => {
    try {
        const response = await axios.put(`${host}backends/${backend_name}/default`, {}, {
            headers: getAuthHeaders(),
        });
        if (response.status === 200) {
            showNotificationMessage('Default backend updated');
            await fetchBackends();
        }
    } catch (error) {
        showNotificationMessage('Failed to set default backend', 'error');
    }
};

const deleteBackend = async (backend_name) => {
    try {
        const response = await axios.delete(`${host}backends/${backend_name}`, {
            headers: getAuthHeaders(),
        });
        if (response.status === 200) {
            showNotificationMessage('Backend removed successfully!');
            await fetchBackends();
        }
    } catch (error) {
        showNotificationMessage('Failed to remove backend', 'error');
    }
};

const fetchBackends = async () => {
    try {
        const response = await axios.get(`${host}backends/`, {
            headers: getAuthHeaders(),
        });
        activeList.value = response.data.backends;

        // Set first backend as default if none is set
        if (activeList.value.length > 0 && !activeList.value.some(b => b.is_default)) {
            await setDefaultBackend(activeList.value[0].backend_name);
        }
    } catch (error) {
        showNotificationMessage('Failed to fetch backends', 'error');
    }
};

const openModal = () => {
    showModal.value = true;
};

const closeModal = () => {
    showModal.value = false;
    formData.value = {
        backend_type: '',
        name: '',
        engine: '',
        api_key: '',
        base_url: '',
        model: '',
        maxtokens: 2048,
        temperature: 0.7,
        topp: 0.5,
        is_default: false
    };
};

onMounted(() => {
    fetchBackends();
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
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

.status-badge.active {
    background: #dcfce7;
    color: #16a34a;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
}

.actions-cell {
    display: flex;
    gap: 8px;
    justify-content: flex-start;
    align-items: center;
    min-width: 200px;
}

.action-button {
    margin: 0;
}

.no-data {
    text-align: center;
    color: #64748b;
    padding: 24px;
}

.custom-modal {
    width: 600px;
}

.code-container {
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 12px;
    background-color: #f8fafc;
    margin-top: 8px;
    overflow: auto;
}

.code-container pre {
    margin: 0;
    font-family: 'Fira Code', 'Courier New', monospace;
    font-size: 0.875rem;
}

.provider-table-container {
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.n-data-table {
    border-radius: 8px;
}

.n-data-table :deep(th) {
    background-color: #f1f5f9 !important;
    font-weight: 600;
}

.n-data-table :deep(tr:hover td) {
    background-color: #f8fafc !important;
}
</style>

<style>
/* Global highlight.js styles */
.hljs {
    background: transparent !important;
    padding: 0 !important;
}
</style>