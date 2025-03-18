<template>
    <div class="register-container">
        <n-card title="Create an Account" bordered class="register-card">
            <n-form ref="formRef" :model="form" :rules="rules">
                <n-form-item label="Username" path="username">
                    <n-input v-model:value="form.username" placeholder="Enter your username" clearable />
                </n-form-item>

                <n-form-item label="Email" path="email">
                    <n-input v-model:value="form.email" type="email" placeholder="Enter your email" clearable />
                </n-form-item>

                <n-form-item label="Password" path="password">
                    <n-input v-model:value="form.password" type="password" placeholder="Enter your password"
                        show-password-on="click" clearable />
                </n-form-item>

                <n-form-item label="First Name" path="first_name">
                    <n-input v-model:value="form.first_name" placeholder="Enter your first name" clearable />
                </n-form-item>

                <n-form-item label="Last Name" path="last_name">
                    <n-input v-model:value="form.last_name" placeholder="Enter your last name" clearable />
                </n-form-item>

                <n-space justify="space-between">
                    <n-checkbox v-model:checked="form.is_active">Active</n-checkbox>
                    <n-checkbox v-model:checked="form.is_admin">Admin</n-checkbox>
                </n-space>

                <n-button type="primary" block :loading="loading" @click="registerUser">
                    Register
                </n-button>

                <div class="login-redirect">
                    <span>You want to login? </span>
                    <a @click="goToLogin" style="color: #409eff; cursor: pointer;">Click here</a>
                </div>
            </n-form>
        </n-card>
    </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useMessage } from "naive-ui";
import axios from "axios";

const formRef = ref(null);
const message = useMessage();
const router = useRouter();

const form = ref({
    username: "",
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    is_active: true,
    is_admin: false,
});

const loading = ref(false);

const rules = {
    username: [
        { required: true, message: "Username is required", trigger: "blur" },
        { min: 3, message: "Username must be at least 3 characters", trigger: "blur" },
    ],
    email: [
        { required: true, message: "Email is required", trigger: "blur" },
        { type: "email", message: "Invalid email format", trigger: "blur" },
    ],
    password: [
        { required: true, message: "Password is required", trigger: "blur" },
        { min: 6, message: "Password must be at least 6 characters", trigger: "blur" },
    ],
    first_name: [{ required: true, message: "First name is required", trigger: "blur" }],
    last_name: [{ required: true, message: "Last name is required", trigger: "blur" }],
};

const registerUser = async () => {
    formRef.value?.validate(async (errors) => {
        if (!errors) {
            loading.value = true;
            console.log(form.value);

            try {
                const response = await axios.post("https://10.0.34.129:8000/auth/register", form.value, {
                    headers: {
                        'Content-Type': 'application/json',
                    },
                });

                console.log(response.data);
                message.success(`User ${response.data.username} registered successfully!`);
                router.push({ name: "login" });
            } catch (error) {
                console.error(error);
                const errorMessage = error.response?.data?.detail || error.message || "Registration failed";
                message.error(errorMessage);
            } finally {
                loading.value = false;
            }
        }
    });
};

const goToLogin = () => {
    router.push({ name: "login" });
};
</script>

<style scoped>
.register-container {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
    background: #f4f4f4;
}

.register-card {
    width: 400px;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}

.login-redirect {
    text-align: center;
    margin-top: 20px;
}
</style>
