import type { Product, SKU } from './api'

export type Selection = Record<string, string | undefined>

export function resolveSKU(product: Product, selected: Selection): SKU | undefined {
  const requiredOptions = product.options.map((option) => option.name)
  const isComplete = requiredOptions.every((name) => Boolean(selected[name]))

  if (!isComplete) return undefined

  return product.skus.find((sku) =>
    requiredOptions.every((name) => sku.options[name] === selected[name]),
  )
}

export function isSelectionComplete(product: Product, selected: Selection): boolean {
  return product.options.every((option) => Boolean(selected[option.name]))
}

export function isOptionValueAvailable(
  product: Product,
  selected: Selection,
  optionName: string,
  candidateValue: string,
): boolean {
  return product.skus.some((sku) => {
    if (sku.options[optionName] !== candidateValue) return false

    return product.options.every((option) => {
      if (option.name === optionName) return true
      const currentValue = selected[option.name]
      return !currentValue || sku.options[option.name] === currentValue
    })
  })
}

export function clampQuantity(quantity: number, availableQuantity: number): number {
  if (availableQuantity <= 0) return 1
  return Math.min(Math.max(quantity, 1), availableQuantity)
}
