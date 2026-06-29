<script setup>
// Placeholder that mirrors MovementCard's exact layout so loading lists keep
// the same rhythm as the loaded state.
</script>

<template>
  <PCard class="movement-list-card">
    <template #content>
      <div class="movement-card-layout">
        <Skel circle w="2.75rem" h="2.75rem" class="movement-card-avatar" />
        <div class="movement-card-main">
          <Skel w="55%" h="0.85rem" />
          <Skel w="78%" h="0.7rem" class="mt-2" />
          <Skel w="48%" h="0.7rem" class="mt-1.5" />
        </div>
        <div class="movement-card-summary">
          <Skel w="4.5rem" h="0.95rem" />
        </div>
      </div>
    </template>
  </PCard>
</template>
