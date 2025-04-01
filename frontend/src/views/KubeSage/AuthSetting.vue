<<template>
    <n-config-provider>
        <n-layout class="app-container" :class="{ 'dark-mode': isDarkMode }">
            <n-layout-header class="dashboard-header">
                <div class="header-content">
                    <div class="header-title">
                        <div class="admin-logo">
                            <i class="fas fa-server"></i>
                        </div>
                        <h2 class="dashboard-title">Provider Management</h2>
                    </div>
                    <n-button type="primary" @click="openModal">
                        <i class="fas fa-plus-circle "></i>  Add New Provider
                    </n-button>
                </div>
            </n-layout-header>

            <n-layout-content class="backend-dashboard">
                <n-alert v-if="showNotification" :type="notificationType" :title="notificationMessage" closable
                    @close="showNotification = false" class="notification-alert" />

                <n-card class="backend-table-container">
                    <div class="table-header">
                        <n-input v-model:value="searchQuery" placeholder="Search backends..." clearable
                            class="search-input">
                            <template #prefix>
                                <i class="fas fa-search"></i>
                            </template>
                        </n-input>
                        <div class="backend-stats">
                            <n-tag type="success" round class="backend-count">
                                <i class="fas fa-database"></i> Total: {{ activeList.length }}
                            </n-tag>
                            <n-button circle @click="fetchBackends" class="refresh-btn" size="medium">
                                <template #icon>
                                    <i class="fas fa-sync-alt"></i>
                                </template>
                            </n-button>
                        </div>
                    </div>

                    <n-data-table :columns="columns" :data="filteredBackends" :pagination="pagination" :bordered="false"
                        class="backend-table" />
                </n-card>

                <!-- Modal for Adding New Backend -->
                <n-modal v-model:show="showModal" :bordered="false"
                    class="custom-modal create-backend-modal" :style="{
                        '--modal-color': '#10BC3B',
                        '--modal-light': 'rgba(32, 128, 240, 0.1)'
                    }" transform-origin="center">
                    <div class="modal-content-wrapper">
                        <div class="modal-header">
                            <div class="modal-icon">
                                <i class="fas fa-server"></i>
                            </div>
                            <h3>Add Backend</h3>
                        </div>

                        <div class="modal-body">
                            <n-form :model="formData" :rules="rules" ref="formRef">
                                <n-form-item label="Provider Name" path="backend_type" required>
                                    <n-input v-model:value="formData.backend_type" placeholder="Enter your provider name"
                                        @update:value="formData.name = formData.backend_type"
                                        :class="{ 'error-field': backendTypeError }" class="modal-input">
                                        <template #prefix>
                                            <i class="fas fa-cloud"></i>
                                        </template>
                                    </n-input>
                                    <!-- <div v-if="backendTypeError" class="error-container">
                                        <span class="error-icon">✖</span>
                                        <span class="error-message">{{ backendTypeError }}</span>
                                    </div> -->
                                </n-form-item>

                                <n-form-item label="Base URL" path="base_url" required>
                                    <n-input v-model:value="formData.base_url" placeholder="Enter base URL"
                                        :class="{ 'error-field': baseUrlError }" class="modal-input">
                                        <template #prefix>
                                            <i class="fas fa-link"></i>
                                        </template>
                                    </n-input>
                                    <!-- <div v-if="baseUrlError" class="error-container">
                                        <span class="error-icon">✖</span>
                                        <span class="error-message">{{ baseUrlError }}</span>
                                    </div> -->
                                </n-form-item>

                                <n-form-item label="Model" path="model" required>
                                    <n-input v-model:value="formData.model" placeholder="Enter model"
                                        :class="{ 'error-field': modelError }" class="modal-input">
                                        <template #prefix>
                                            <i class="fas fa-robot"></i>
                                        </template>
                                    </n-input>
                                    <!-- <div v-if="modelError" class="error-container">
                                        <span class="error-icon">✖</span>
                                        <span class="error-message">{{ modelError }}</span>
                                    </div> -->
                                </n-form-item>

                                <n-form-item label="API Key" path="api_key" required>
                                    <n-input v-model:value="formData.api_key" placeholder="Enter API key (if required)"
                                        type="password" show-password-toggle :class="{ 'error-field': apiKeyError }"
                                        class="modal-input">
                                        <template #prefix>
                                            <i class="fas fa-key"></i>
                                        </template>
                                    </n-input>
                                    <!-- <div v-if="apiKeyError" class="error-container">
                                        <span class="error-icon">✖</span>
                                        <span class="error-message">{{ apiKeyError }}</span>
                                    </div> -->
                                </n-form-item>
                            </n-form>
                        </div>

                        <div class="modal-footer">
                            <n-space justify="end">
                                <n-button @click="closeModal" class="cancel-btn" ghost>
                                    Cancel
                                </n-button>
                                <n-button type="primary" @click="validateAndConnect" class="submit-btn">
                                    <i class="fas fa-plug"></i> Connect
                                </n-button>
                            </n-space>
                        </div>
                    </div>
                </n-modal>
            </n-layout-content>
        </n-layout>
    </n-config-provider>
