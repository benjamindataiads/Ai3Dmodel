import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

// Routes
const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('./components/ProjectList.vue'),
  },
  {
    path: '/project/:id',
    name: 'project',
    component: () => import('./components/ProjectView.vue'),
  },
  {
    path: '/docs',
    name: 'docs',
    component: () => import('./components/Documentation.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
