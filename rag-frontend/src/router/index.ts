import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    redirect: '/rag',
  },
  {
    path: '/rag',
    name: 'Rag',
    component: () => import('@/views/RagView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
