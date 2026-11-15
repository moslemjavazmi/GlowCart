"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import AuthGuard from "@/components/auth/AuthGuard";
import OrderStatusBadge from "@/components/orders/OrderStatusBadge";
import {
  useGetOrderQuery,
  useCancelOrderMutation,
} from "@/lib/redux/services/orderApi";

function money(value: string | number) {
  const amount = Number(value || 0);

  return `${new Intl.NumberFormat("fa-IR").format(amount)} تومان`;
}

function date(value: string) {
  return new Date(value).toLocaleString("fa-IR", {
    dateStyle: "long",
    timeStyle: "short",
  });
}

function OrderDetailContent() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const orderId = params.id;

  const {
    data: order,
    isLoading,
    isError,
    refetch,
  } = useGetOrderQuery(orderId, {
    skip: !orderId,
  });

  const [cancelOrder, { isLoading: isCancelling }] =
    useCancelOrderMutation();

  const [cancelError, setCancelError] = useState("");

  const canCancel =
    order?.status === "pending" ||
    order?.status === "awaiting_payment";

  const handleCancel = async () => {
    if (!order || !canCancel || isCancelling) return;

    const confirmed = window.confirm(
      `آیا از لغو سفارش ${order.order_number} مطمئن هستید؟`
    );

    if (!confirmed) return;

    setCancelError("");

    try {
      await cancelOrder(order.id).unwrap();
      await refetch();
    } catch {
      setCancelError(
        "لغو سفارش انجام نشد. ممکن است وضعیت سفارش تغییر کرده باشد."
      );
    }
  };

  if (isLoading) {
    return (
      <div className="rounded-xl border bg-white p-10 text-center text-gray-500">
        در حال دریافت اطلاعات سفارش...
      </div>
    );
  }

  if (isError || !order) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-8 text-center">
        <p className="text-red-700">
          دریافت اطلاعات سفارش ممکن نبود.
        </p>
        <button
          onClick={() => refetch()}
          className="mt-4 rounded-lg bg-red-600 px-5 py-2 text-sm text-white"
        >
          تلاش مجدد
        </button>
        <div>
          <Link
            href="/orders"
            className="mt-4 inline-block text-sm text-gray-600 underline"
          >
            بازگشت به سفارش‌ها
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            جزئیات سفارش
          </h1>
          <p className="mt-2 text-sm text-gray-500">
            شماره سفارش: {order.order_number}
          </p>
        </div>

        <OrderStatusBadge status={order.status} />
      </div>

      <section className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="mb-5 font-semibold text-gray-900">
          اطلاعات سفارش
        </h2>

        <div className="grid gap-5 text-sm sm:grid-cols-2">
          <div>
            <p className="text-gray-500">تاریخ ثبت</p>
            <p className="mt-1 font-medium text-gray-900">
              {date(order.created_at)}
            </p>
          </div>

          <div>
            <p className="text-gray-500">آخرین بروزرسانی</p>
            <p className="mt-1 font-medium text-gray-900">
              {date(order.updated_at)}
            </p>
          </div>

          <div>
            <p className="text-gray-500">نام گیرنده</p>
            <p className="mt-1 font-medium text-gray-900">
              {order.recipient_name || "—"}
            </p>
          </div>

          <div>
            <p className="text-gray-500">شماره تماس</p>
            <p className="mt-1 font-medium text-gray-900">
              {order.phone_number || "—"}
            </p>
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="mb-5 font-semibold text-gray-900">
          آدرس تحویل
        </h2>

        <p className="text-sm leading-7 text-gray-700">
          {[
            order.province,
            order.city,
            order.address_line,
          ]
            .filter(Boolean)
            .join("، ") || "آدرسی ثبت نشده است"}
        </p>

        {order.postal_code && (
          <p className="mt-2 text-sm text-gray-500">
            کد پستی: {order.postal_code}
          </p>
        )}
      </section>

      <section className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="mb-5 font-semibold text-gray-900">
          محصولات سفارش
        </h2>

        <div className="divide-y divide-gray-100">
          {order.items.map((item) => (
            <div
              key={item.id}
              className="flex flex-wrap items-center justify-between gap-4 py-4 first:pt-0 last:pb-0"
            >
              <div>
                <p className="font-medium text-gray-900">
                  {item.product_name}
                </p>
                <p className="mt-1 text-sm text-gray-500">
                  {item.variant_name} · کد محصول: {item.sku}
                </p>
                <p className="mt-1 text-sm text-gray-500">
                  تعداد: {item.quantity.toLocaleString("fa-IR")}
                </p>
              </div>

              <p className="font-semibold text-gray-900">
                {money(item.line_total)}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="mb-5 font-semibold text-gray-900">
          خلاصه پرداخت سفارش
        </h2>

        <div className="space-y-3 text-sm">
          <div className="flex justify-between gap-4">
            <span className="text-gray-500">مبلغ محصولات</span>
            <span>{money(order.subtotal)}</span>
          </div>

          <div className="flex justify-between gap-4">
            <span className="text-gray-500">هزینه ارسال</span>
            <span>{money(order.shipping_cost)}</span>
          </div>

          <div className="flex justify-between gap-4">
            <span className="text-gray-500">تخفیف</span>
            <span className="text-green-600">
              {money(order.discount_amount)}
            </span>
          </div>

          <div className="flex justify-between gap-4 border-t pt-4 text-base font-bold">
            <span>مبلغ نهایی</span>
            <span>{money(order.total_amount)}</span>
          </div>
        </div>
      </section>

      {(order.status === "awaiting_payment" ||
        order.status === "pending") && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-5">
          <p className="text-sm leading-7 text-amber-800">
            وضعیت سفارش شما در انتظار پرداخت است. برای مشاهده وضعیت دقیق
            تراکنش، از صفحه نتیجه پرداخت استفاده کنید.
          </p>
          <Link
            href="/checkout"
            className="mt-3 inline-block text-sm font-semibold text-amber-900 underline"
          >
            بازگشت به تسویه حساب
          </Link>
        </div>
      )}

      {cancelError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {cancelError}
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        <Link
          href="/orders"
          className="rounded-lg border border-gray-300 px-5 py-3 text-sm text-gray-700 hover:bg-gray-50"
        >
          بازگشت به سفارش‌ها
        </Link>

        {canCancel && (
          <button
            onClick={handleCancel}
            disabled={isCancelling}
            className="rounded-lg bg-red-600 px-5 py-3 text-sm text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isCancelling ? "در حال لغو سفارش..." : "لغو سفارش"}
          </button>
        )}
      </div>
    </div>
  );
}

export default function OrderDetailPage() {
  return (
    <AuthGuard>
      <main dir="rtl" className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
        <OrderDetailContent />
      </main>
    </AuthGuard>
  );
}