<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  icon: { type: String, default: '' },
  empty: { type: Boolean, default: false },
  emptyText: { type: String, default: 'Nessun dato disponibile' },
})
</script>

<template>
  <section class="dk-card dk-chart-card">
    <header class="dk-card__head">
      <div class="min-w-0">
        <h3 class="dk-card__title">
          <i v-if="icon" :class="icon" class="dk-card__title-icon" />
          {{ title }}
        </h3>
        <p v-if="subtitle" class="dk-card__subtitle">{{ subtitle }}</p>
      </div>
      <slot name="actions" />
    </header>
    <div class="dk-chart-card__body">
      <div v-if="empty" class="dk-chart-card__empty">
        <i class="pi pi-chart-bar" />
        <span>{{ emptyText }}</span>
      </div>
      <slot v-else />
    </div>
  </section>
</template>
