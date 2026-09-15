import { expect, test } from '@playwright/test'

test('loads a statement, shows analysis, and confirms deletion', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Contraseña').fill('admin-password')
  await page.getByLabel('Contraseña').focus()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('button', { name: 'Iniciar sesión' })).toBeFocused()
  await page.getByRole('button', { name: 'Iniciar sesión' }).click()
  await expect(page.getByText('Carga una cartola')).toBeVisible()

  await page.locator('input[type="file"]').setInputFiles('../media/cartola_ejemplo_banco_chile.pdf')
  await expect(page.getByText('Movimientos')).toBeVisible()
  await page.getByRole('tab', { name: 'Análisis' }).click()
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: 'Actualizar análisis' }).click()
  await expect(page.getByText('Evolución mensual')).toBeVisible()

  await page.getByRole('tab', { name: 'Cartolas' }).click()
  await page.getByRole('button', { name: 'Volver al historial' }).click()
  await page.getByRole('button', { name: 'Ver detalle' }).click()
  await page.getByRole('button', { name: 'Eliminar' }).click()
  await expect(page.getByText('¿Eliminar cartola?')).toBeVisible()
  await page.getByRole('button', { name: 'Eliminar', exact: true }).click()
  await expect(page.getByText('Aún no hay cartolas cargadas.')).toBeVisible()
})
