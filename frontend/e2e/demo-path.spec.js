import { test, expect } from '@playwright/test'

test('demo path: map, jump to the heat cluster, open the alert, check validation', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: /Risk on/ })).toBeVisible()

  await page.getByRole('button', { name: /Heat cluster/ }).click()
  await page.locator('.alert-row', { hasText: 'GBC Site A' }).click()
  await expect(page.getByRole('heading', { name: 'Recommended action' })).toBeVisible()
  await expect(page.getByText('Site HSE Manager (Gulf Build Co.)').first()).toBeVisible()

  await page.getByRole('button', { name: 'Validation', exact: true }).click()
  await expect(page.getByText('Outbreaks detected')).toBeVisible()
  await expect(page.getByText('100%').first()).toBeVisible()
})

test('public view never shows work-site data', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Viewing as').selectOption('public')
  await expect(page.getByRole('status')).toContainText('Public')
  await expect(page.getByRole('button', { name: 'Validation', exact: true })).toHaveCount(0)
  await page.getByRole('button', { name: /Dust storm/ }).click()
  await expect(page.locator('.feed')).not.toContainText('GBC Site')
})
