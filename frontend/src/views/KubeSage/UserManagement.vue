<template>
    <div class="app-container" :class="{ 'dark-mode': isDarkMode }">
        <div class="main-content">
            <!-- Header -->
            <div class="user-header">
                <div class="header-title">
                    <div class="admin-logo">
                        <i class="fas fa-user-shield"></i>
                    </div>
                    <h2>User Management</h2>
                </div>
                <n-button type="primary" @click="showCreateUserModal = true">
                    <i class="fas fa-user-plus"></i> Create New User
                </n-button>
            </div>

            <!-- User Table -->
            <n-card class="user-table-container">
                <div class="table-header">
                    <n-input v-model:value="searchQuery" placeholder="Search users..." clearable class="search-input">
                        <template #prefix>
                            <i class="fas fa-search"></i>
                        </template>
                    </n-input>
                    <div class="user-stats">
                        <n-tag type="success" round class="user-count">
                            <i class="fas fa-users"></i> Total: {{ filteredUsers.length }}
                        </n-tag>
                        <n-button circle @click="refreshUsers" class="refresh-btn" size="medium">
                            <template #icon>
                                <i class="fas fa-sync-alt"></i>
                            </template>
                        </n-button>
                    </div>
                </div>

                <n-data-table :columns="columns" :data="filteredUsers" :pagination="pagination" :bordered="false"
                    :loading="loading" class="user-table" />
            </n-card>
        </div>

        <!-- Create User Modal -->
        <n-modal v-model:show="showCreateUserModal" :bordered="false" class="custom-modal create-user-modal" :style="{
            '--modal-color': '#10BC3B',
            '--modal-light': 'rgba(16, 188, 59, 0.1)'
        }" transform-origin="center">
            <div class="modal-content-wrapper">
                <div class="modal-header">
                    <div class="modal-icon">
                        <i class="fas fa-user-plus"></i>
                    </div>
                    <h3>Create New User</h3>
                </div>

                <div class="modal-body">
                    <n-form ref="createUserForm" :model="newUser" :rules="userRules">
                        <n-form-item label="Username" path="username">
                            <n-input v-model:value="newUser.username" placeholder="Enter username" class="modal-input">
                                <template #prefix>
                                    <i class="fas fa-user"></i>
                                </template>
                            </n-input>
                        </n-form-item>
                        <n-form-item label="Email" path="email">
                            <n-input v-model:value="newUser.email" placeholder="Enter email" class="modal-input">
                                <template #prefix>
                                    <i class="fas fa-envelope"></i>
                                </template>
                            </n-input>
                        </n-form-item>
                        <n-form-item label="Password" path="password">
                            <n-input v-model:value="newUser.password" type="password" placeholder="Enter password"
                                class="modal-input">
                                <template #prefix>
                                    <i class="fas fa-lock"></i>
                                </template>
                            </n-input>
                        </n-form-item>
                        <n-form-item label="First Name" path="first_name">
                            <n-input v-model:value="newUser.first_name" placeholder="Enter first name"
                                class="modal-input">
                                <template #prefix>
                                    <i class="fas fa-user"></i>
                                </template>
                            </n-input>
                        </n-form-item>
                        <n-form-item label="Last Name" path="last_name">
                            <n-input v-model:value="newUser.last_name" placeholder="Enter last name"
                                class="modal-input">
                                <template #prefix>
                                    <i class="fas fa-user"></i>
                                </template>
                            </n-input>
                        </n-form-item>
                        <n-space justify="space-between">
                            <n-checkbox v-model:checked="newUser.is_active">Active</n-checkbox>
                            <n-checkbox v-model:checked="newUser.is_admin">Admin</n-checkbox>
                        </n-space>
                    </n-form>
                </div>

                <div class="modal-footer">
                    <n-space justify="end">
                        <n-button @click="showCreateUserModal = false" class="cancel-btn" ghost>
                            Cancel
                        </n-button>
                        <n-button type="primary" @click="createUser" class="submit-btn" :loading="registerLoading">
                            <i class="fas fa-plus-circle"></i> Create User
                        </n-button>
                    </n-space>
                </div>
            </div>
        </n-modal>

        <!-- Edit User Modal -->
        <n-modal v-model:show="showEditUserModal" :bordered="false" class="custom-modal edit-user-modal" :style="{
            '--modal-color': '#2080F0',
            '--modal-light': 'rgba(32, 128, 240, 0.1)'
        }" transform-origin="center">
            <div class="modal-content-wrapper">
                <div class="modal-header">
                    <div class="modal-icon">
                        <i class="fas fa-user-edit"></i>
                    </div>
                    <h3>Edit User: {{ editUser.username }}</h3>
                </div>

                <div class="modal-body">
                    <n-form ref="editUserForm" :model="editUser" :rules="userRules">
                        <n-form-item label="Username" path="username">
                            <n-input v-model:value="editUser.username" placeholder="Enter username" class="modal-input">
                                <template #prefix>
                                    <i class="fas fa-user"></i>
                                </template>
                            </n-input>
                        </n-form-item>
                        <n-form-item label="Email" path="email">
                            <n-input v-model:value="editUser.email" placeholder="Enter email" class="modal-input">
                                <template #prefix>
                                    <i class="fas fa-envelope"></i>
                                </template>
                            </n-input>
                        </n-form-item>
                        <n-form-item label="First Name" path="first_name">
                            <n-input v-model:value="editUser.first_name" placeholder="Enter first name"
                                class="modal-input">
                                <template #prefix>
                                    <i class="fas fa-user"></i>
                                </template>
                            </n-input>
                        </n-form-item>
                        <n-form-item label="Last Name" path="last_name">
                            <n-input v-model:value="editUser.last_name" placeholder="Enter last name"
                                class="modal-input">
                                <template #prefix>
                                    <i class="fas fa-user"></i>
                                </template>
                            </n-input>
                        </n-form-item>
                        <n-space justify="space-between">
                            <n-checkbox v-model:checked="editUser.is_active">Active</n-checkbox>
                            <n-checkbox v-model:checked="editUser.is_admin">Admin</n-checkbox>
                        </n-space>
                    </n-form>
                </div>

                <div class="modal-footer">
                    <n-space justify="end">
                        <n-button @click="showEditUserModal = false" class="cancel-btn" ghost>
                            Cancel
                        </n-button>
                        <n-button type="primary" @click="updateUser" class="submit-btn">
                            <i class="fas fa-save"></i> Save Changes
                        </n-button>
                    </n-space>
                </div>
            </div>
        </n-modal>

        <!-- Change Password Modal -->
        <n-modal v-model:show="showChangePasswordModal" :bordered="false" class="custom-modal change-password-modal"
            :style="{
                '--modal-color': '#F0A020',
                '--modal-light': 'rgba(240, 160, 32, 0.1)'
            }" transform-origin="center">
            <div class="modal-content-wrapper">
                <div class="modal-header">
                    <div class="modal-icon">
                        <i class="fas fa-key"></i>
                    </div>
                    <h3>Change Password for {{ passwordUser?.username }}</h3> <!-- User info here -->
                </div>

                <div class="modal-body">
                    <n-form ref="passwordForm" :model="passwordData" :rules="passwordRules">
                        <n-form-item label="New Password" path="newPassword">
                            <n-input v-model:value="passwordData.newPassword" type="password"
                                placeholder="Enter new password" class="modal-input">
                                <template #prefix>
                                    <i class="fas fa-lock"></i>
                                </template>
                            </n-input>
                        </n-form-item>
                        <n-form-item label="Confirm Password" path="confirmPassword">
                            <n-input v-model:value="passwordData.confirmPassword" type="password"
                                placeholder="Confirm new password" class="modal-input">
                                <template #prefix>
                                    <i class="fas fa-lock"></i>
                                </template>
                            </n-input>
                        </n-form-item>
                    </n-form>
                </div>

                <div class="modal-footer">
                    <n-space justify="end">
                        <n-button @click="showChangePasswordModal = false" class="cancel-btn" ghost>
                            Cancel
                        </n-button>
                        <n-button type="primary" @click="changePassword(passwordUser.id)" class="submit-btn">
                            <i class="fas fa-sync-alt"></i> Change Password
                        </n-button>
                    </n-space>
                </div>
            </div>
        </n-modal>

    </div>
