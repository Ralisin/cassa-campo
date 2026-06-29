<script setup>
// Tiny presentational skeleton block. Compose several of these inside the real
// layout containers so the placeholder mirrors the actual screen shape.
defineProps({
  w: { type: [String, Number], default: '100%' },
  h: { type: [String, Number], default: '1rem' },
  r: { type: String, default: '' },
  circle: { type: Boolean, default: false },
  soft: { type: Boolean, default: false },
  dark: { type: Boolean, default: false },
})

function size(value) {
  return typeof value === 'number' ? `${value}px` : value
}
</script>

<template>
  <div
    class="skel"
    :class="{ 'skel--circle': circle, 'skel--soft': soft, 'skel--dark': dark }"
    :style="{ width: size(w), height: size(h), borderRadius: circle ? undefined : (r || undefined) }"
    aria-hidden="true"
  />
</template>
