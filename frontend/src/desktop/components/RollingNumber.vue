<script setup>
// Odometer-style number: each digit is a vertical 0-9 strip that slides to the
// target digit, so changing value rolls the digits up/down. Non-digit chars
// (currency symbol, separators, minus) are rendered statically.
defineProps({
  value: { type: String, default: '' },
})

function isDigit(ch) {
  return ch >= '0' && ch <= '9'
}
</script>

<template>
  <span class="roll" aria-hidden="true">
    <span
      v-for="(ch, i) in value.split('')"
      :key="i"
      class="roll__cell"
      :class="{ 'roll__cell--digit': isDigit(ch) }"
    >
      <span v-if="isDigit(ch)" class="roll__strip" :style="{ transform: `translateY(${-Number(ch)}em)` }">
        <span v-for="d in 10" :key="d" class="roll__digit">{{ d - 1 }}</span>
      </span>
      <span v-else class="roll__sep">{{ ch === ' ' ? ' ' : ch }}</span>
    </span>
  </span>
</template>

<style scoped>
.roll {
  display: inline-flex;
  align-items: flex-start;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
.roll__cell {
  display: inline-block;
  height: 1em;
  line-height: 1em;
}
/* Window onto a single digit: anchored to the TOP so translateY(-Nem) on the
   strip lands digit N exactly in view. */
.roll__cell--digit {
  overflow: hidden;
  vertical-align: top;
}
.roll__strip {
  display: block;
  transition: transform 0.55s cubic-bezier(0.22, 1, 0.36, 1);
  will-change: transform;
}
.roll__digit {
  display: block;
  height: 1em;
  line-height: 1em;
  text-align: center;
}
.roll__sep {
  display: inline-block;
  height: 1em;
  line-height: 1em;
}
@media (prefers-reduced-motion: reduce) {
  .roll__strip { transition: none; }
}
</style>