</template>

<script setup>
import { ref, onMounted, computed, h } from 'vue';
import axios from 'axios';
import { watch } from 'vue';

import {
    NConfigProvider, NLayout, NLayoutHeader, NLayoutContent, NButton, NIcon,
    NAlert, NCard, NDataTable, NModal, NForm, NFormItem, NInput, NSpace, NSelect, NSwitch, NTag
} from 'naive-ui';
import { Add as PlusIcon } from '@vicons/ionicons5';

const host = 'https://10.0.34.129:8003/';
const showModal = ref(false);
const showNotification = ref(false);
const notificationMessage = ref('');
const notificationType = ref('success');
const activeList = ref([]);
const formRef = ref(null);
const searchQuery = ref('');
const isDarkMode = ref(false);

const backendTypeError = ref('');
const baseUrlError = ref('');
const modelError = ref('');
const apiKeyError = ref('');

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

const rules = {
    backend_type: {
        required: true,
        message: 'Provider name is required',
        trigger: ['blur', 'input']
    },
    base_url: {
        required: true,
        message: 'Base URL is required',
        trigger: ['blur', 'input'],
        validator: (rule, value) => {
            if (!value) return false;
            try {
                new URL(value);
                return true;
            } catch {
                return false;
            }
        }
    },
    model: {
        required: true,
        message: 'Model is required',
        trigger: ['blur', 'input']
    },
    api_key: {
        required: true,
        message: 'API key is required',
        trigger: ['blur', 'input']
    }
};

const filteredBackends = computed(() => {
    if (!activeList.value || !Array.isArray(activeList.value)) return [];
    if (!searchQuery.value) return activeList.value;
    const query = searchQuery.value.toLowerCase();
    return activeList.value.filter(
        backend =>
            backend?.backend_name?.toLowerCase().includes(query) ||
            backend?.model?.toLowerCase().includes(query)
    );
});

const validateField = (fieldName) => {
    switch (fieldName) {
        case 'backend_type':
            backendTypeError.value = formData.value.backend_type ? '' : 'Provider name is required';
            break;
        case 'base_url':
            if (!formData.value.base_url) {
                baseUrlError.value = 'Base URL is required';
            } else {
                try {
                    new URL(formData.value.base_url);
                    baseUrlError.value = '';
                } catch {
                    baseUrlError.value = 'Please enter a valid URL (include http:// or https://)';
                }
            }
            break;
        case 'model':
            modelError.value = formData.value.model ? '' : 'Model is required';
            break;
        case 'api_key':
            apiKeyError.value = formData.value.api_key ? '' : 'API key is required';
            break;
    }
};

