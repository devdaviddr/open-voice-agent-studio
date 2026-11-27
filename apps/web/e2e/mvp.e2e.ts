import { expect, test } from '@playwright/test'
import { newAgent, saved, say, signUp } from './helpers.ts'

// NFR-1: sign-up → template → edit → publish → chat → memory recall. Also AC-15, AC-17.
test('build, publish, talk to and be remembered by an agent', async ({ page }) => {
  await signUp(page)
  await newAgent(page, 'E2E Receptionist', 'Blank')

  // Edit: a step prompt, and long-term memory on.
  await page.locator('.react-flow__node', { hasText: 'Conversation' }).click()
  await page.getByLabel('Step prompt').fill('Greet the caller and help them book.')
  await saved(page)
  await page.locator('.react-flow__pane').click({ position: { x: 20, y: 20 } })
  await page.getByRole('switch', { name: /Long-term memory/ }).click()
  await saved(page)

  // Publish v1.
  await page.getByRole('button', { name: 'Publish' }).click()
  await page.getByLabel('What changed?').fill('First version')
  await page.getByRole('button', { name: 'Publish and go live' }).click()
  await expect(page.getByText('Published v1')).toBeVisible()

  // Chat with v1 as test caller "ana", with read-aloud on (AC-17: TTS gets the agent's voice).
  const tts: { text: string; voice: string }[] = []
  await page.route('**/api/v1/tts', async (route) => {
    tts.push(route.request().postDataJSON())
    await route.fulfill({ status: 503, body: 'no TTS in e2e' })
  })
  await page.getByRole('button', { name: 'Test' }).click()
  const panel = page.getByRole('complementary', { name: 'Test console' })
  await panel.getByRole('combobox', { name: 'Run' }).click()
  await page.getByRole('option', { name: /v1/ }).click()
  await panel.getByLabel('Test caller ID').fill('ana')
  await panel.getByRole('button', { name: 'Read replies aloud' }).click()
  await panel.getByRole('button', { name: 'Start session' }).click()
  await expect(panel.getByText('no memories of this caller yet')).toBeVisible()

  await say(page, 'Hi, my dog is called Rex')
  await expect(panel.getByText('You said: Hi, my dog is called Rex')).toBeVisible()
  await expect.poll(() => tts.map((t) => t.text)).toContain('You said: Hi, my dog is called Rex')
  expect(tts.every((t) => t.voice === 'af_heart')).toBe(true)
  await panel.getByRole('button', { name: 'End session' }).click()

  // AC-15: the memory job saves the fact after the session ends.
  await expect(async () => {
    await page.reload()
    await expect(page.getByRole('button', { name: 'Memories (1)' })).toBeVisible({ timeout: 2_000 })
  }).toPass({ timeout: 90_000 })
  await page.getByRole('button', { name: 'Memories (1)' }).click()
  await expect(page.getByText('Their dog is called Rex.')).toBeVisible()
  await page.keyboard.press('Escape')

  // A new session for ana recalls it.
  await page.getByRole('button', { name: 'Test' }).click()
  await panel.getByLabel('Test caller ID').fill('ana')
  await panel.getByRole('button', { name: 'Start session' }).click()
  await expect(panel.getByText('remembered: Their dog is called Rex.')).toBeVisible()
  await say(page, 'Do you remember me?')
  await expect(panel.getByText('Yes, I remember: Their dog is called Rex.')).toBeVisible()
  await panel.getByRole('button', { name: 'End session' }).click()

  // Deleting the memory in the UI means the next session does not recall it.
  await panel.getByRole('button', { name: 'Close test console' }).click()
  await page.getByRole('button', { name: /Memories \(/ }).click()
  await page.getByRole('button', { name: 'Delete memory: Their dog is called Rex.' }).click()
  await expect(page.getByText('Their dog is called Rex.')).toHaveCount(0)
  await page.keyboard.press('Escape')
  await page.getByRole('button', { name: 'Test' }).click()
  await panel.getByLabel('Test caller ID').fill('ana')
  await panel.getByRole('button', { name: 'Start session' }).click()
  await expect(panel.getByText('no memories of this caller yet')).toBeVisible()
})
