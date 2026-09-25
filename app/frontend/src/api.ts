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

export async function getProduct(id: string): Promise<Product> {
  const response = await fetch(`${API_BASE}/api/products/${id}`)
  if (!response.ok) throw new Error('Unable to load product.')
  return response.json()
}

export async function getCart(): Promise<Cart> {
  const response = await fetch(`${API_BASE}/api/cart`)
  if (!response.ok) throw new Error('Unable to load cart.')
  return response.json()
}

export async function addToCart(skuId: string, quantity: number, key: string) {
  const response = await fetch(`${API_BASE}/api/cart/items`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': key,
    },
    body: JSON.stringify({ sku_id: skuId, quantity }),
  })

  const body = await response.json()
  if (!response.ok) {
    throw new Error(body?.error?.message ?? 'Unable to add item to cart.')
  }
  return body.cart as Cart
}
