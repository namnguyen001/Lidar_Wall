import { readFileSync, readdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const sourceRoot = path.join(root, 'frontend', 'src')
const tokenFiles = new Set([
  path.join(sourceRoot, 'index.css'),
  path.join(sourceRoot, 'features', 'topview', 'theme.ts'),
])
const forbidden = /#[\da-fA-F]{3,8}\b|\b(?:text-white|bg-black|text-black)\b/g
const violations = []

function visit(directory) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const filePath = path.join(directory, entry.name)
    if (entry.isDirectory()) {
      if (entry.name !== 'assets') visit(filePath)
      continue
    }
    if (!/\.(?:css|tsx?|jsx?)$/.test(entry.name) || tokenFiles.has(filePath)) continue
    const contents = readFileSync(filePath, 'utf8')
    for (const match of contents.matchAll(forbidden)) {
      violations.push(`${path.relative(root, filePath)}: ${match[0]}`)
    }
  }
}

visit(sourceRoot)
if (violations.length) {
  console.error(`Hardcoded colors found outside theme tokens:\n${violations.join('\n')}`)
  process.exitCode = 1
} else {
  console.log('Theme token check passed.')
}
