"use client";

import Link from "next/link";
import { useState } from "react";

import {
  useGetCartQuery,
  useUpdateCartItemMutation,
  useRemoveCartItemMutation,
  useClearCartMutation,
} from "@/lib/redux/services/cartApi";

import type { CartItem } from "@/lib/redux/features/cart/cartTypes";

function formatPrice(price: string) {
  return `${Number(price).toLocaleString("fa-IR")} تومان`;
}

function getErrorMessage(error: unknown): string {
  const apiError = error as {
    data?: {
      error?: string;
      detail?: string;
    };
  };

  return (
    apiError.data?.error ||
    apiError.data?.detail ||
    "عملیات انجام نشد. لطفاً دوباره تلاش کنید."
  );
}

function CartItemCard({
  item,
  onUpdate,
  onRemove,
  isUpdating,
  isRemoving,
}: {
  item: CartItem;
  onUpdate: (item: CartItem, quantity: number) => void;
  onRemove: (itemId: string) => void;
  isUpdating: boolean;
  isRemoving: boolean;
}) {
  const unavailable = item.available_stock < 1;
  const exceedsStock = item.quantity > item.available_stock;

  return (
    <article className="flex flex-col gap-5 rounded-2xl border border-gray-100 bg-white p-5 sm:flex-row">
      <div className="h-28 w-full shrink-0 overflow-hidden rounded-xl bg-gray-100 sm:w-28">
        {item.product_image ? (
          <img
            src={item.product_image}
            alt={item.product_name}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-gray-400">
            بدون تصویر
          </div>
        )}
      </div>

      <div className="flex min-w-0 flex-1 flex-col justify-between gap-4">
        <div>
          <h3 className="font-bold text-gray-900">
            {item.product_name}
          </h3>

          <p className="mt-2 text-sm text-gray-500">
            {item.variant_name || item.sku}
          </p>

          <p className="mt-1 text-xs text-gray-400">
            کد محصول: {item.sku}
          </p>

          <p className="mt-3 text-sm font-semibold text-pink-600">
            {formatPrice(item.unit_price)}
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center rounded-xl border border-gray-200">
            <button
              type="button"
              disabled={isUpdating || item.quantity <= 1}
              onClick={() => onUpdate(item, item.quantity - 1)}
              className="px-3 py-2 text-lg disabled:opacity-30"
              aria-label="کاهش تعداد"
            >
              −
            </button>

            <span className="min-w-10 text-center text-sm font-bold">
              {item.quantity.toLocaleString("fa-IR")}
            </span>

            <button
              type="button"
              disabled={
                isUpdating ||
                unavailable ||
                item.quantity >= item.available_stock
              }
              onClick={() => onUpdate(item, item.quantity + 1)}
              className="px-3 py-2 text-lg disabled:opacity-30"
              aria-label="افزایش تعداد"
            >
              +
            </button>
          </div>

          <strong className="text-sm text-gray-900">
            {formatPrice(item.line_total)}
          </strong>

          <button
            type="button"
            disabled={isRemoving}
            onClick={() => onRemove(item.id)}
            className="text-sm text-red-500 hover:text-red-700 disabled:opacity-50"
          >
            {isRemoving ? "در حال حذف..." : "حذف"}
          </button>
        </div>

        {(unavailable || exceedsStock) && (
          <p className="rounded-lg bg-red-50 p-3 text-xs text-red-600">
            {unavailable
              ? "این محصول در حال حاضر موجود نیست."
              : `موجودی فعلی محصول ${item.available_stock} عدد است. تعداد سفارش خود را اصلاح کنید.`}
          </p>
        )}
      </div>
    </article>
  );
}

