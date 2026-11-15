"use client";

import Link from "next/link";

import AuthGuard from "@/components/auth/AuthGuard";
import LogoutButton from "@/components/auth/LogoutButton";
import { useAppSelector } from "@/lib/redux/hooks";
import { selectCurrentUser } from "@/lib/redux/features/auth/authSelectors";
import { useGetOrdersQuery } from "@/lib/redux/services/orderApi";

function AccountContent() {
  const user = useAppSelector(selectCurrentUser);
  const { data: orders = [], isLoading: ordersLoading } =
    useGetOrdersQuery();

  return (
    <main dir="rtl" className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
        <h1 className="text-2xl font-bold text-gray-900">
          حساب کاربری من
        </h1>

        <p className="mt-2 text-sm text-gray-500">
          مدیریت اطلاعات حساب و مشاهده سفارش‌ها
        </p>

        <div className="mt-8 grid gap-5 sm:grid-cols-2">
          <div className="rounded-xl bg-gray-50 p-4">
            <p className="text-sm text-gray-500">ایمیل</p>
            <p className="mt-2 break-all font-medium text-gray-900">
              {user?.email || "—"}
            </p>
          </div>

          <div className="rounded-xl bg-gray-50 p-4">
            <p className="text-sm text-gray-500">نقش کاربر</p>
            <p className="mt-2 font-medium text-gray-900">
              {user?.role || "—"}
            </p>
          </div>

          <div className="rounded-xl bg-gray-50 p-4">
            <p className="text-sm text-gray-500">وضعیت تأیید ایمیل</p>
            <p
              className={`mt-2 font-medium ${
                user?.is_email_verified
                  ? "text-green-700"
                  : "text-amber-700"
              }`}
            >
              {user?.is_email_verified ? "تأیید شده" : "تأیید نشده"}
            </p>
          </div>

          <div className="rounded-xl bg-gray-50 p-4">
            <p className="text-sm text-gray-500">تعداد سفارش‌ها</p>
            <p className="mt-2 font-medium text-gray-900">
              {ordersLoading
                ? "در حال دریافت..."
                : orders.length.toLocaleString("fa-IR")}
            </p>
          </div>
        </div>

        <div className="mt-8 border-t border-gray-100 pt-6">
          <h2 className="font-semibold text-gray-900">
            دسترسی سریع
          </h2>

          <div className="mt-4 flex flex-wrap gap-3">
            <Link
              href="/orders"
              className="rounded-lg bg-black px-5 py-3 text-sm text-white transition hover:bg-gray-800"
            >
              مشاهده سفارش‌های من
            </Link>

            <Link
              href="/"
              className="rounded-lg border border-gray-300 px-5 py-3 text-sm text-gray-700 transition hover:bg-gray-50"
            >
              صفحه اصلی فروشگاه
            </Link>

            <LogoutButton />
          </div>
        </div>
      </div>
    </main>
  );
}

export default function AccountPage() {
  return (
    <AuthGuard>
      <AccountContent />
    </AuthGuard>
  );
}