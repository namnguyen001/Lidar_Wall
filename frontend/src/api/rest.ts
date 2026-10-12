const API_URL = '/api'

export async function fetchConfig() {
  const res = await fetch(`${API_URL}/config`)
  if (!res.ok) throw new Error(`Không tải được cấu hình (${res.status})`)
  return res.json()
}

export async function fetchHealth() {
  const res = await fetch(`${API_URL}/health`)
  return res.json()
}

export async function fetchLidars() {
  const res = await fetch(`${API_URL}/lidars`)
  return res.json()
}

export async function connectLidar(id: string) {
  const res = await fetch(`${API_URL}/lidars/${id}/connect`, { method: 'POST' })
  return res.json()
}

export async function disconnectLidar(id: string) {
  const res = await fetch(`${API_URL}/lidars/${id}/disconnect`, { method: 'POST' })
  return res.json()
}

export const api = {
  post: async (path: string, body: any) => {
    const res = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },
  put: async (path: string, body: any) => {
    const res = await fetch(path, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  }
}
