"use client";

import { useEffect, useState } from "react";

import type { ProductVariant } from "@/lib/redux/features/catalog/catalogTypes";

import { useAddCartItemMutation } from "@/lib/redux/services/cartApi";

interface AddToCartButtonProps {
  variant: ProductVariant | null;
}

export default function AddToCartButton({
  variant,
}: AddToCartButtonProps) {
  const [quantity, setQuantity] = useState(1);
  const [message, setMessage] = useState("");

  const [addCartItem, { isLoading }] = useAddCartItemMutation();

  useEffect(() => {
    setQuantity(1);
    setMessage("");
  }, [variant?.id]);

  const availableStock = variant?.stock ?? 0;

  const handleAddToCart = async () => {
    if (!variant || availableStock < 1) {
      return;
    }

    if (quantity > availableStock) {
      setMessage("تعداد انتخاب‌شده بیشتر از موجودی محصول است.");
      return;
    }

    setMessage("");

    try {
      await addCartItem({
        variant_id: variant.id,
        quantity,
      }).unwrap();

      setMessage("محصول با موفقیت به سبد خرید اضافه شد.");
      setQuantity(1);
    } catch (error: unknown) {
      const apiError = error as {
        data?: {
          error?: string;
          detail?: string;
        };
      };

      setMessage(
        apiError.data?.error ||
          apiError.data?.detail ||
          "افزودن محصول به سبد خرید ناموفق بود."
      );
    }
  };

  if (!variant || availableStock < 1) {
    return (
      <button
        type="button"
        disabled
        className="mt-6 w-full cursor-not-allowed rounded-xl bg-gray-200 px-6 py-4 text-sm font-bold text-gray-500"
      >
        محصول ناموجود است
      </button>
    );
  }

  return (
    <div className="mt-6 text-gray-700">
      <div className="flex items-center justify-between gap-4">
        <span className="text-sm font-medium text-gray-700">
          تعداد
        </span>

        <div className="flex items-center rounded-xl border border-gray-200">
          <button
            type="button"
            onClick={() =>
              setQuantity((current) => Math.max(1, current - 1))
            }
            disabled={quantity <= 1 || isLoading}
            className="px-4 py-2 text-lg disabled:opacity-30"
            aria-label="کاهش تعداد"
          >
            −
          </button>

          <span className="min-w-10 text-center text-sm font-bold">
            {quantity.toLocaleString("fa-IR")}
          </span>

          <button
            type="button"
            onClick={() =>
              setQuantity((current) =>
                Math.min(availableStock, current + 1)
              )
            }
            disabled={quantity >= availableStock || isLoading}
            className="px-4 py-2 text-lg disabled:opacity-30"
            aria-label="افزایش تعداد"
          >
            +
          </button>
        </div>
      </div>

      <button
        type="button"
        onClick={handleAddToCart}
        disabled={isLoading}
        className="mt-5 w-full rounded-xl bg-pink-600 px-6 py-4 text-sm font-bold text-white transition hover:bg-pink-700 disabled:cursor-wait disabled:opacity-60"
      >
        {isLoading
          ? "در حال افزودن..."
          : "افزودن به سبد خرید"}
      </button>

      {message && (
        <p
          role="status"
          className={`mt-3 rounded-xl p-3 text-center text-sm ${
            message.includes("موفقیت")
              ? "bg-green-50 text-green-700"
              : "bg-red-50 text-red-600"
          }`}
        >
          {message}
        </p>
      )}

      <p className="mt-3 text-xs text-gray-400">
        حداکثر موجودی قابل سفارش:{" "}
        {availableStock.toLocaleString("fa-IR")} عدد
      </p>
    </div>
  );
}