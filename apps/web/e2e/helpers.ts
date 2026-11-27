import { expect, type Page } from '@playwright/test'

/** A fresh account per test (open sign-up: the first user owns the workspace). */
export async function signUp(page: Page) {
  const email = `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 7)}@example.com`
  await page.goto('/sign-up')
  await page.getByLabel('Name').fill('E2E Tester')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill('correct horse battery staple')
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page).toHaveURL(/\/agents$/)
}

export async function newAgent(page: Page, name: string, template: 'Blank' | 'Dental receptionist') {
  await page.getByRole('button', { name: 'New agent' }).first().click()
  await page.getByLabel('Name').fill(name)
  await page.getByText(template, { exact: true }).click()
  await page.getByRole('button', { name: 'Create agent' }).click()
  await expect(page).toHaveURL(/\/agents\/[0-9a-f-]+$/)
  await expect(page.getByText('Saved', { exact: true })).toBeVisible()
}

export async function saved(page: Page) {
  await expect(page.getByText('Saved', { exact: true })).toBeVisible()
}

/** Send a caller message and wait for the agent's complete reply bubble. */
export async function say(page: Page, text: string) {
  const console = page.getByRole('complementary', { name: 'Test console' })
  await console.getByLabel('Message as the caller').fill(text)
  await console.getByRole('button', { name: 'Send' }).click()
}
