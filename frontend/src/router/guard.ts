import type { Router } from 'vue-router'
import { useAppStore, useRouteStore, useTabStore } from '@/store'
import { local } from '@/utils'
import axios from 'axios'


const title = import.meta.env.VITE_APP_NAME

export function setupRouterGuard(router: Router) {
  const appStore = useAppStore()
  const routeStore = useRouteStore()
  const tabStore = useTabStore()

  router.beforeEach(async (to, from, next) => {
    // 判断是否是外链，如果是直接打开网页并拦截跳转
    if (to.meta.href) {
      window.open(to.meta.href)
      return false
    }
    // 开始 loadingBar
    appStore.showProgress && window.$loadingBar?.start()

    // 判断有无TOKEN,登录鉴权
    const isLogin = Boolean(local.get('accessToken'))
    if (!isLogin) {
      if (to.name === 'login' || to.name === 'register')
        next()

      if (to.name !== 'login' && to.name !== 'register') {
        const redirect = to.name === '404' ? undefined : to.fullPath
        next({ path: '/login', query: { redirect } })
      }
      return false
    }

    // Get the user info from local storage
    const userInfo = local.get('userInfo')
    console.log('userinfo', userInfo)

    let userRole = 'user' // Default role

    try {
      // Fetch the admin status from the API to determine the role
      const response = await axios.get('https://10.0.32.123:8001/auth/check-admin', {
        headers: {
          Authorization: `Bearer ${local.get('accessToken')}` // If the API requires authorization
        }
      })
      const { is_admin } = response.data

      // Set the user role based on is_admin from the API response
      userRole = is_admin ? 'admin' : 'user'
    } catch (error) {
      console.error('Error fetching user role:', error)
      // If the API call fails, fallback to the default 'user' role
      userRole = 'user'
    }


    // Check if userInfo exists and has roles
    // if (userInfo && userInfo.roles && userInfo.roles.length > 0) {
    //   // Get the first role (assuming a user has at least one role)
    //   const userRole = userInfo.roles[0]

    //   // Now you can use userRole which will be "user" in this example
    //   console.log('User role:', userRole)

    // Check if route requires specific roles
    if (to.meta.roles && !to.meta.roles.includes(userRole)) {
      next({ path: '/403' }) // Redirect to 403 page if user doesn't have permission
      return false
    }

    // 判断路由有无进行初始化
    if (!routeStore.isInitAuthRoute) {
      await routeStore.initAuthRoute(userRole) // Pass the user role to filter routes
      // 动态路由加载完回到根路由
      if (to.name === '404') {
        // 等待权限路由加载好了，回到之前的路由,否则404
        next({
          path: to.fullPath,
          replace: true,
          query: to.query,
          hash: to.hash,
        })
        return false
      }
    }

    // 判断当前页是否在login或register,则定位去首页
    if (to.name === 'login' || to.name === 'register') {
      next({ path: '/' })
      return false
    }

    next()
  })
  router.beforeResolve((to) => {
    // 设置菜单高亮
    routeStore.setActiveMenu(to.meta.activeMenu ?? to.fullPath)
    // 添加tabs
    tabStore.addTab(to)
    // 设置高亮标签;
    tabStore.setCurrentTab(to.path as string)
  })

  router.afterEach((to) => {
    // 修改网页标题
    document.title = `${to.meta.title} - ${title}`
    // 结束 loadingBar
    appStore.showProgress && window.$loadingBar?.finish()
  })
}
