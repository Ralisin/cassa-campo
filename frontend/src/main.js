import { createPinia } from 'pinia'
import { createApp } from 'vue'
import { definePreset } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import Button from 'primevue/button'
import Avatar from 'primevue/avatar'
import Card from 'primevue/card'
import DatePicker from 'primevue/datepicker'
import DataView from 'primevue/dataview'
import Dialog from 'primevue/dialog'
import Divider from 'primevue/divider'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Menu from 'primevue/menu'
import Password from 'primevue/password'
import Select from 'primevue/select'
import Skeleton from 'primevue/skeleton'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import Toolbar from 'primevue/toolbar'
import ToggleSwitch from 'primevue/toggleswitch'

import App from '@/_UI/layout/App.vue'
import router from './router'
import 'primeicons/primeicons.css'
import './style.css'

const CassaCampoPreset = definePreset(Aura, {
  semantic: {
    primary: {
      50: '#edf7f1',
      100: '#d5ecdd',
      200: '#acd9be',
      300: '#78bd98',
      400: '#509c74',
      500: '#347d59',
      600: '#286448',
      700: '#224f3b',
      800: '#1d4031',
      900: '#12372a',
      950: '#092017',
    },
  },
})

createApp(App)
  .use(createPinia())
  .use(router)
  .use(PrimeVue, {
    theme: {
      preset: CassaCampoPreset,
      options: { darkModeSelector: false, cssLayer: { name: 'primevue', order: 'tailwind-base, primevue, tailwind-utilities' } },
    },
  })
  .component('PAvatar', Avatar)
  .component('PButton', Button)
  .component('PCard', Card)
  .component('PDatePicker', DatePicker)
  .component('PDataView', DataView)
  .component('PDialog', Dialog)
  .component('PDivider', Divider)
  .component('PIconField', IconField)
  .component('PInputIcon', InputIcon)
  .component('PInputNumber', InputNumber)
  .component('PInputText', InputText)
  .component('PMessage', Message)
  .component('PMenu', Menu)
  .component('PPassword', Password)
  .component('PSelect', Select)
  .component('PSkeleton', Skeleton)
  .component('PTag', Tag)
  .component('PTextarea', Textarea)
  .component('PToolbar', Toolbar)
  .component('PToggleSwitch', ToggleSwitch)
  .mount('#app')
