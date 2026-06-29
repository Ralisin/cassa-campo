import { expect, test } from '@playwright/test'

test('login exposes password reset flow', async ({ page }) => {
  await page.goto('/login')

  await expect(page.getByText('Cassa Campo').first()).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Bentornato' })).toBeVisible()
  await expect(page.getByLabel('Email')).toBeVisible()
  await expect(page.getByPlaceholder('La tua password')).toBeVisible()

  await page.getByRole('button', { name: /password dimenticata/i }).click()
  await expect(page).toHaveURL(/\/reset-password$/)
  await expect(page.getByRole('heading', { name: 'Password' })).toBeVisible()
  await expect(page.getByLabel('Email')).toBeVisible()
})

test('reset confirmation page asks for the new password twice', async ({ page }) => {
  await page.goto('/reset-password?token=fake-token')

  await expect(page.getByRole('heading', { name: 'Password' })).toBeVisible()
  await expect(page.getByText('Nuova password', { exact: true })).toBeVisible()
  await expect(page.getByText('Ripeti password', { exact: true })).toBeVisible()
  await expect(page.locator('input[type="password"]')).toHaveCount(2)
  await expect(page.getByRole('button', { name: /aggiorna password/i })).toBeVisible()
})
