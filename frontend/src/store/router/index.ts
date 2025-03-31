import type { MenuOption } from 'naive-ui'
import { router } from '@/router'
import { staticRoutes } from '@/router/routes.static'
// import { useDynamicRoutes } from '@/router/routes.static'
import { fetchUserRoutes } from '@/service'
import { useAuthStore } from '@/store/auth'
import { $t, local } from '@/utils'
// import { defineAsyncComponent } from 'vue';
// import { RouteRecordRaw } from 'vue-router';

import { createMenus, createRoutes, generateCacheRoutes } from './helper'

interface RoutesStatus {
  isInitAuthRoute: boolean
  menus: MenuOption[]
  rowRoutes: AppRoute.RowRoute[]
  activeMenu: string | null
  cacheRoutes: string[]
}
export const useRouteStore = defineStore('route-store', {
  state: (): RoutesStatus => {
    return {
      isInitAuthRoute: false,
      activeMenu: null,
      menus: [],
      rowRoutes: [],
      cacheRoutes: [],
    }
  },
  actions: {
    resetRouteStore() {
      this.resetRoutes()
      this.$reset()
    },
    resetRoutes() {
      if (router.hasRoute('appRoot'))
        router.removeRoute('appRoot')
    },
    // set the currently highlighted menu key
    setActiveMenu(key: string) {
      this.activeMenu = key
    },

    async initRouteInfo() {
      if (import.meta.env.VITE_ROUTE_LOAD_MODE === 'dynamic') {
        const userInfo = local.get('userInfo')

        if (!userInfo || !userInfo.id) {
          const authStore = useAuthStore()
          authStore.logout()
          return
        }

        // Get user's route
        const { data } = await fetchUserRoutes({
          id: userInfo.id,
        })

        if (!data)
          return

        return data
      }
      else {
        this.rowRoutes = staticRoutes
        return staticRoutes
      }
    },
    async initAuthRoute() {
  this.isInitAuthRoute = false;

  // Initialize route information (either static or fetched)
  const rowRoutes = await this.initRouteInfo();
  if (!rowRoutes) {
    window.$message.error($t(`app.getRouteError`));
    return;
  }

  this.rowRoutes = rowRoutes;

  // Generate actual routes and add them to the router
  const routes = createRoutes(rowRoutes);
  router.addRoute(routes);

  // Assuming `useDynamicRoutes` returns an array of dynamic routes
  
  
  // const dynamicRoutes = useDynamicRoutes();
  // console.log(dynamicRoutes)
  
  // const validateRoute = (route: any): RouteRecordRaw => {
  //   // Use defineAsyncComponent for dynamic components
  //   const component = route.componentPath ? defineAsyncComponent(() => import(`@/views${route.componentPath}.vue`)) : void 0;
  
  //   return {
  //     ...route,
  //     component,
  //     redirect: route.redirect || undefined,
  //   };
  // };
  
  // // Process the routes
  // if (Array.isArray(dynamicRoutes)) {
  //   dynamicRoutes.forEach((route) => {
  //     const validatedRoute = validateRoute(route);
  //     router.addRoute(validatedRoute);
  //   });
  // } else {
  //   const validatedRoute = validateRoute(dynamicRoutes);
  //   router.addRoute(validatedRoute);
  // }
  

  // Generate side menu
  this.menus = createMenus(rowRoutes);

  // Generate the route cache
  this.cacheRoutes = generateCacheRoutes(rowRoutes);

  this.isInitAuthRoute = true;
}

  },
})
