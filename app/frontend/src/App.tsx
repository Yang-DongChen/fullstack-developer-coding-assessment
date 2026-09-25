import { useEffect, useMemo, useState } from 'react'
import { addToCart, getCart, getProduct, type Cart, type Product, type SKU } from './api'

function findSKU(product: Product, selected: Record<string, string>): SKU | undefined {
  return product.skus.find((sku) =>
    Object.entries(selected).every(([key, value]) => sku.options[key] === value),
  )
}

export default function App() {
  const [product, setProduct] = useState<Product | null>(null)
  const [cart, setCart] = useState<Cart | null>(null)
  const [selected, setSelected] = useState<Record<string, string>>({ colour: 'Black', size: 'S' })
  const [quantity, setQuantity] = useState(1)
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([getProduct('pdp-001'), getCart()])
      .then(([productData, cartData]) => {
        setProduct(productData)
        setCart(cartData)
      })
      .catch(() => setError('Unable to load the product.'))
      .finally(() => setLoading(false))
  }, [])

  const sku = useMemo(
    () => (product ? findSKU(product, selected) : undefined),
    [product, selected],
  )

  const setOption = (name: string, value: string) => {
    setSelected((current) => ({ ...current, [name]: value }))
    setQuantity(1)
    setMessage('')
    setError('')
  }

  const addCurrentItem = async () => {
    if (!sku || sku.available_quantity < quantity) return

    setAdding(true)
    setMessage('')
    setError('')

    try {
      const nextCart = await addToCart(sku.id, quantity, crypto.randomUUID())
      setCart(nextCart)
      setMessage('Added to cart.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to add item.')
      // Refresh so the UI reflects server-side stock after a race.
      try {
        const nextProduct = await getProduct('pdp-001')
        const nextCart = await getCart()
        setProduct(nextProduct)
        setCart(nextCart)
      } catch {
        // Keep the original user-facing error.
      }
    } finally {
      setAdding(false)
    }
  }

  if (loading) return <main className="page"><p>Loading…</p></main>
  if (!product) return <main className="page"><p>{error || 'Product unavailable.'}</p></main>

  const isUnavailable = !sku
  const isOutOfStock = Boolean(sku && sku.available_quantity === 0)
  const maxQuantity = sku ? Math.max(1, Math.min(9, sku.available_quantity)) : 1

  return (
    <main className="page">
      <header className="topbar">
        <span className="brand">Variant Shop</span>
        <span className="cart-badge">Cart ({cart?.total_item_count ?? 0})</span>
      </header>

      <section className="product-grid">
        <div className="image-panel">
          <img src={sku?.image ?? product.skus[0].image} alt={product.name} />
        </div>

        <div className="details">
          <p className="eyebrow">PDP · SKU selection</p>
          <h1>{product.name}</h1>
          <p className="description">{product.description}</p>

          <div className="price-row">
            <strong>{sku ? `$${(sku.price / 100).toFixed(2)}` : '—'}</strong>
            {sku && <span>{isOutOfStock ? 'Out of stock' : `${sku.available_quantity} available`}</span>}
            {isUnavailable && <span>Unavailable combination</span>}
          </div>

          {product.options.map((option) => (
            <div className="option-group" key={option.name}>
              <label>{option.name}</label>
              <div className="option-row">
                {option.values.map((value) => {
                  const previewSelection = { ...selected, [option.name]: value }
                  const previewSKU = findSKU(product, previewSelection)
                  const disabled = !previewSKU
                  const active = selected[option.name] === value
                  return (
                    <button
                      type="button"
                      key={value}
                      className={`option-button ${active ? 'active' : ''} ${disabled ? 'disabled' : ''}`}
                      disabled={disabled}
                      onClick={() => setOption(option.name, value)}
                    >
                      {value}
                    </button>
                  )
                })}
              </div>
            </div>
          ))}

          <div className="quantity-row">
            <label htmlFor="quantity">Quantity</label>
            <input
              id="quantity"
              type="number"
              min={1}
              max={maxQuantity}
              value={quantity}
              disabled={isUnavailable || isOutOfStock || adding}
              onChange={(event) => setQuantity(Math.max(1, Math.min(maxQuantity, Number(event.target.value) || 1)))}
            />
          </div>

          <button
            className="add-button"
            type="button"
            disabled={adding || isUnavailable || isOutOfStock}
            onClick={addCurrentItem}
          >
            {adding ? 'Adding…' : isUnavailable ? 'Unavailable' : isOutOfStock ? 'Out of stock' : 'Add to cart'}
          </button>

          {message && <p className="success" role="status">{message}</p>}
          {error && <p className="error" role="alert">{error}</p>}

          <aside className="cart-summary">
            <h2>Cart</h2>
            {cart?.items.length ? (
              cart.items.map((item) => (
                <div className="cart-item" key={item.sku_id}>
                  <span>{Object.values(item.options).join(' / ')}</span>
                  <span>× {item.quantity}</span>
                </div>
              ))
            ) : (
              <p>Your cart is empty.</p>
            )}
            <strong>Total: ${(cart ? cart.total_price / 100 : 0).toFixed(2)}</strong>
          </aside>
        </div>
      </section>
    </main>
  )
}
