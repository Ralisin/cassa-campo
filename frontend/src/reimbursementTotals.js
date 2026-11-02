export function summarizeReimbursements(movements, performerId = 'tutti') {
  const totals = {
    pendingCents: 0,
    reimbursedCents: 0,
    pendingCount: 0,
    reimbursedCount: 0,
  }

  for (const movement of movements) {
    if (performerId !== 'tutti' && movement.performed_by_id !== performerId) continue
    const cents = Math.round(Number(movement.amount) * 100)
    if (movement.reimbursement_status === 'rimborsato') {
      totals.reimbursedCents += cents
      totals.reimbursedCount += 1
    } else if (movement.reimbursement_status === 'da_rimborsare') {
      totals.pendingCents += cents
      totals.pendingCount += 1
    }
  }

  return {
    pendingAmount: totals.pendingCents / 100,
    reimbursedAmount: totals.reimbursedCents / 100,
    pendingCount: totals.pendingCount,
    reimbursedCount: totals.reimbursedCount,
  }
}
