import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  addToCart,
  ApiError,
  getCart,
  getProduct,
  type Cart,
  type Product,
} from './api'
import {
  clampQuantity,
  isOptionValueAvailable,
  isSelectionComplete,
  resolveSKU,
  type Selection,
} from './domain'

const PRODUCT_ID = 'pdp-001'

function createRequestKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `add-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function formatPrice(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`
}

function getAddErrorMessage(error: ApiError): string {
  switch (error.code) {
    case 'VALIDATION_ERROR':
      return 'Please choose a valid quantity before adding the item.'
    case 'INSUFFICIENT_STOCK': {
      const available = error.details.available_quantity
      return typeof available === 'number'
        ? `Stock changed. Only ${available} unit${available === 1 ? '' : 's'} remain. Your selection has been refreshed.`
        : 'Stock changed. Please review the latest stock and try again.'
    }
    case 'SKU_NOT_FOUND':
      return 'That variant is no longer available. The latest product data has been loaded.'
    case 'IDEMPOTENCY_KEY_REUSED':
      return 'This add-to-cart request was already submitted with different data. Please try again.'
    case 'INTERNAL_ERROR':
      return 'The server could not add the item. Please try again.'
    default:
      return error.message || 'Unable to add the item.'
  }
}

export default function App() {
  const [product, setProduct] = useState<Product | null>(null)
  const [cart, setCart] = useState<Cart | null>(null)
  const [selection, setSelection] = useState<Selection>({})
  const [quantity, setQuantity] = useState(1)
  const [productLoading, setProductLoading] = useState(true)
  const [productError, setProductError] = useState('')
  const [cartLoading, setCartLoading] = useState(true)
  const [cartError, setCartError] = useState('')
  const [adding, setAdding] = useState(false)
  const [feedback, setFeedback] = useState<{ kind: 'success' | 'error'; text: string } | null>(null)
  const addInFlightRef = useRef(false)

  const loadProduct = useCallback(async () => {
    setProductLoading(true)
    setProductError('')

    try {
      const nextProduct = await getProduct(PRODUCT_ID)
      setProduct(nextProduct)
    } catch (error) {
      setProductError(error instanceof Error ? error.message : 'Unable to load the product.')
    } finally {
      setProductLoading(false)
    }
  }, [])

  const loadCart = useCallback(async () => {
    setCartLoading(true)
    setCartError('')

    try {
      setCart(await getCart())
    } catch (error) {
      setCartError(error instanceof Error ? error.message : 'Unable to load the cart.')
    } finally {
      setCartLoading(false)
    }
  }, [])

  const refreshProductAndCart = useCallback(async () => {
    await Promise.all([loadProduct(), loadCart()])
  }, [loadCart, loadProduct])

  useEffect(() => {
    void Promise.all([loadProduct(), loadCart()])
  }, [loadCart, loadProduct])

  const sku = useMemo(
    () => (product ? resolveSKU(product, selection) : undefined),
    [product, selection],
  )
  const selectionComplete = Boolean(product && isSelectionComplete(product, selection))
  const invalidCombination = selectionComplete && !sku
  const outOfStock = Boolean(sku && sku.available_quantity === 0)
  const maxQuantity = sku && sku.available_quantity > 0 ? sku.available_quantity : 1

  useEffect(() => {
    if (!sku) {
      setQuantity(1)
      return
    }
    setQuantity((current) => clampQuantity(current, sku.available_quantity))
  }, [sku])

  const selectOption = (optionName: string, value: string) => {
    setSelection((current) => {
      if (current[optionName] === value) return current
      return { ...current, [optionName]: value }
    })
    setFeedback(null)
  }

  const addCurrentItem = async () => {
    if (!sku || sku.available_quantity < quantity || adding || addInFlightRef.current) return

    addInFlightRef.current = true
    setAdding(true)
    setFeedback(null)

    const idempotencyKey = createRequestKey()

    try {
      let response: Awaited<ReturnType<typeof addToCart>>

      try {
        response = await addToCart(sku.id, quantity, idempotencyKey)
      } catch (error) {
        // A network failure can mean the server committed the request but the response was lost.
        // Replaying the exact same idempotency key is safe and avoids creating a duplicate.
        if (error instanceof ApiError && error.status === null) {
          response = await addToCart(sku.id, quantity, idempotencyKey)
        } else {
          throw error
        }
      }

      setCart(response.cart)
      setFeedback({ kind: 'success', text: 'Item added to cart successfully.' })

      // Re-read the product so stock and SKU data reflect the server after the reservation.
      try {
        const [freshProduct, freshCart] = await Promise.all([getProduct(PRODUCT_ID), getCart()])
        setProduct(freshProduct)
        setCart(freshCart)
      } catch {
        setFeedback({
          kind: 'error',
          text: 'The item was added, but the latest stock could not be loaded. Please retry the product refresh.',
        })
      }
    } catch (error) {
      const apiError = error instanceof ApiError
        ? error
        : new ApiError(error instanceof Error ? error.message : 'Unable to add the item.')

      setFeedback({ kind: 'error', text: getAddErrorMessage(apiError) })

      // A newer stock response or other concurrent change can leave the first product response stale.
      // Refresh both resources without a page reload.
      try {
        await refreshProductAndCart()
      } catch {
        // Keep the original user-facing error if the refresh itself fails.
      }
    } finally {
      addInFlightRef.current = false
      setAdding(false)
    }
  }

  if (productLoading && !product) {
    return (
      <main className="page" aria-busy="true">
        <section className="state-card" aria-labelledby="loading-title">
          <div className="spinner" aria-hidden="true" />
          <h1 id="loading-title">Loading product</h1>
          <p>Please wait while we load the latest product information.</p>
        </section>
      </main>
    )
  }

  if (productError && !product) {
    return (
      <main className="page">
        <section className="state-card" role="alert" aria-labelledby="load-error-title">
          <p className="eyebrow">Connection error</p>
          <h1 id="load-error-title">We could not load this product.</h1>
          <p>{productError}</p>
          <button type="button" className="secondary-button" onClick={() => void loadProduct()}>
            Retry
          </button>
        </section>
      </main>
    )
  }

  if (!product) return null

  const selectedImage = sku?.image ?? product.skus[0]?.image
  const selectedAlt = sku
    ? `${product.name} - ${Object.values(sku.options).join(', ')}`
    : `${product.name} product image`

  return (
    <main className="page">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Variant Shop home">Variant Shop</a>
        <div className="cart-status" aria-label={`Cart contains ${cart?.total_item_count ?? 0} items`}>
          <span className="cart-icon" aria-hidden="true">🛒</span>
          <span>Cart ({cartLoading ? '…' : cart?.total_item_count ?? 0})</span>
        </div>
      </header>

      <section className="product-grid" aria-labelledby="product-title">
        <div className="image-panel">
          <img src={selectedImage} alt={selectedAlt} />
        </div>

        <div className="details">
          <p className="eyebrow">PDP · SKU selection</p>
          <h1 id="product-title">{product.name}</h1>
          <p className="description">{product.description}</p>

          <div className="price-row" aria-live="polite" aria-atomic="true">
            <strong>{sku ? formatPrice(sku.price) : 'Select options'}</strong>
            <span className={outOfStock ? 'stock-status out' : 'stock-status'}>
              {!selectionComplete && 'Choose all options'}
              {selectionComplete && invalidCombination && 'Unavailable combination'}
              {sku && !outOfStock && `${sku.available_quantity} available`}
              {outOfStock && 'Out of stock'}
            </span>
          </div>

          <div className="selection-panel" aria-label="Product options">
            {product.options.map((option) => (
              <fieldset className="option-group" key={option.name}>
                <legend>{option.name}</legend>
                <div className="option-row">
                  {option.values.map((value) => {
                    const available = isOptionValueAvailable(product, selection, option.name, value)
                    const active = selection[option.name] === value
                    return (
                      <button
                        type="button"
                        key={value}
                        className={`option-button ${active ? 'active' : ''}`}
                        aria-pressed={active}
                        disabled={!available || adding}
                        onClick={() => selectOption(option.name, value)}
                      >
                        {value}
                      </button>
                    )
                  })}
                </div>
              </fieldset>
            ))}
          </div>

          {!selectionComplete && (
            <p className="helper-text" role="status">Select one value for every option before adding to cart.</p>
          )}
          {invalidCombination && (
            <p className="helper-text" role="status">That option combination is not available. Choose another value.</p>
          )}

          <div className="quantity-row">
            <label htmlFor="quantity">Quantity</label>
            <input
              id="quantity"
              type="number"
              inputMode="numeric"
              min={1}
              max={maxQuantity}
              value={quantity}
              disabled={!sku || outOfStock || adding}
              aria-describedby="quantity-help"
              onChange={(event) => {
                const nextValue = Number(event.target.value)
                if (!Number.isFinite(nextValue)) return
                setQuantity(clampQuantity(Math.floor(nextValue), maxQuantity))
                setFeedback(null)
              }}
            />
            <span id="quantity-help" className="field-hint">
              {outOfStock ? 'No units currently available.' : sku ? `1–${sku.available_quantity}` : 'Select all options first.'}
            </span>
          </div>

          <button
            className="add-button"
            type="button"
            disabled={adding || !sku || outOfStock || quantity < 1 || quantity > sku.available_quantity}
            aria-disabled={adding || !sku || outOfStock}
            onClick={() => void addCurrentItem()}
          >
            {adding ? 'Adding…' : outOfStock ? 'Out of stock' : !sku ? 'Select options' : 'Add to cart'}
          </button>

          <div className="feedback-region" aria-live="polite" aria-atomic="true">
            {feedback?.kind === 'success' && <p className="success" role="status">{feedback.text}</p>}
          </div>
          <div className="error-region" aria-live="assertive" aria-atomic="true">
            {feedback?.kind === 'error' && <p className="error" role="alert">{feedback.text}</p>}
          </div>

          <aside className="cart-summary" aria-labelledby="cart-title">
            <div className="summary-header">
              <h2 id="cart-title">Cart</h2>
              {cartError && (
                <button type="button" className="link-button" onClick={() => void loadCart()}>
                  Retry cart
                </button>
              )}
            </div>

            {cart?.items.length ? (
              cart.items.map((item) => (
                <div className="cart-item" key={item.sku_id}>
                  <span>
                    {Object.values(item.options).join(' / ')}
                    <span className="item-price"> · {formatPrice(item.unit_price)}</span>
                  </span>
                  <span>× {item.quantity}</span>
                </div>
              ))
            ) : cartError ? (
              <p className="muted">Cart information is temporarily unavailable.</p>
            ) : (
              <p>Your cart is empty.</p>
            )}
            <strong>Total: {formatPrice(cart?.total_price ?? 0)}</strong>
          </aside>
        </div>
      </section>
    </main>
  )
}
