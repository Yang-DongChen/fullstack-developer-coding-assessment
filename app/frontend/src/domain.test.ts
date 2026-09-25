import { describe, expect, it } from 'vitest'
import { isOptionValueAvailable, resolveSKU } from './domain'
import type { Product } from './api'

const product: Product = {
  id: 'pdp-001',
  name: 'Test Tee',
  description: 'Test product',
  options: [
    { name: 'colour', values: ['Black', 'White'] },
    { name: 'size', values: ['S', 'M', 'L', 'XL'] },
  ],
  skus: [
    { id: 'black-s', price: 1000, available_quantity: 2, image: 'black-s.jpg', options: { colour: 'Black', size: 'S' } },
    { id: 'black-l', price: 1200, available_quantity: 0, image: 'black-l.jpg', options: { colour: 'Black', size: 'L' } },
    { id: 'white-s', price: 1000, available_quantity: 4, image: 'white-s.jpg', options: { colour: 'White', size: 'S' } },
  ],
}

describe('variant resolution', () => {
  it('resolves a complete selection to the matching SKU', () => {
    const sku = resolveSKU(product, { colour: 'Black', size: 'S' })
    expect(sku?.id).toBe('black-s')
    expect(sku?.price).toBe(1000)
  })

  it('returns no SKU for an incomplete or unavailable selection', () => {
    expect(resolveSKU(product, { colour: 'Black' })).toBeUndefined()
    expect(resolveSKU(product, { colour: 'White', size: 'XL' })).toBeUndefined()
  })

  it('disables impossible option values but allows an existing out-of-stock SKU', () => {
    expect(isOptionValueAvailable(product, { colour: 'White' }, 'size', 'XL')).toBe(false)
    expect(isOptionValueAvailable(product, { colour: 'Black' }, 'size', 'L')).toBe(true)
  })
})
