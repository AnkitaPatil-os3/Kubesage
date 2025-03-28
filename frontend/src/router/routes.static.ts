
export const staticRoutes: AppRoute.RowRoute[] = [
  {
    name: 'homeCenter',
    path: '/home',
    title: 'Home',
    requiresAuth: true,
    icon: 'line-md:home',
    componentPath: '/KubeSage/home.vue',
    id: 89,
    pid: null,
  },


  {
    name: 'Cluster Management',
    path: '/cluster-management',
    title: 'Cluster Management',
    requiresAuth: true,
    icon: 'icon-park-outline:alarm',
    // menuType: 'dir',
    componentPath: "/KubeSage/ClusterManagement.vue",
    id: 4,
    pid: null,
  },
 
  {
    name: 'Cluster Analysis',
    path: '/cluster-analysis',
    title: 'Cluster Analysis',
    requiresAuth: true,
    icon: 'icon-park-outline:error-computer',
    componentPath: '/KubeSage/analyze.vue',
    id: 31,
    pid: null,
  },
  {
    name: 'Chat with KubeSage',
    path: '/chat-with-kubesage',
    title: 'KubeSage Chat',
    requiresAuth: true,
    icon: 'icon-park-outline:list',
    componentPath: '/KubeSage/chat.vue',
    id: 32,
    pid: null,
  },

  {
    name: 'Auth Settings',
    path: '/auth-settings',
    title: 'Auth Settings',
    requiresAuth: true,
    icon: 'icon-park-outline:setting',
    // menuType: 'dir',
    componentPath: '/KubeSage/AuthSetting.vue',
    id: 33,
    pid: null,
  },
  

]

