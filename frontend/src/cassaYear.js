export function formatCassaYear(kind, year) {
  return kind === 'anno' ? `${year - 1}/${year}` : String(year)
}

export function defaultCassaYears(kind, today = new Date()) {
  const currentYear = today.getFullYear()
  if (kind === 'campo') return { startYear: currentYear, year: currentYear }

  const startYear = today.getMonth() >= 8 ? currentYear : currentYear - 1
  return { startYear, year: startYear + 1 }
}

export function validCassaYears(kind, startYear, year) {
  if (!Number.isInteger(year) || year < 2000 || year > 2100) return false
  return kind === 'campo' || (
    Number.isInteger(startYear) && startYear >= 1999 && year === startYear + 1
  )
}