const validateForm = () => {
    validateField('backend_type');
    validateField('base_url');
    validateField('model');
    validateField('api_key');

    return !backendTypeError.value && !baseUrlError.value && !modelError.value && !apiKeyError.value;
};

const validateAndConnect = async () => {
    if (validateForm()) {
        await handleConnect();
    } else {
        showNotificationMessage('Please fix all errors before submitting', 'error');
    }
};

watch(() => formData.value.backend_type, (newName) => {
    formData.value.name = newName;
    validateField('backend_type');
});

watch(() => formData.value.base_url, () => {
    validateField('base_url');
});

watch(() => formData.value.model, () => {
    validateField('model');
});

watch(() => formData.value.api_key, () => {
    validateField('api_key');
});

const columns = [
    {
        title: 'Provider Name',
        key: 'backend_name',
        render: (row) => {
            return h(
                'div',
                { class: 'backend-cell' },
                [
                    h('i', {
                        class: 'fas fa-server',
                        style: 'margin-right: 8px; color: #10BC3B;'
                    }),
                    h('span', row.backend_name)
                ]
            );
        }
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
    // Clear errors when closing modal
    backendTypeError.value = '';
    baseUrlError.value = '';
    modelError.value = '';
    apiKeyError.value = '';
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
/* Import Font Awesome */
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');

/* Main container */
.app-container {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    background-color: #f8f9fa;
    background-image: linear-gradient(to bottom right, #f8f9fa, #e8f5e9);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
    width: 100%;
}

.app-container.dark-mode {
    background-color: #1a1a1a;
    background-image: linear-gradient(to bottom right, #1a1a1a, #0d2d0f);
    color: #f0f0f0;
}

/* Header */
.dashboard-header {
    padding: 16px 24px;
    background-color: #ffffff;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    margin-bottom: 24px;
    border-left: 4px solid #10BC3B;
}

.app-container.dark-mode .dashboard-header {
    background-color: #222222;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    border-left: 4px solid #10BC3B;
}

.header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.header-title {
    display: flex;
    align-items: center;
    gap: 12px;
}

.admin-logo {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, #10BC3B, #80f769);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 18px;
    box-shadow: 0 2px 8px rgba(32, 128, 240, 0.3);
}

.dashboard-title {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: #10BC3B;
    letter-spacing: 0.5px;
}

.app-container.dark-mode .dashboard-title {
    color: #10BC3B;
}

/* Table Container */
.backend-table-container {
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    padding: 20px;
    background-color: #ffffff;
}

.app-container.dark-mode .backend-table-container {
    background-color: #222222;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.table-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    gap: 16px;
}

.search-input {
    flex: 1;
    max-width: 400px;
}

.backend-stats {
    display: flex;
    align-items: center;
    gap: 12px;
}

.backend-count {
    font-weight: 600;
    padding: 0 12px;
    height: 36px;
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(16, 188, 59, 0.1);
    border: 1px solid rgba(16, 188, 59, 0.2);
}

.backend-count i {
    font-size: 14px;
}

.refresh-btn {
    background: rgba(32, 128, 240, 0.1);
    color: #10BC3B;
    border: 1px solid rgba(32, 128, 240, 0.2);
    transition: all 0.3s ease;
}

.refresh-btn:hover {
    background: rgba(32, 128, 240, 0.2);
    transform: rotate(180deg);
}

/* Table Styles */
.backend-table {
    --n-border-color: rgba(32, 128, 240, 0.1);
    --n-th-color: #f5f9ff;
    --n-td-color: #ffffff;
    --n-th-text-color: #10BC3B;
    --n-td-text-color: #4a5568;
}

.app-container.dark-mode .backend-table {
    --n-border-color: rgba(32, 128, 240, 0.2);
    --n-th-color: #1a2e4d;
    --n-td-color: #222222;
    --n-th-text-color: #10BC3B;
    --n-td-text-color: #a0aec0;
}

.backend-cell {
    display: flex;
    align-items: center;
    font-weight: 500;
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

.app-container.dark-mode .status-badge.active {
    background: rgba(22, 163, 74, 0.2);
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

.notification-alert {
    margin-bottom: 20px;
}

/* Updated Modal Styles */
.custom-modal {
    --modal-color: #10BC3B;
    --modal-light: rgba(32, 128, 240, 0.1);
    border-radius: 12px;
    background-color: white;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
    width: 500px;
    max-width: 90%;
    display: flex;
    flex-direction: column;
}

.app-container.dark-mode .custom-modal {
    background-color: #222222;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

.modal-content-wrapper {
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 20px;
    height: 100%;
}

.modal-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding-bottom: 16px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.1);
    margin-bottom: 0;
}

.modal-body {
    flex: 1;
    overflow-y: auto;
    padding: 8px 0;
}

.modal-footer {
    padding-top: 16px;
    border-top: 1px solid rgba(0, 0, 0, 0.1);
    margin-top: auto;
}

.modal-icon {
    width: 40px;
    height: 40px;
    background: var(--modal-light);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--modal-color);
    font-size: 18px;
}

.modal-header h3 {
    margin: 0;
    font-size: 1.3rem;
    color: var(--modal-color);
}

.modal-input :deep(.n-input) {
    border-radius: 8px;
    border: 1px solid rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
}

.app-container.dark-mode .modal-input :deep(.n-input) {
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.modal-input :deep(.n-input):focus {
    border-color: var(--modal-color);
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--modal-color) 20%, transparent);
}

.cancel-btn {
    color: var(--modal-color);
    border: 1px solid var(--modal-color);
}

.cancel-btn:hover {
    background-color: var(--modal-light);
}

.submit-btn {
    background-color: var(--modal-color) !important;
    border: none !important;
    color: white !important;
    box-shadow: 0 2px 8px color-mix(in srgb, var(--modal-color) 30%, transparent);
    transition: all 0.3s ease;
}

.submit-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px color-mix(in srgb, var(--modal-color) 40%, transparent);
}

.submit-btn i {
    margin-right: 8px;
}

/* Error styling */
.error-field {
    border-color: #ff4d4f !important;
}

.error-field:focus {
    box-shadow: 0 0 0 2px rgba(255, 77, 79, 0.2) !important;
}

.error-container {
    display: flex;
    align-items: center;
    margin-top: 6px;
    padding: 8px 12px;
    border-radius: 4px;
    background-color: #fff2f0;
    border: 1px solid #ffccc7;
    color: #ff4d4f;
    font-size: 13px;
    line-height: 1.5;
}

.app-container.dark-mode .error-container {
    background-color: rgba(255, 77, 79, 0.1);
    border-color: rgba(255, 77, 79, 0.3);
}

.error-icon {
    margin-right: 8px;
    font-weight: bold;
}

.error-message {
    flex: 1;
}

:deep(.n-modal-mask) {
    background-color: rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(4px);
}

.app-container.dark-mode :deep(.n-modal-mask) {
    background-color: rgba(0, 0, 0, 0.6);
}

:deep(.n-modal-container) {
    transition: all 0.3s ease;
}

@keyframes modalFadeIn {
    from {
        opacity: 0;
        transform: scale(0.95) translateY(20px);
    }
    to {
        opacity: 1;
        transform: scale(1) translateY(0);
    }
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .header-content {
        flex-direction: column;
        gap: 12px;
        align-items: flex-start;
    }

    .table-header {
        flex-direction: column;
        gap: 12px;
        align-items: stretch;
    }

    .search-input {
        max-width: 100%;
    }

    .backend-stats {
        width: 100%;
        justify-content: space-between;
    }

    .backend-table-container {
        padding: 12px;
    }

    .custom-modal {
        width: 95% !important;
        padding: 16px;
    }

    .actions-cell {
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;
    }
}
</style>