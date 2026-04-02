import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/novels' },
    {
      path: '/novels',
      name: 'Novels',
      component: () => import('../views/NovelsView.vue'),
    },
    {
      path: '/novels/:slug/characters',
      name: 'Characters',
      component: () => import('../views/CharactersView.vue'),
    },
    {
      path: '/novels/:slug/script',
      name: 'Script',
      component: () => import('../views/ScriptView.vue'),
    },
    {
      path: '/tasks',
      name: 'Tasks',
      component: () => import('../views/TasksView.vue'),
    },
  ],
})

export default router
