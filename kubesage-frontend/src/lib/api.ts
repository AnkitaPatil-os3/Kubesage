import axios from 'axios';
import { getSession } from 'next-auth/react';

// Define API service URLs
const userServiceBaseUrl = process.env.NEXT_PUBLIC_USER_SERVICE_URL;
const kubeconfigServiceBaseUrl = process.env.NEXT_PUBLIC_KUBECONFIG_SERVICE_URL;

// Create API instances
const userApi = axios.create({
  baseURL: userServiceBaseUrl,
});

const kubeconfigApi = axios.create({
  baseURL: kubeconfigServiceBaseUrl,
});

// Request interceptor to add auth token
const addAuthToken = async (config) => {
  const session = await getSession();
  
  if (session?.accessToken) {
    config.headers.Authorization = `Bearer ${session.accessToken}`;
  }
  
  return config;
};

// Add interceptors to both API instances
userApi.interceptors.request.use(addAuthToken);
kubeconfigApi.interceptors.request.use(addAuthToken);

// API functions for User Service
export const userService = {
  login: async (username: string, password: string) => {
    const response = await userApi.post('/auth/token', { username, password });
    return response.data;
  },
  
  register: async (userData) => {
    const response = await userApi.post(`/auth/register`, userData);
    return response.data;
  },
  
  getProfile: async () => {
    const response = await userApi.get('/users/me');
    return response.data;
  },
  
  changePassword: async (passwordData) => {
    const response = await userApi.post('/change-password', passwordData);
    return response.data;
  },
  
  // Admin endpoints
  getUsers: async () => {
    const response = await userApi.get('/');
    return response.data;
  },
  
  getUserById: async (id: number) => {
    const response = await userApi.get(`/${id}`);
    return response.data;
  },
  
  updateUser: async (id: number, userData) => {
    const response = await userApi.put(`/${id}`, userData);
    return response.data;
  },
  
  deleteUser: async (id: number) => {
    const response = await userApi.delete(`/${id}`);
    return response.data;
  },
};

// API functions for Kubeconfig Service
export const kubeconfigService = {
  upload: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await kubeconfigApi.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  },
  
  list: async () => {
    const response = await kubeconfigApi.get('/list');
    return response.data;
  },
  
  activate: async (filename: string) => {
    const response = await kubeconfigApi.put(`/activate/${filename}`);
    return response.data;
  },
  
  getClusters: async () => {
    const response = await kubeconfigApi.get('/clusters');
    return response.data;
  },
  
  getNamespaces: async () => {
    const response = await kubeconfigApi.get('/namespaces');
    return response.data;
  },
  
  installOperator: async () => {
    const response = await kubeconfigApi.post('/install-operator');
    return response.data;
  },
  
  removeKubeconfig: async (filename: string) => {
    const response = await kubeconfigApi.delete('/remove', {
      params: { filename },
    });
    return response.data;
  },
};
