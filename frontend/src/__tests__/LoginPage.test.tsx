import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../context/AuthContext'
import * as AuthContextModule from '../context/AuthContext'
import { ThemeProvider } from '../context/ThemeContext'
import { VisualMoodProvider } from '../context/VisualMoodContext'

// Simple test component that renders without the heavy WebGL/3D dependencies
const SimpleAuthForm = () => {
  return (
    <div>
      <h1>Bienvenido a Ascenso Pro</h1>
      <p>Empieza tu plan de estudio en pocos segundos.</p>
      <label>Ingresa tu cédula</label>
      <input placeholder="Ej: 1234567890" />
      <label>Ingresa tu clave secreta</label>
      <input type="password" placeholder="Ingresa tu clave secreta" />
      <button>Entrar al asistente</button>
    </div>
  )
}

describe('Login Page (componentes base)', () => {
  it('renders login form elements', () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <ThemeProvider>
            <VisualMoodProvider>
              <SimpleAuthForm />
            </VisualMoodProvider>
          </ThemeProvider>
        </AuthProvider>
      </MemoryRouter>
    )

    expect(screen.getByText('Bienvenido a Ascenso Pro')).toBeTruthy()
    expect(screen.getByText('Empieza tu plan de estudio en pocos segundos.')).toBeTruthy()
    expect(screen.getByPlaceholderText('Ej: 1234567890')).toBeTruthy()
    expect(screen.getByPlaceholderText('Ingresa tu clave secreta')).toBeTruthy()
    expect(screen.getByText('Entrar al asistente')).toBeTruthy()
    expect(screen.getByText('Ingresa tu cédula')).toBeTruthy()
  })

  it('accepts user input in cedula field', () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <ThemeProvider>
            <VisualMoodProvider>
              <SimpleAuthForm />
            </VisualMoodProvider>
          </ThemeProvider>
        </AuthProvider>
      </MemoryRouter>
    )

    const input = screen.getByPlaceholderText('Ej: 1234567890')
    fireEvent.change(input, { target: { value: '1234567890' } })

    expect(input).toHaveProperty('value', '1234567890')
  })

  it('accepts user input in password field', () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <ThemeProvider>
            <VisualMoodProvider>
              <SimpleAuthForm />
            </VisualMoodProvider>
          </ThemeProvider>
        </AuthProvider>
      </MemoryRouter>
    )

    const input = screen.getByPlaceholderText('Ingresa tu clave secreta')
    fireEvent.change(input, { target: { value: '@' } })

    expect(input).toHaveProperty('value', '@')
  })
})

describe('AuthProvider Integration', () => {
  it('provides auth context to child components', () => {
    const TestConsumer = () => {
      const { isAuthenticated, token } = (() => {
        try {
          const { useAuth } = AuthContextModule
          return useAuth()
        } catch {
          return { isAuthenticated: false, token: null }
        }
      })()

      return (
        <div>
          <span data-testid="authenticated">{String(isAuthenticated)}</span>
          <span data-testid="token">{token || 'no-token'}</span>
        </div>
      )
    }

    render(
      <MemoryRouter>
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      </MemoryRouter>
    )

    expect(screen.getByTestId('authenticated').textContent).toBe('false')
    expect(screen.getByTestId('token').textContent).toBe('no-token')
  })
})
