<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: String, required: true },
  icon: { type: String, default: 'pi pi-wallet' },
  tone: { type: String, default: 'forest' },
  hint: { type: String, default: '' },
})
</script>

<template>
  <article class="dk-kpi" :class="`dk-kpi--${tone}`">
    <span class="dk-kpi__icon"><i :class="icon" /></span>
    <div class="dk-kpi__body">
      <p class="dk-kpi__label">{{ label }}</p>
      <p class="dk-kpi__value">{{ value }}</p>
      <p v-if="hint" class="dk-kpi__hint">{{ hint }}</p>
    </div>
  </article>
</template>
