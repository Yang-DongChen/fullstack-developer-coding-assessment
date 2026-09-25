export const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

export type Option = {
  name: string
  values: string[]
}

export type SKU = {
  id: string
  price: number
  available_quantity: number
  image: string
  options: Record<string, string>
}

export type Product = {
  id: string
  name: string
  description: string
  options: Option[]
  skus: SKU[]
}

export type CartItem = {
  sku_id: string
  quantity: number
  unit_price: number
  options: Record<string, string>
  image: string
}

export type Cart = {
  items: CartItem[]
  total_item_count: number
  total_price: number
}

export type ApiErrorBody = {
  error?: {
    code?: string
    message?: string
    details?: Record<string, unknown>
  }
}

export class ApiError extends Error {
  readonly status: number | null
  readonly code: string | undefined
  readonly details: Record<string, unknown>

  constructor(message: string, status: number | null = null, code?: string, details: Record<string, unknown> = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  const raw = await response.text()
  let body: ApiErrorBody | T | null = null

  if (raw) {
    try {
      body = JSON.parse(raw) as ApiErrorBody | T
    } catch {
      body = null
    }
  }

  if (!response.ok) {
    const errorBody = body as ApiErrorBody | null
    const message = errorBody?.error?.message ?? `Request failed with status ${response.status}.`
    throw new ApiError(message, response.status, errorBody?.error?.code, errorBody?.error?.details)
  }

  if (body === null) {
    throw new ApiError('The server returned an empty response.', response.status)
  }

  return body as T
}

async function request<T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> {
  try {
    const response = await fetch(input, init)
    return await parseResponse<T>(response)
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new ApiError('Network request failed. Please check your connection and try again.', null)
  }
}

export function getProduct(id: string): Promise<Product> {
  return request<Product>(`${API_BASE}/api/products/${id}`)
}

export function getCart(): Promise<Cart> {
  return request<Cart>(`${API_BASE}/api/cart`)
}

export function addToCart(skuId: string, quantity: number, idempotencyKey: string): Promise<{ message: string; cart: Cart }> {
  return request<{ message: string; cart: Cart }>(`${API_BASE}/api/cart/items`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify({ sku_id: skuId, quantity }),
  })
}
