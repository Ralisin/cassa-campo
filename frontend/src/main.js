import { createPinia } from 'pinia'
import { createApp } from 'vue'
import { definePreset } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import ConfirmationService from 'primevue/confirmationservice'
import Tooltip from 'primevue/tooltip'
import Button from 'primevue/button'
import Avatar from 'primevue/avatar'
import Card from 'primevue/card'
import Chart from 'primevue/chart'
import Column from 'primevue/column'
import ConfirmDialog from 'primevue/confirmdialog'
import DataTable from 'primevue/datatable'
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
import Popover from 'primevue/popover'
import ProgressBar from 'primevue/progressbar'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import Skeleton from 'primevue/skeleton'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import Toolbar from 'primevue/toolbar'
import ToggleSwitch from 'primevue/toggleswitch'

import App from '@/_UI/layout/App.vue'
import router from './router'
import 'primeicons/primeicons.css'
import './style.css'
import './desktop.css'

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

const app = createApp(App)
  .use(createPinia())
  .use(router)
  .use(PrimeVue, {
    theme: {
      preset: CassaCampoPreset,
      options: { darkModeSelector: false, cssLayer: { name: 'primevue', order: 'tailwind-base, primevue, tailwind-utilities' } },
    },
  })
  .use(ConfirmationService)
  .directive('tooltip', Tooltip)
  .component('PAvatar', Avatar)
  .component('PButton', Button)
  .component('PCard', Card)
  .component('PChart', Chart)
  .component('PColumn', Column)
  .component('PConfirmDialog', ConfirmDialog)
  .component('PDataTable', DataTable)
  .component('PDatePicker', DatePicker)
  .component('PDataView', DataView)
  .component('PDialog', Dialog)
  .component('PDivider', Divider)
  .component('PIconField', IconField)
  .component('PProgressBar', ProgressBar)
  .component('PInputIcon', InputIcon)
  .component('PInputNumber', InputNumber)
  .component('PInputText', InputText)
  .component('PMessage', Message)
  .component('PMenu', Menu)
  .component('PPassword', Password)
  .component('PPopover', Popover)
  .component('PSelect', Select)
  .component('PSelectButton', SelectButton)
  .component('PSkeleton', Skeleton)
  .component('PTag', Tag)
  .component('PTextarea', Textarea)
  .component('PToolbar', Toolbar)
  .component('PToggleSwitch', ToggleSwitch)

// Mount only after the router has resolved the initial navigation (incl. the
// auth guard's loadUser). This avoids the flash where the desktop shell renders
// on '/' before an invalid token redirects to /login on a hard reload.
router.isReady().then(() => app.mount('#app'))