export default function CartPage() {
  const {
    data: cart,
    isLoading,
    isError,
    refetch,
  } = useGetCartQuery();

  const [updateCartItem, updateState] =
    useUpdateCartItemMutation();

  const [removeCartItem, removeState] =
    useRemoveCartItemMutation();

  const [clearCart, clearState] =
    useClearCartMutation();

  const [message, setMessage] = useState("");

  const handleUpdate = async (
    item: CartItem,
    quantity: number
  ) => {
    if (quantity < 1 || quantity > item.available_stock) {
      return;
    }

    setMessage("");

    try {
      await updateCartItem({
        itemId: item.id,
        quantity,
      }).unwrap();
    } catch (error) {
      setMessage(getErrorMessage(error));
    }
  };

  const handleRemove = async (itemId: string) => {
    setMessage("");

    try {
      await removeCartItem(itemId).unwrap();
    } catch (error) {
      setMessage(getErrorMessage(error));
    }
  };

  const handleClear = async () => {
    if (!window.confirm("آیا از خالی کردن سبد خرید مطمئن هستید؟")) {
      return;
    }

    setMessage("");

    try {
      await clearCart().unwrap();
    } catch (error) {
      setMessage(getErrorMessage(error));
    }
  };

  if (isLoading) {
    return (
      <main className="mx-auto max-w-7xl animate-pulse px-4 py-16">
        <div className="mb-8 h-8 w-48 rounded bg-gray-200" />

        <div className="grid gap-8 lg:grid-cols-3">
          <div className="space-y-4 lg:col-span-2">
            <div className="h-40 rounded-2xl bg-gray-200" />
            <div className="h-40 rounded-2xl bg-gray-200" />
          </div>

          <div className="h-64 rounded-2xl bg-gray-200" />
        </div>
      </main>
    );
  }

  if (isError || !cart) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-20 text-center">
        <h1 className="text-xl font-bold">
          دریافت سبد خرید ناموفق بود.
        </h1>

        <button
          type="button"
          onClick={() => void refetch()}
          className="mt-5 rounded-xl bg-pink-600 px-6 py-3 text-sm text-white"
        >
          تلاش مجدد
        </button>
      </main>
    );
  }

  const hasStockProblem = cart.items.some(
    (item) =>
      item.available_stock < 1 ||
      item.quantity > item.available_stock
  );

  return (
    <main className="min-h-screen bg-gray-50 text-gray-600">
      <div className="mx-auto max-w-7xl px-4 py-10">
        <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              سبد خرید
            </h1>

            <p className="mt-2 text-sm text-gray-500">
              {cart.total_items.toLocaleString("fa-IR")} عدد محصول
            </p>
          </div>

          {cart.items.length > 0 && (
            <button
              type="button"
              disabled={clearState.isLoading}
              onClick={handleClear}
              className="text-sm text-red-500 hover:text-red-700 disabled:opacity-50"
            >
              {clearState.isLoading
                ? "در حال خالی کردن..."
                : "خالی کردن سبد"}
            </button>
          )}
        </div>

        {message && (
          <div
            role="alert"
            className="mb-6 rounded-xl bg-red-50 p-4 text-sm text-red-600"
          >
            {message}
          </div>
        )}

        {cart.items.length === 0 ? (
          <div className="rounded-3xl border border-gray-100 bg-white px-5 py-20 text-center">
            <div className="text-5xl">🛍️</div>

            <h2 className="mt-5 text-xl font-bold text-gray-900">
              سبد خرید شما خالی است
            </h2>

            <p className="mt-3 text-sm text-gray-500">
              می‌توانید محصولات موردنظرتان را از فروشگاه انتخاب کنید.
            </p>

            <Link
              href="/products"
              className="mt-7 inline-block rounded-xl bg-pink-600 px-7 py-3 text-sm font-bold text-white hover:bg-pink-700"
            >
              مشاهده محصولات
            </Link>
          </div>
        ) : (
          <div className="grid items-start gap-8 lg:grid-cols-3">
            <section className="space-y-4 lg:col-span-2">
              {cart.items.map((item) => (
                <CartItemCard
                  key={item.id}
                  item={item}
                  onUpdate={handleUpdate}
                  onRemove={handleRemove}
                  isUpdating={updateState.isLoading}
                  isRemoving={removeState.isLoading}
                />
              ))}
            </section>

            <aside className="rounded-2xl border border-gray-100 bg-white p-6">
              <h2 className="text-lg font-bold text-gray-900">
                خلاصه سفارش
              </h2>

              <div className="mt-6 flex justify-between gap-4 text-sm">
                <span className="text-gray-500">
                  تعداد محصولات
                </span>

                <span className="font-semibold">
                  {cart.total_items.toLocaleString("fa-IR")}
                </span>
              </div>

              <div className="mt-5 flex justify-between gap-4 text-sm">
                <span className="text-gray-500">
                  مبلغ محصولات
                </span>

                <span className="font-semibold">
                  {formatPrice(cart.subtotal)}
                </span>
              </div>

              <div className="my-6 border-t border-gray-100" />

              <div className="flex justify-between gap-4">
                <span className="font-bold">
                  مبلغ کل
                </span>

                <strong className="text-lg text-pink-600">
                  {formatPrice(cart.subtotal)}
                </strong>
              </div>

              {hasStockProblem && (
                <p className="mt-5 rounded-xl bg-red-50 p-3 text-xs leading-6 text-red-600">
                  برای ادامه سفارش، ابتدا وضعیت موجودی محصولات را اصلاح کنید.
                </p>
              )}

              <button
                type="button"
                disabled={hasStockProblem}
                className="mt-7 w-full rounded-xl bg-pink-600 px-5 py-4 text-sm font-bold text-white transition hover:bg-pink-700 disabled:cursor-not-allowed disabled:bg-gray-300"
              >
                ادامه فرآیند خرید
              </button>

              <Link
                href="/products"
                className="mt-4 block text-center text-sm text-gray-500 hover:text-pink-600"
              >
                ادامه خرید
              </Link>
            </aside>
          </div>
        )}
      </div>
    </main>
  );
}