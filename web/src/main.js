import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import './styles/index.scss'
import App from './App.vue'
import { vClickable } from './directives/clickable'

const app = createApp(App)
app.directive('clickable', vClickable)
app.use(createPinia())
app.use(router)
app.mount('#app')
