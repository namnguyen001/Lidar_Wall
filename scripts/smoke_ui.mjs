import { spawn, spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const frontend = path.join(root, 'frontend')
const backend = path.join(root, 'backend')
const port = Number(process.env.SMOKE_PORT ?? 8080)
const baseUrl = `http://127.0.0.1:${port}`
const python = process.env.PYTHON ?? (
  process.platform === 'win32' && existsSync(path.join(backend, '.venv', 'Scripts', 'python.exe'))
    ? path.join(backend, '.venv', 'Scripts', 'python.exe')
    : 'python'
)

function run(command, args, cwd) {
  const result = spawnSync(command, args, { cwd, stdio: 'inherit', shell: process.platform === 'win32' })
  if (result.status !== 0) throw new Error(`${command} ${args.join(' ')} failed (${result.status ?? result.signal})`)
}

async function waitForBackend(child) {
  const deadline = Date.now() + 30_000
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`Backend exited early (${child.exitCode})`)
    try {
      const response = await fetch(`${baseUrl}/api/health`)
      if (response.ok) return
    } catch {
      // Keep polling until uvicorn is ready.
    }
    await new Promise(resolve => setTimeout(resolve, 300))
  }
  throw new Error('Backend did not become healthy within 30 seconds')
}

const playwrightPath = path.join(frontend, 'node_modules', 'playwright', 'index.mjs')
if (!existsSync(playwrightPath)) throw new Error('Playwright is missing; install frontend devDependencies first')
const { chromium } = await import(pathToFileURL(playwrightPath).href)

run('node', [path.join(root, 'scripts', 'check_theme_tokens.mjs')], root)
run('npm', ['run', 'build'], frontend)

const backendProcess = spawn(python, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(port)], {
  cwd: backend,
  env: { ...process.env, LIDAR_FORCE_SIM: '1' },
  stdio: ['ignore', 'inherit', 'inherit'],
})

