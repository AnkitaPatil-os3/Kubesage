import type { RouteRecordRaw } from 'vue-router'

/* Some fixed routes in the page, error pages, etc. */
export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'root',
    redirect: '/appRoot',
    children: [
    ],
  },
  // {
  //   path: '/login',
  //   name: 'login',
  //   component: () => import('@/views/login/index.vue'), // Note that the file extension .vue must be included
  //   meta: {
  //     title: 'Login',
  //     withoutTab: true,
  //   },
  // },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/auth/login.vue'), // Note that the file extension .vue should be included here
    meta: {
      title: 'Login',
      withoutTab: true,
    },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/auth/register.vue'), // Note that the file extension .vue should be included here
    meta: {
      title: 'Register',
      withoutTab: true,
    },
  },
  {
    path: '/403',
    name: '403',
    component: () => import('@/views/error/403/index.vue'),
    meta: {
      title: 'User Not Authorized',
      withoutTab: true,
    },
  },
  {
    path: '/404',
    name: '404',
    component: () => import('@/views/error/404/index.vue'),
    meta: {
      title: 'Page Not Found',
      icon: 'icon-park-outline:ghost',
      withoutTab: true,
    },
  },
  {
    path: '/500',
    name: '500',
    component: () => import('@/views/error/500/index.vue'),
    meta: {
      title: 'Server Error',
      icon: 'icon-park-outline:close-wifi',
      withoutTab: true,
    },
  },
  {
    path: '/:pathMatch(.*)*',
    component: () => import('@/views/error/404/index.vue'),
    name: '404',
    meta: {
      title: 'Page Not Found',
      icon: 'icon-park-outline:ghost',
      withoutTab: true,
    },
  },
  // {
  //   name: 'SOC Wazuh',
  //   path: '/soc',
  //   component: () => import('@/views/SOC_Wazuh/soc.vue'), 
  //   // title: 'SOC Wazuh',
  //   // requiresAuth: true,
  //   // icon: 'icon-park-outline:book-one',
  //   // menuType: 'dir',
  //   // componentPath: '/SOC_Wazuh/soc.vue',
  //   // id: 39,
  //   // pid: null,

  // },
  // {
  //   name: 'Wazuh2',
  //   path: '/wazuh2', // Unique path for Wazuh2
  //   title: 'Wazuh2',
  //   requiresAuth: true,
  //   icon: 'carbon:data-error',
  //   // menuType: 'dir',
  //   componentPath: '/Wazuh2/wazuh2.vue',
  //   id: 40,
  //   pid: null,
  // },
  // {
  //   name: 'Wazuh3',
  //   path: '/wazuh3', // Unique path for Wazuh3
  //   title: 'Wazuh3',
  //   requiresAuth: true,
  //   icon: 'carbon:data-error',
  //   // menuType: 'dir',
  //   componentPath: '/Wazuh3/wazuh3.vue',
  //   id: 41,
  //   pid: null,

  // },
]
