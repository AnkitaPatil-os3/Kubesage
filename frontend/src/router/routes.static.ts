export const staticRoutes: AppRoute.RowRoute[] = [
  {
    name: 'homeCenter',
    path: '/home',
    title: 'Home',
    requiresAuth: true,
    icon: 'mdi:home',
    componentPath: '/KubeSage/home.vue',
    id: 89,
    pid: null,
    roles: ['user','admin'] // Both can access
  },

  {
    name: 'Cluster Management',
    path: '/cluster-management',
    title: 'Cluster Management',
    requiresAuth: true,
    icon: 'mdi:kubernetes',
    componentPath: "/KubeSage/ClusterManagement.vue",
    id: 4,
    pid: null,
    roles: ['user'] // Only user can access
  },
 
  {
    name: 'Cluster Analysis',
    path: '/cluster-analysis',
    title: 'Cluster Analysis',
    requiresAuth: true,
    icon: 'mdi:chart-bar',
    componentPath: '/KubeSage/analyze.vue',
    id: 31,
    pid: null,
    roles: ['user'] // Only user can access
  },
  
  {
    name: 'Chat with KubeSage',
    path: '/chat-with-kubesage',
    title: 'KubeSage Chat',
    requiresAuth: true,
    icon: 'mdi:chat',
    componentPath: '/KubeSage/chat.vue',
    id: 32,
    pid: null,
    roles: ['user'] // Only user can access
  },
  
  {
    name: 'Observability',
    path: '/observability',
    title: 'Observability',
    requiresAuth: true,
    icon: 'mdi:monitor-dashboard',
    componentPath: '/KubeSage/Observability.vue',
    id: 35,
    pid: null,
    roles: ['user'] // Only user can access
  },

  {
    name: 'Auth Settings',
    path: '/auth-settings',
    title: 'Auth Settings',
    requiresAuth: true,
    icon: 'mdi:shield-key',
    componentPath: '/KubeSage/AuthSetting.vue',
    id: 33,
    pid: null,
    roles: ['admin'] // Only admin can access
  },
  
  // Add User Management for admin
  {
    name: 'User Management',
    path: '/user-management',
    title: 'User Management',
    requiresAuth: true,
    icon: 'mdi:account-group',
    componentPath: '/KubeSage/UserManagement.vue',
    id: 34,
    pid: null,
    roles: ['admin'] // Only admin can access
  }
]
