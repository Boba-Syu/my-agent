import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/home',
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('@/pages/HomePage.vue'),
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/pages/ChatPage.vue'),
  },
  {
    path: '/records',
    name: 'Records',
    component: () => import('@/pages/RecordsPage.vue'),
  },
  {
    path: '/stats',
    name: 'Stats',
    component: () => import('@/pages/StatsPage.vue'),
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
