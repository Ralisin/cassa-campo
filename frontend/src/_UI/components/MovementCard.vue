<script setup>
defineProps({
  movement: {
    type: Object,
    required: true,
  },
})

const euro = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' })
</script>

<template>
  <RouterLink :to="`/movimenti/${movement.id}`" class="block">
    <PCard class="movement-list-card cursor-pointer">
      <template #content>
        <div class="movement-card-layout">
          <PAvatar
            :icon="movement.payment_method === 'carta' ? 'pi pi-credit-card' : 'pi pi-wallet'"
            size="large"
            shape="circle"
            class="movement-card-avatar"
            :class="movement.type === 'uscita' ? '!bg-red-50 !text-red-600' : '!bg-emerald-50 !text-emerald-700'"
          />
          <div class="movement-card-main">
            <p class="truncate text-sm font-black">{{ movement.supplier }}</p>
            <div class="mt-0.5 flex items-center gap-1.5 text-xs text-slate-500">
              <span class="capitalize">{{ movement.payment_method }}</span>
              <span>·</span>
              <span>{{ movement.unit }}</span>
              <span>·</span>
              <span>{{ movement.balance_type }}</span>
              <template v-if="movement.category">
                <span>·</span>
                <span class="capitalize">{{ movement.category }}</span>
              </template>
            </div>
            <div class="mt-1 flex min-w-0 items-center gap-1.5 text-xs text-slate-500">
              <i class="pi pi-user text-[10px]" />
              <span class="truncate">Inserito da {{ movement.creator_name }}</span>
            </div>
            <p v-if="movement.notes" class="mt-1 truncate text-xs text-slate-600">{{ movement.notes }}</p>
          </div>
          <div class="movement-card-summary">
            <PTag v-if="movement.reimbursement_status === 'da_rimborsare'" value="Da rimborsare" severity="warn" class="movement-card-status" />
            <PTag v-else-if="movement.reimbursement_status === 'rimborsato'" value="Rimborsato" severity="success" class="movement-card-status" />
            <p
              class="movement-card-amount"
              :class="movement.type === 'uscita' ? 'text-red-600' : 'text-emerald-700'"
            >
              {{ movement.type === 'uscita' ? '−' : '+' }}{{ euro.format(Number(movement.amount)) }}
            </p>
          </div>
          <i class="movement-card-chevron pi pi-chevron-right text-xs text-slate-400" />
        </div>
      </template>
    </PCard>
  </RouterLink>
</template>