let browser
try {
  await waitForBackend(backendProcess)
  try {
    browser = await chromium.launch({ headless: true })
  } catch {
    console.log('Chromium is not installed; downloading it once with Playwright...')
    run(process.execPath, [path.join(frontend, 'node_modules', 'playwright', 'cli.js'), 'install', 'chromium'], root)
    browser = await chromium.launch({ headless: true })
  }

  let failed = false
  for (const route of ['/', '/control', '/wall']) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
    await page.addInitScript(() => {
      window.__pointFrames = 0
      window.__foregroundPoints = 0
      window.addEventListener('lidar-points', event => {
        window.__pointFrames += 1
        const buffer = event.detail
        const view = new DataView(buffer)
        const count = view.getUint32(8, true)
        const flags = new Uint8Array(buffer, 16 + count * 8, count)
        window.__foregroundPoints = flags.reduce((total, flag) => total + Number((flag & 1) !== 0), 0)
      })
    })
    const errors = []
    page.on('console', message => {
      if (message.type() === 'error') errors.push(`console.error: ${message.text()}`)
    })
    page.on('pageerror', error => errors.push(`pageerror: ${error.stack ?? error.message}`))
    page.on('requestfailed', request => errors.push(`request failed: ${request.method()} ${request.url()} (${request.failure()?.errorText ?? 'unknown'})`))

    const response = await page.goto(`${baseUrl}${route}`, { waitUntil: 'networkidle', timeout: 30_000 }).catch(error => {
      errors.push(`navigation error: ${error.message}`)
      return null
    })
    const testId = route === '/wall' ? 'wall-page' : 'control-page'
    const rendered = await page.getByTestId(testId).count().catch(() => 0)
    await page.waitForTimeout(500)
    const pointFrames = await page.evaluate(() => window.__pointFrames)
    const foregroundPoints = await page.evaluate(() => window.__foregroundPoints)
    const finalPath = new URL(page.url()).pathname
    const orangePixels = await page.locator('canvas').first().evaluate(canvas => {
      const context = canvas.getContext('2d')
      if (!context) return 0
      const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data
      let count = 0
      for (let i = 0; i < pixels.length; i += 4) {
        if (pixels[i] > 150 && pixels[i + 1] < 90 && pixels[i + 2] < 40 && pixels[i + 3] > 0) count += 1
      }
      return count
    }).catch(() => 0)
    await page.screenshot({ path: path.join(root, `smoke-${route === '/' ? 'root' : route.slice(1)}.png`), fullPage: true }).catch(error => {
      errors.push(`screenshot error: ${error.message}`)
    })

    console.log(`\n[${route}] HTTP ${response?.status() ?? 'navigation failed'}; path: ${finalPath}; ${testId}: ${rendered > 0 ? 'FOUND' : 'MISSING'}; scan frames: ${pointFrames}; foreground points: ${foregroundPoints}; orange canvas pixels: ${orangePixels}`)
    for (const error of errors) console.error(`  ${error}`)
    if (!rendered || (route === '/' && finalPath !== '/control')) failed = true
    if ((route === '/' || route === '/control') && (pointFrames === 0 || foregroundPoints === 0 || orangePixels === 0)) failed = true
    if (route === '/control') {
      const api404 = await page.evaluate(async () => {
        const response = await fetch('/api/__smoke_not_found')
        return { status: response.status, contentType: response.headers.get('content-type') ?? '', body: await response.json().catch(() => null) }
      })
      console.log(`[api 404] ${JSON.stringify(api404)}`)
      if (api404.status !== 404 || !api404.contentType.includes('application/json')) failed = true

      const timeOrigin = await page.evaluate(() => performance.timeOrigin)
      await page.getByRole('button', { name: 'Cài đặt' }).click()
      const controlTheme = page.getByRole('group', { name: 'Giao diện điều khiển' })
      await controlTheme.getByRole('button', { name: 'Tối' }).click()
      await page.waitForFunction(() => document.documentElement.dataset.theme === 'dark')
      await controlTheme.getByRole('button', { name: 'Sáng' }).click()
      await page.waitForFunction(() => document.documentElement.dataset.theme === 'light')
      const persistedTheme = await page.evaluate(async () => {
        const config = await fetch('/api/config').then(response => response.json())
        return { theme: config.ui.theme, wallTheme: config.ui.wallTheme }
      })
      const stillSameDocument = await page.evaluate(initial => performance.timeOrigin === initial, timeOrigin)
      console.log(`[themes] ${JSON.stringify(persistedTheme)}; no reload: ${stillSameDocument}`)
      await page.screenshot({ path: path.join(root, 'smoke-control-light.png'), fullPage: true })
      if (!stillSameDocument || persistedTheme.theme !== 'light' || persistedTheme.wallTheme !== 'dark') failed = true
      await page.evaluate(() => window.dispatchEvent(new ErrorEvent('error', { message: 'Smoke global error check' })))
      const globalError = await page.getByRole('alert').innerText().catch(() => '')
      console.log(`[global error banner] ${globalError}`)
      if (!globalError.includes('Smoke global error check')) failed = true
    }
    if (route === '/wall') {
      const wallTheme = await page.evaluate(() => document.documentElement.dataset.theme)
      console.log(`[wall theme] ${wallTheme}`)
      if (wallTheme !== 'dark') failed = true
    }
    await page.close()
  }

  const errorPage = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const errorLogs = []
  errorPage.on('console', message => {
    if (message.type() === 'error') errorLogs.push(`console.error: ${message.text()}`)
  })
  errorPage.on('pageerror', error => errorLogs.push(`pageerror: ${error.stack ?? error.message}`))
  await errorPage.route('**/api/config', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ ui: { theme: 'light', wallTheme: 'dark' }, lidars: [null], zones: [] }),
  }))
  await errorPage.goto(`${baseUrl}/control`, { waitUntil: 'networkidle' })
  const boundaryHeading = await errorPage.getByRole('heading', { name: 'Ứng dụng gặp lỗi' }).count()
  const boundaryStack = await errorPage.locator('pre').innerText().catch(() => '')
  console.log(`\n[ErrorBoundary] visible: ${boundaryHeading > 0}; stack includes TypeError: ${boundaryStack.includes('TypeError')}`)
  for (const error of errorLogs) console.error(`  ${error}`)
  if (!boundaryHeading || !boundaryStack.includes('TypeError')) failed = true
  await errorPage.close()

  await browser.close()
  browser = null
  if (failed) process.exitCode = 1
} finally {
  await browser?.close()
  backendProcess.kill('SIGTERM')
  await new Promise(resolve => {
    if (backendProcess.exitCode !== null) return resolve()
    backendProcess.once('exit', resolve)
    setTimeout(() => {
      backendProcess.kill('SIGKILL')
      resolve()
    }, 5_000).unref()
  })
}