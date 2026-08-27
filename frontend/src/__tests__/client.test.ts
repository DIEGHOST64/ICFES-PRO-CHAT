import { describe, it, expect, beforeEach, vi } from 'vitest'

describe('API Client (client.ts)', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.resetModules()
  })

  it('creates axios instance with correct base URL', async () => {
    const apiModule = await import('../api/client')
    const api = apiModule.default

    const expectedBase = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://127.0.0.1:8080/api'
    expect(api.defaults.baseURL).toBe(expectedBase)
    expect(api.defaults.headers['Content-Type']).toBe('application/json')
    expect(api.defaults.timeout).toBe(10000)
  })

  it('request interceptor auto-attaches Bearer token from localStorage', async () => {
    localStorage.setItem('sp_token', 'my-secret-token')

    vi.resetModules()
    const apiModule = await import('../api/client')
    const api = apiModule.default

    const config = { headers: {} as Record<string, string> }
    const interceptor = (api.interceptors.request as any).handlers[0]
    const result = interceptor.fulfilled(config)

    expect(result.headers.Authorization).toBe('Bearer my-secret-token')
  })

  it('request interceptor skips token when localStorage is empty', async () => {
    vi.resetModules()
    const apiModule = await import('../api/client')
    const api = apiModule.default

    const config = { headers: {} as Record<string, string> }
    const interceptor = (api.interceptors.request as any).handlers[0]
    const result = interceptor.fulfilled(config)

    expect(result.headers.Authorization).toBeUndefined()
  })

  it('exports typed API modules with correct methods', async () => {
    vi.resetModules()
    const { authAPI, queriesAPI, aiAPI, coordinatorAPI } = await import('../api/client')

    expect(authAPI.registerStudent).toBeDefined()
    expect(authAPI.loginStudent).toBeDefined()
    expect(authAPI.loginCoordinator).toBeDefined()
    expect(authAPI.logout).toBeDefined()

    expect(queriesAPI.save).toBeDefined()
    expect(queriesAPI.history).toBeDefined()
    expect(queriesAPI.rate).toBeDefined()
    expect(queriesAPI.updateVisual).toBeDefined()

    expect(aiAPI.consultar).toBeDefined()
    expect(aiAPI.sugerencias).toBeDefined()
    expect(aiAPI.adminChat).toBeDefined()

    expect(coordinatorAPI.metrics).toBeDefined()
    expect(coordinatorAPI.byProgram).toBeDefined()
    expect(coordinatorAPI.trend).toBeDefined()
  })

  it('response interceptor handles 401 by clearing localStorage', async () => {
    localStorage.setItem('sp_token', 'expired-token')
    localStorage.setItem('sp_role', 'student')

    vi.resetModules()
    const apiModule = await import('../api/client')
    const api = apiModule.default

    const responseError = {
      response: { status: 401 },
      config: { headers: { Authorization: 'Bearer expired-token' } },
    }

    const interceptor = (api.interceptors.response as any).handlers[0]

    try {
      await interceptor.rejected(responseError)
    } catch {
      // Expected - the interceptor redirects, which throws in test env
    }

    expect(localStorage.getItem('sp_token')).toBeNull()
    expect(localStorage.getItem('sp_role')).toBeNull()
  })
})
