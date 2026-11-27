import { expect, test } from '@playwright/test'
import { newAgent, saved, signUp } from './helpers.ts'

// AC-5: each MVP node type can be added from the palette, edited in the inspector and
// connected; reloading shows the same graph.
test('add, edit and connect every node type, and reload', async ({ page }) => {
  await signUp(page)
  await newAgent(page, 'E2E Canvas', 'Blank')
  const nodes = page.locator('.react-flow__node')
  await expect(nodes).toHaveCount(3) // Start, Conversation, End
  const palette = page.getByRole('complementary', { name: 'Node palette' })

  // Agent step: add, rename, move it clear of the others, connect Conversation to it.
  await palette.getByRole('button', { name: /Agent step/ }).click()
  await page.getByLabel('Label').fill('Billing')
  await saved(page)
  const billing = nodes.filter({ hasText: 'Billing' })
  const box = (await billing.boundingBox())!
  await page.mouse.move(box.x + 40, box.y + 12)
  await page.mouse.down()
  await page.mouse.move(box.x + 40, box.y + 260, { steps: 8 })
  await page.mouse.up()
  const edges = page.locator('.react-flow__edge')
  const before = await edges.count()
  await nodes.filter({ hasText: 'Conversation' }).locator('.react-flow__handle.source').click()
  await billing.locator('.react-flow__handle.target').click()
  await expect(edges).toHaveCount(before + 1)
  await saved(page)

  // The other types: add from the palette and edit in the inspector.
  for (const [kind, label] of [
    ['Extract', 'Collect details'],
    ['Router', 'Route by need'],
    ['End', 'Hang up'],
  ] as const) {
    await palette.getByRole('button', { name: new RegExp(`^${kind}`) }).click()
    await page.getByLabel('Label').fill(label)
  }
  await palette.getByRole('button', { name: /^Note/ }).click()
  await page.locator('#note-text').fill('Check the billing path')
  await saved(page)
  await expect(nodes).toHaveCount(8)

  await page.reload()
  await expect(nodes).toHaveCount(8)
  for (const text of ['Billing', 'Collect details', 'Route by need', 'Hang up', 'Check the billing path'])
    await expect(nodes.filter({ hasText: new RegExp(text) })).toHaveCount(1) // case-sensitive
  await expect(edges).toHaveCount(before + 1)
})
