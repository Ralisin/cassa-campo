<script setup>
// Renders the reimbursement status of a movement consistently across desktop
// tables and detail panels. Falls back to nothing when there is no status.
defineProps({
  status: { type: String, default: 'nessuno' },
})

const MAP = {
  da_rimborsare: { label: 'Da rimborsare', severity: 'warn' },
  rimborsato: { label: 'Rimborsato', severity: 'success' },
}
</script>

<template>
  <PTag
    v-if="MAP[status]"
    :value="MAP[status].label"
    :severity="MAP[status].severity"
  />
  <span v-else class="dk-muted">—</span>
</template>
