"use client";

import Link from "next/link";
import AuthGuard from "@/components/auth/AuthGuard";
import OrderCard from "@/components/orders/OrderCard";
import { useGetOrdersQuery } from "@/lib/redux/services/orderApi";

function OrdersContent() {
  const { data: orders = [], isLoading, isError, refetch } =
    useGetOrdersQuery();

  return (
    <main dir="rtl" className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">سفارش‌های من</h1>
          <p className="mt-2 text-sm text-gray-500">
            فهرست سفارش‌هایی که در فروشگاه ثبت کرده‌اید.
          </p>
        </div>

        <Link
          href="/account"
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 transition hover:bg-gray-50"
        >
          بازگشت به حساب کاربری
        </Link>
      </div>

      {isLoading && (
        <div className="rounded-xl border bg-white p-10 text-center text-gray-500">
          در حال دریافت سفارش‌ها...
        </div>
      )}

      {isError && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm text-red-700">
            دریافت سفارش‌ها با خطا مواجه شد.
          </p>
          <button
            onClick={() => refetch()}
            className="mt-4 rounded-lg bg-red-600 px-5 py-2 text-sm text-white hover:bg-red-700"
          >
            تلاش مجدد
          </button>
        </div>
      )}

      {!isLoading && !isError && orders.length === 0 && (
        <div className="rounded-xl border border-gray-200 bg-white px-6 py-16 text-center">
          <h2 className="text-lg font-semibold text-gray-800">
            هنوز سفارشی ثبت نکرده‌اید
          </h2>
          <p className="mt-2 text-sm text-gray-500">
            بعد از ثبت سفارش، اطلاعات آن را در این قسمت مشاهده می‌کنید.
          </p>
          <Link
            href="/products"
            className="mt-6 inline-flex rounded-lg bg-black px-6 py-3 text-sm text-white hover:bg-gray-800"
          >
            مشاهده محصولات
          </Link>
        </div>
      )}

      {!isLoading && !isError && orders.length > 0 && (
        <div className="space-y-4">
          <p className="text-sm text-gray-500">
            تعداد سفارش‌ها: {orders.length.toLocaleString("fa-IR")}
          </p>

          {orders.map((order) => (
            <OrderCard key={order.id} order={order} />
          ))}
        </div>
      )}
    </main>
  );
}

export default function OrdersPage() {
  return (
    <AuthGuard>
      <OrdersContent />
    </AuthGuard>
  );
}