</template>

<script setup>
import { ref, computed, onMounted, h } from 'vue';
import {
    NButton,
    NCard,
    NDataTable,
    NInput,
    NModal,
    NForm,
    NFormItem,
    NSelect,
    NSpace,
    NTag,
    NCheckbox,
    useMessage,
    useDialog
} from 'naive-ui';
import axios from 'axios';

// Configuration
const host = '10.0.32.122:8003'; // Define your host variable here
const baseURL = `https://${host}`;

// Dark mode
const isDarkMode = ref(localStorage.getItem('darkMode') === 'true');

// UI Helpers
const message = useMessage();
const dialog = useDialog();

// Data
const users = ref([]);
const loading = ref(false);
const registerLoading = ref(false);
const searchQuery = ref('');

// Modals
const showCreateUserModal = ref(false);
const showEditUserModal = ref(false);
const showChangePasswordModal = ref(false);

// Form Data
const newUser = ref({
    username: '',
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    is_active: true,
    is_admin: false
});

const editUser = ref({
    id: '',
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    is_active: true,
    is_admin: false
});

const passwordUser = ref({
    id: '',
    username: ''
});

const passwordData = ref({
    newPassword: '',
    confirmPassword: ''
});

// Form Refs
const createUserForm = ref(null);
const editUserForm = ref(null);
const passwordForm = ref(null);

