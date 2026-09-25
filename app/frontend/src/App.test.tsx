import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import type { Cart, Product } from './api'

const product: Product = {
  id: 'pdp-001',
  name: 'Everyday Cotton Tee',
  description: 'Test product',
  options: [
    { name: 'colour', values: ['Black', 'White'] },
    { name: 'size', values: ['S', 'M', 'L', 'XL'] },
  ],
  skus: [
    { id: 'black-s', price: 2999, available_quantity: 3, image: 'black-s.jpg', options: { colour: 'Black', size: 'S' } },
    { id: 'black-l', price: 3299, available_quantity: 0, image: 'black-l.jpg', options: { colour: 'Black', size: 'L' } },
    { id: 'white-s', price: 2999, available_quantity: 2, image: 'white-s.jpg', options: { colour: 'White', size: 'S' } },
  ],
}

const emptyCart: Cart = { items: [], total_item_count: 0, total_price: 0 }

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

beforeEach(() => {
  vi.restoreAllMocks()
  vi.stubGlobal('crypto', { randomUUID: vi.fn(() => 'test-key') })
})

describe('PDP UI', () => {
  it('resolves the selected variant and updates price/image/stock', async () => {
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/products/')) return Promise.resolve(jsonResponse(product))
      return Promise.resolve(jsonResponse(emptyCart))
    }))

    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Everyday Cotton Tee' })).toBeInTheDocument()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'L' }))
    })
    expect(screen.getByText('Out of stock')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Out of stock' })).toBeDisabled()
  })

  it('prevents duplicate add-to-cart submissions while the first request is in progress', async () => {
    let resolveAdd!: (response: Response) => void
    const addPromise = new Promise<Response>((resolve) => {
      resolveAdd = resolve
    })

    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/products/')) return Promise.resolve(jsonResponse(product))
      if (url.includes('/api/cart/items')) return addPromise
      return Promise.resolve(jsonResponse(emptyCart))
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    const addButton = await screen.findByRole('button', { name: 'Add to cart' })

    fireEvent.click(addButton)
    fireEvent.click(addButton)

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
    expect(addButton).toBeDisabled()

    resolveAdd(jsonResponse({ message: 'ok', cart: { ...emptyCart, total_item_count: 1, total_price: 2999 } }, 201))

    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Item added to cart successfully.'))
  })

  it('shows a retryable product-load error without requiring a page refresh', async () => {
    let attempts = 0
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/products/')) {
        attempts += 1
        return attempts === 1
          ? Promise.reject(new Error('Temporary network failure'))
          : Promise.resolve(jsonResponse(product))
      }
      return Promise.resolve(jsonResponse(emptyCart))
    }))

    render(<App />)
    expect(await screen.findByRole('button', { name: 'Retry' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))

    expect(await screen.findByRole('heading', { name: 'Everyday Cotton Tee' })).toBeInTheDocument()
  })
})
