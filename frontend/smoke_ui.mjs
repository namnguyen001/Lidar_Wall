import { chromium } from 'playwright';
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');

async function run() {
    console.log('Building Frontend...');
    // We assume FE is built since the start scripts handle it or it was built before. 
    // To be safe we could build it, but let's assume it's built to save time.
    
    console.log('Starting Backend...');
    const pythonExe = path.join(rootDir, 'backend', '.venv', 'Scripts', 'python.exe');
    const serverProcess = spawn(pythonExe, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8080'], {
        cwd: path.join(rootDir, 'backend'),
        env: { ...process.env, LIDAR_FORCE_SIM: '1' }
    });

    let serverReady = false;
    serverProcess.stdout.on('data', (data) => {
        const str = data.toString();
        // console.log('[Server OUT]', str.trim());
        if (str.includes('Uvicorn running on')) serverReady = true;
    });
    serverProcess.stderr.on('data', (data) => {
        const str = data.toString();
        // console.log('[Server ERR]', str.trim());
        if (str.includes('Uvicorn running on')) serverReady = true;
    });

    // Wait for server to be ready
    let retries = 30;
    while (!serverReady && retries > 0) {
        await new Promise(r => setTimeout(r, 500));
        retries--;
    }

    if (!serverReady) {
        console.error('Server failed to start');
        serverProcess.kill();
        process.exit(1);
    }

    console.log('Server is ready. Launching browser...');
    const browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();

    let hasErrors = false;
    page.on('console', msg => {
        if (msg.type() === 'error') {
            console.error(`[Console Error] ${msg.text()}`);
            hasErrors = true;
        }
    });
    page.on('pageerror', error => {
        console.error(`[Page Error] ${error.message}`);
        hasErrors = true;
    });
    page.on('requestfailed', request => {
        console.error(`[Request Failed] ${request.url()} - ${request.failure()?.errorText}`);
        hasErrors = true;
    });

    const routes = [
        { url: 'http://127.0.0.1:8080/', name: 'root', testId: 'app-root' },
        { url: 'http://127.0.0.1:8080/control', name: 'control', testId: 'control-page' },
        { url: 'http://127.0.0.1:8080/wall', name: 'wall', testId: 'wall-page' }
    ];

    let failed = false;

    for (const route of routes) {
        console.log(`\nTesting ${route.url}...`);
        await page.goto(route.url, { waitUntil: 'networkidle', timeout: 10000 }).catch(e => console.error(e));
        
        await page.screenshot({ path: path.join(rootDir, `smoke-${route.name}.png`) });
        console.log(`Saved screenshot to smoke-${route.name}.png`);

        try {
            await page.waitForSelector(`[data-testid="${route.testId}"]`, { timeout: 3000 });
            console.log(`✅ Found data-testid="${route.testId}"`);
        } catch (e) {
            console.error(`❌ Could not find data-testid="${route.testId}"`);
            failed = true;
        }
    }

    await browser.close();
    serverProcess.kill();

    if (failed || hasErrors) {
        console.error('\nSmoke test FAILED due to missing elements or console errors.');
        process.exit(1);
    } else {
        console.log('\nSmoke test PASSED!');
        process.exit(0);
    }
}

run().catch(e => {
    console.error(e);
    process.exit(1);
});