// Authentication headers
const getAuthHeaders = () => {
    try {
        const token = JSON.parse(localStorage.getItem('accessToken')).value;
        return {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
        };
    } catch (error) {
        console.error('Authentication error. Please login again.');
        return { 'Content-Type': 'application/json' };
    }
};

// Validation Rules
const userRules = {
    username: [
        { required: true, message: 'Username is required', trigger: 'blur' },
        { min: 3, message: 'Username must be at least 3 characters', trigger: 'blur' }
    ],
    email: [
        { required: true, message: 'Email is required', trigger: 'blur' },
        { type: 'email', message: 'Invalid email format', trigger: 'blur' }
    ],
    password: [
        { required: true, message: 'Password is required', trigger: 'blur' },
        { min: 6, message: 'Password must be at least 6 characters', trigger: 'blur' }
    ],
    first_name: [
        { required: true, message: 'First name is required', trigger: 'blur' }
    ],
    last_name: [
        { required: true, message: 'Last name is required', trigger: 'blur' }
    ]
};

const passwordRules = {
    newPassword: {
        required: true,
        message: 'Password is required',
        trigger: 'blur',
        validator(rule, value) {
            if (value.length < 6) {
                return new Error('Password must be at least 6 characters');
            }
            return true;
        }
    },
    confirmPassword: {
        required: true,
        message: 'Please confirm password',
        trigger: 'blur',
        validator(rule, value) {
            if (value !== passwordData.value.newPassword) {
                return new Error('Passwords do not match');
            }
            return true;
        }
    }
};

// Table Configuration
const columns = [
    {
        title: 'User',
        key: 'username',
        render(row) {
            return h(
                'div',
                { class: 'user-cell' },
                [
                    h('i', { class: `fas fa-user${row.is_admin ? '-shield' : ''}`, style: 'margin-right: 8px; color: #10BC3B;' }),
                    h('span', row.username)
                ]
            );
        }
    },
    {
        title: 'Email',
        key: 'email'
    },
    {
        title: 'Name',
        key: 'name',
        render(row) {
            return `${row.first_name} ${row.last_name}`;
        }
    },
    {
        title: 'Role',
        key: 'is_admin',
        render(row) {
            return h(
                NTag,
                {
                    type: row.is_admin ? 'error' : 'success'
                },
                {
                    default: () => row.is_admin ? 'ADMIN' : 'USER'
                }
            );
        }
    },
    {
        title: 'Status',
        key: 'is_active',
        render(row) {
            return h(
                NTag,
                {
                    type: row.is_active ? 'success' : 'warning'
                },
                {
                    default: () => row.is_active ? 'ACTIVE' : 'INACTIVE'
                }
            );
        }
    },
    {
        title: 'Created',
        key: 'created_at',
        render(row) {
            return new Date(row.created_at).toLocaleDateString();
        }
    },
    {
        title: 'Actions',
        key: 'actions',
        render(row) {
            return h(
                NSpace,
                {},
                [
                    h(
                        NButton,
                        {
                            size: 'small',
                            type: 'info',
                            onClick: () => openEditModal(row),
                            class: 'action-btn'
                        },
                        {
                            default: () => h('i', { class: 'fas fa-edit' }),
                            icon: () => h('i', { class: 'fas fa-edit' })
                        }
                    ),
                    h(
                        NButton,
                        {
                            size: 'small',
                            type: 'warning',
                            onClick: () => openChangePasswordModal(row),
                            class: 'action-btn'
                        },
                        {
                            default: () => h('i', { class: 'fas fa-key' }),
                            icon: () => h('i', { class: 'fas fa-key' })
                        }
                    ),
                    h(
                        NButton,
                        {
                            size: 'small',
                            type: 'error',
                            onClick: () => confirmDeleteUser(row),
                            class: 'action-btn'
                        },
                        {
                            default: () => h('i', { class: 'fas fa-trash' }),
                            icon: () => h('i', { class: 'fas fa-trash' })
                        }
                    )
                ]
            );
        }
    }
];

