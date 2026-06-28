<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
})
</script>

<template>
  <div class="dk-page-header">
    <div class="min-w-0">
      <h2 class="dk-page-header__title">{{ title }}</h2>
      <p v-if="subtitle" class="dk-page-header__subtitle">{{ subtitle }}</p>
    </div>
    <div class="dk-page-header__actions">
      <slot name="actions" />
    </div>
  </div>
</template>
