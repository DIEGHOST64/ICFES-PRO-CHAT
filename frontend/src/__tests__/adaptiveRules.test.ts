import { describe, expect, it } from 'vitest'
import { inferEnglishLevel, inferGeneralDifficulty } from '../pages/PracticePage'

describe('inferGeneralDifficulty', () => {
    it('sube a avanzado con ratio >= 0.8', () => {
        expect(inferGeneralDifficulty(0.8)).toBe('avanzado')
        expect(inferGeneralDifficulty(1.0)).toBe('avanzado')
    })

    it('intermedio entre 0.55 y 0.79', () => {
        expect(inferGeneralDifficulty(0.55)).toBe('intermedio')
        expect(inferGeneralDifficulty(0.79)).toBe('intermedio')
    })

    it('basico por debajo de 0.55', () => {
        expect(inferGeneralDifficulty(0.54)).toBe('basico')
        expect(inferGeneralDifficulty(0)).toBe('basico')
    })
})

describe('inferEnglishLevel', () => {
    it('sube a B1 con ratio >= 0.7', () => {
        expect(inferEnglishLevel(0.7, 'A2')).toBe('B1')
        expect(inferEnglishLevel(1.0, 'A2')).toBe('B1')
    })

    it('se mantiene en A2 si no alcanza 0.7', () => {
        expect(inferEnglishLevel(0.69, 'A2')).toBe('A2')
        expect(inferEnglishLevel(0, 'A2')).toBe('A2')
    })

    it('se mantiene en B1 entre 0.5 y 0.69', () => {
        expect(inferEnglishLevel(0.5, 'B1')).toBe('B1')
        expect(inferEnglishLevel(0.69, 'B1')).toBe('B1')
    })

    it('baja de B1 a A2 con ratio < 0.5', () => {
        expect(inferEnglishLevel(0.49, 'B1')).toBe('A2')
        expect(inferEnglishLevel(0.2, 'B1')).toBe('A2')
    })

    it('vuelve a subir desde B1 con ratio >= 0.7', () => {
        expect(inferEnglishLevel(0.75, 'B1')).toBe('B1')
    })
})