const pagination = {
    pageSize: 10
};

// Computed
const filteredUsers = computed(() => {
    if (!users.value || !Array.isArray(users.value)) return [];
    if (!searchQuery.value) return users.value;
    const query = searchQuery.value.toLowerCase();
    return users.value.filter(
        user =>
            user?.username?.toLowerCase().includes(query) ||
            user?.email?.toLowerCase().includes(query) ||
            user?.first_name?.toLowerCase().includes(query) ||
            user?.last_name?.toLowerCase().includes(query) ||
            (user?.is_admin ? 'admin' : 'user').includes(query)
    );
});

// Methods
const fetchUsers = async () => {
    loading.value = true;
    try {
        const response = await axios.get(`${baseURL}/users/`, {
            headers: getAuthHeaders()
        });
        users.value = response.data;
        message.success('Users loaded successfully');
    } catch (error) {
        message.error('Failed to load users');
        console.error(error);
    } finally {
        loading.value = false;
    }
};

const createUser = async () => {
    try {
        await createUserForm.value?.validate();
        registerLoading.value = true;

        const response = await axios.post(`${baseURL}/auth/register`, {
            username: newUser.value.username,
            email: newUser.value.email,
            password: newUser.value.password,
            first_name: newUser.value.first_name,
            last_name: newUser.value.last_name,
            is_active: newUser.value.is_active,
            is_admin: newUser.value.is_admin
        }, {
            headers: getAuthHeaders()
        });

        const user = {
            ...response.data,
            created_at: new Date().toISOString()
        };

        users.value.unshift(user);
        message.success('User created successfully');
        showCreateUserModal.value = false;
        resetNewUserForm();
    } catch (error) {
        console.error(error);
        const errorMessage = error.response?.data?.detail || error.message || "User creation failed";
        message.error(errorMessage);
    } finally {
        registerLoading.value = false;
    }
};

const updateUser = async () => {
    try {
        await editUserForm.value?.validate();

        await axios.put(`${baseURL}/users/${editUser.value.id}`, {
            username: editUser.value.username,
            email: editUser.value.email,
            first_name: editUser.value.first_name,
            last_name: editUser.value.last_name,
            is_active: editUser.value.is_active,
            is_admin: editUser.value.is_admin
        }, {
            headers: getAuthHeaders()
        });

        const index = users.value.findIndex(u => u.id === editUser.value.id);
        if (index !== -1) {
            users.value[index] = {
                ...users.value[index],
                ...editUser.value
            };
            message.success('User updated successfully');
            showEditUserModal.value = false;
        }
    } catch (error) {
        console.error(error);
        const errorMessage = error.response?.data?.detail || error.message || "User update failed";
        message.error(errorMessage);
    }
};

const changePassword = async (userId) => {
    console.log("Changing password for user ID: ", userId);

    if (!userId || typeof userId !== 'number') {
        message.error('Valid User ID is required');
        return;
    }

    try {
        await passwordForm.value?.validate();

        if (passwordData.value.newPassword !== passwordData.value.confirmPassword) {
            message.error('New password and confirm password do not match');
            return;
        }

        await axios.post(`${baseURL}/auth/change-password/${userId}`, {
            new_password: passwordData.value.newPassword,
            confirm_password: passwordData.value.confirmPassword
        }, {
            headers: getAuthHeaders()
        });

        message.success('Password changed successfully');
        showChangePasswordModal.value = false;
        passwordData.value = { newPassword: '', confirmPassword: '' };
    } catch (error) {
        console.error(error);
        const errorMessage = error.response?.data?.detail || error.message || "Password change failed";
        message.error(errorMessage);
    }
};




const confirmDeleteUser = (user) => {
    dialog.warning({
        title: 'Confirm Deletion',
        content: `Are you sure you want to delete user ${user.username}? This action cannot be undone.`,
        positiveText: 'Delete',
        negativeText: 'Cancel',
        onPositiveClick: () => deleteUser(user.id)
    });
};

