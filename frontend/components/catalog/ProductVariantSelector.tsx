"use client";

import type { ProductVariant } from "@/lib/redux/features/catalog/catalogTypes";

interface ProductVariantSelectorProps {
  variants: ProductVariant[];
  selectedVariantId: number | null;
  onSelect: (variantId: number) => void;
}

export default function ProductVariantSelector({
  variants,
  selectedVariantId,
  onSelect,
}: ProductVariantSelectorProps) {
  if (variants.length === 0) {
    return (
      <p className="rounded-xl bg-red-50 p-4 text-sm text-red-600">
        در حال حاضر هیچ تنوع فعالی برای این محصول ثبت نشده است.
      </p>
    );
  }

  return (
    <div>
      <h3 className="mb-3 text-sm font-bold text-gray-800">
        انتخاب نوع محصول
      </h3>

      <div className="flex flex-wrap gap-3">
        {variants.map((variant) => {
          const selected = variant.id === selectedVariantId;
          const available = variant.stock > 0;

          return (
            <button
              key={variant.id}
              type="button"
              disabled={!available}
              onClick={() => onSelect(variant.id)}
              aria-pressed={selected}
              className={`min-w-24 rounded-xl border px-4 py-3 text-sm transition ${
                selected
                  ? "border-pink-500 bg-pink-50 text-pink-700"
                  : "border-gray-200 bg-white text-gray-700"
              } ${
                !available
                  ? "cursor-not-allowed opacity-40"
                  : "hover:border-pink-400"
              }`}
            >
              <span className="block font-semibold">
                {variant.name || variant.sku}
              </span>

              <span className="mt-1 block text-xs">
                {available ? "موجود" : "ناموجود"}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}