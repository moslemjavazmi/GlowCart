
"use client";

import type { Cart } from "@/lib/redux/features/cart/cartTypes";
import type { Order } from "@/lib/redux/features/orders/orderTypes";

interface CheckoutSummaryProps {
  cart: Cart;
  order?: Order | null;
  couponCode: string;
  onCouponChange: (value: string) => void;
  disabled: boolean;
  isSubmitting: boolean;
  hasPendingOrder: boolean;
  onSubmit: () => void;
}

function formatPrice(price: string) {
  return `${Number(price).toLocaleString("fa-IR")} تومان`;
}

export default function CheckoutSummary({
  cart,
  order,
  couponCode,
  onCouponChange,
  disabled,
  isSubmitting,
  hasPendingOrder,
  onSubmit,
}: CheckoutSummaryProps) {
  const subtotal = order?.subtotal ?? cart.subtotal;
  const shippingCost = order?.shipping_cost ?? "0";
  const discountAmount = order?.discount_amount ?? "0";
  const totalAmount = order?.total_amount ?? cart.subtotal;

  return (
    <aside className="rounded-2xl border border-gray-100 bg-white p-6">
      <h2 className="text-lg font-bold text-gray-900">
        خلاصه سفارش
      </h2>

      <div className="mt-6 space-y-4">
        <div className="flex justify-between gap-3 text-sm">
          <span className="text-gray-500">تعداد محصولات</span>

          <span className="font-semibold text-gray-800">
            {cart.total_items.toLocaleString("fa-IR")}
          </span>
        </div>

        <div className="flex justify-between gap-3 text-sm">
          <span className="text-gray-500">مبلغ محصولات</span>

          <span className="font-semibold text-gray-800">
            {formatPrice(subtotal)}
          </span>
        </div>

        <div className="flex justify-between gap-3 text-sm">
          <span className="text-gray-500">هزینه ارسال</span>

          <span className="font-semibold text-gray-800">
            {formatPrice(shippingCost)}
          </span>
        </div>

        {Number(discountAmount) > 0 && (
          <div className="flex justify-between gap-3 text-sm">
            <span className="text-gray-500">تخفیف</span>

            <span className="font-semibold text-green-600">
              {formatPrice(discountAmount)}
            </span>
          </div>
        )}

        <div className="border-t border-gray-100 pt-5">
          <div className="flex items-center justify-between gap-3">
            <span className="font-bold text-gray-800">
              مبلغ قابل پرداخت
            </span>

            <strong className="text-lg text-pink-600">
              {formatPrice(totalAmount)}
            </strong>
          </div>
        </div>

        <div className="border-t border-gray-100 pt-5">
          <label className="mb-2 block text-sm font-medium text-gray-700">
            کد تخفیف
          </label>

          <input
            value={couponCode}
            onChange={(event) => onCouponChange(event.target.value)}
            placeholder="کد تخفیف را وارد کنید"
            maxLength={50}
            disabled={hasPendingOrder}
            className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm outline-none focus:border-pink-500 disabled:bg-gray-50"
          />

          <p className="mt-2 text-xs leading-5 text-gray-400">
            تخفیف نهایی پس از اعتبارسنجی کد توسط سرور محاسبه می‌شود.
          </p>
        </div>
      </div>

      <button
        type="button"
        disabled={disabled || isSubmitting}
        onClick={onSubmit}
        className="mt-7 w-full rounded-xl bg-pink-600 px-5 py-4 text-sm font-bold text-white transition hover:bg-pink-700 disabled:cursor-not-allowed disabled:bg-gray-300"
      >
        {isSubmitting
          ? "در حال پردازش..."
          : hasPendingOrder
            ? "تلاش مجدد برای پرداخت"
            : "ثبت سفارش و پرداخت"}
      </button>

      <p className="mt-4 text-center text-xs leading-6 text-gray-400">
        مبلغ نهایی سفارش در زمان ایجاد سفارش توسط سرور محاسبه می‌شود.
      </p>
    </aside>
  );
}