const deleteUser = async (userId) => {
    try {
        await axios.delete(`${baseURL}/users/${userId}`, {
            headers: getAuthHeaders()
        });

        users.value = users.value.filter(user => user.id !== userId);
        message.success('User deleted successfully');
    } catch (error) {
        message.error('Failed to delete user');
        console.error(error);
    }
};

const openEditModal = (user) => {
    editUser.value = { ...user };
    showEditUserModal.value = true;
};

const openChangePasswordModal = (user) => {
    passwordUser.value = { id: user.id, username: user.username };
    showChangePasswordModal.value = true;
};

const refreshUsers = () => {
    fetchUsers();
};

const resetNewUserForm = () => {
    newUser.value = {
        username: '',
        email: '',
        password: '',
        first_name: '',
        last_name: '',
        is_active: true,
        is_admin: false
    };
};

// Lifecycle
onMounted(() => {
    fetchUsers();
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

.main-content {
    flex: 1;
    padding: 20px;
    width: 100%;
    max-width: 100%;
    margin: 0 auto;
}

/* Header */
.user-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    background-color: #ffffff;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    margin-bottom: 24px;
    border-left: 4px solid #10BC3B;
}

.header-title {
    display: flex;
    align-items: center;
    gap: 12px;
}

.admin-logo {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, #10BC3B, #09a431);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 18px;
    box-shadow: 0 2px 8px rgba(16, 188, 59, 0.3);
}

.app-container.dark-mode .user-header {
    background-color: #222222;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    border-left: 4px solid #10BC3B;
}

.user-header h2 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: #10BC3B;
    letter-spacing: 0.5px;
}

.app-container.dark-mode .user-header h2 {
    color: #10BC3B;
}

/* Table Container */
.user-table-container {
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    padding: 20px;
    background-color: #ffffff;
}

.app-container.dark-mode .user-table-container {
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

.user-stats {
    display: flex;
    align-items: center;
    gap: 12px;
}

.user-count {
    font-weight: 600;
    padding: 0 12px;
    height: 36px;
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(16, 188, 59, 0.1);
    border: 1px solid rgba(16, 188, 59, 0.2);
}

.user-count i {
    font-size: 14px;
}

.refresh-btn {
    background: rgba(16, 188, 59, 0.1);
    color: #10BC3B;
    border: 1px solid rgba(16, 188, 59, 0.2);
    transition: all 0.3s ease;
}

.refresh-btn:hover {
    background: rgba(16, 188, 59, 0.2);
    transform: rotate(180deg);
}

/* Table Styles */
.user-table {
    --n-border-color: rgba(16, 188, 59, 0.1);
    --n-th-color: #f5fff7;
    --n-td-color: #ffffff;
    --n-th-text-color: #10BC3B;
    --n-td-text-color: #4a5568;
}

.app-container.dark-mode .user-table {
    --n-border-color: rgba(16, 188, 59, 0.2);
    --n-th-color: #1a2e1d;
    --n-td-color: #222222;
    --n-th-text-color: #10BC3B;
    --n-td-text-color: #a0aec0;
}

.user-cell {
    display: flex;
    align-items: center;
    font-weight: 500;
}

.action-btn {
    transition: all 0.2s ease;
}

.action-btn:hover {
    transform: scale(1.1);
}

/* Modal Styles */
.custom-modal {
    --modal-color: #10BC3B;
    --modal-light: rgba(16, 188, 59, 0.1);
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

.app-container.dark-mode .modal-header {
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
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

.app-container.dark-mode .modal-footer {
    border-top: 1px solid rgba(255, 255, 255, 0.1);
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

.modal-select :deep(.n-base-selection) {
    border-radius: 8px;
    border: 1px solid rgba(0, 0, 0, 0.1);
}

.app-container.dark-mode .modal-select :deep(.n-base-selection) {
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.modal-select :deep(.n-base-selection):focus {
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

/* Specific modal colors */
.create-user-modal {
    --modal-color: #10BC3B;
    --modal-light: rgba(16, 188, 59, 0.1);
}

.edit-user-modal {
    --modal-color: #2080F0;
    --modal-light: rgba(32, 128, 240, 0.1);
}

.change-password-modal {
    --modal-color: #F0A020;
    --modal-light: rgba(240, 160, 32, 0.1);
}

/* Animation */
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
    .user-header {
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

    .user-stats {
        width: 100%;
        justify-content: space-between;
    }

    .user-table-container {
        padding: 12px;
    }

    .custom-modal {
        width: 95%;
    }
}
</style>