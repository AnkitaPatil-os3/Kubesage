import type { MenuOption } from 'naive-ui'
import { router } from '@/router'
import { staticRoutes } from '@/router/routes.static'
import { fetchUserRoutes } from '@/service'
import { useAuthStore } from '@/store/auth'
import { $t, local } from '@/utils'

import { createMenus, createRoutes, generateCacheRoutes } from './helper'

interface RoutesStatus {
  isInitAuthRoute: boolean
  menus: MenuOption[]
  rowRoutes: AppRoute.RowRoute[]
  activeMenu: string | null
  cacheRoutes: string[]
  userRole: string
}

export const useRouteStore = defineStore('route-store', {
  state: (): RoutesStatus => {
    return {
      isInitAuthRoute: false,
      activeMenu: null,
      menus: [],
      rowRoutes: [],
      cacheRoutes: [],
      userRole: 'user', // Default role
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
    
    // Set user role
    setUserRole(role: string) {
      this.userRole = role
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
    
    async initAuthRoute(userRole: string = 'admin') {
      this.isInitAuthRoute = false;
      
      // Set user role
      this.userRole = userRole || local.get('userRole') || 'admin';
      
      // Initialize route information (either static or fetched)
      const rowRoutes = await this.initRouteInfo();
      if (!rowRoutes) {
        window.$message.error($t(`app.getRouteError`));
        return;
      }

      this.rowRoutes = rowRoutes;

      // Generate actual routes and add them to the router
      const routes = createRoutes(rowRoutes, this.userRole);
      router.addRoute(routes);

      // Generate side menu based on user role
      this.menus = createMenus(rowRoutes, this.userRole);

      // Generate the route cache
      this.cacheRoutes = generateCacheRoutes(rowRoutes);

      this.isInitAuthRoute = true;
    }
  },
})
