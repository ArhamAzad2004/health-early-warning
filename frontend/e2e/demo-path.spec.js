import { test, expect } from '@playwright/test'

test('first visit starts the guided tour once', async ({ page }) => {
  await page.goto('/')
  const tour = page.getByRole('dialog', { name: 'The risk map' })
  await expect(tour).toBeVisible()
  await expect(tour).toBeFocused()
  for (const title of ['Replay summer 2025', 'Alerts and what to do', 'Who is looking', 'Proof it works']) {
    await page.getByRole('button', { name: 'Next' }).click()
    await expect(page.getByRole('dialog', { name: title })).toBeVisible()
  }
  await page.getByRole('button', { name: 'Finish' }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await page.reload()
  await expect(page.getByRole('heading', { name: /Risk on/ })).toBeVisible()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await page.getByRole('button', { name: 'Take the tour' }).click()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Take the tour' })).toBeFocused()
})

test.describe('after the tour', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem('sentinel-tour-seen', '1'))
  })

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
})
