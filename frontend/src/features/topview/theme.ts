export interface TopViewTheme {
  canvasBackground: string
  grid: string
  ring: string
  ringLabel: string
  axisX: string
  axisY: string
  rawPointMuted: string
  rawPointForeground: string
  scanArea: string
  scanFill: string
  wallQuad: string
  wallHandle: string
  blob: string
  zone: string
  hudBackground: string
  hudText: string
}

export function readTopViewTheme(): TopViewTheme {
  const styles = getComputedStyle(document.documentElement)
  const value = (name: string) => styles.getPropertyValue(name).trim()
  return {
    canvasBackground: value('--canvas-bg'),
    grid: value('--grid'),
    ring: value('--ring'),
    ringLabel: value('--muted'),
    axisX: value('--axis-x'),
    axisY: value('--axis-y'),
    rawPointMuted: value('--point-muted'),
    rawPointForeground: value('--point-foreground'),
    scanArea: value('--accent-amber'),
    scanFill: value('--scan-fill'),
    wallQuad: value('--accent-magenta'),
    wallHandle: value('--accent-cyan'),
    blob: value('--blob'),
    zone: value('--accent-cyan'),
    hudBackground: value('--surface'),
    hudText: value('--text'),
  }
}