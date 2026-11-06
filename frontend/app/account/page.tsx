"use client";

import Link from "next/link";

import AuthGuard from "@/components/auth/AuthGuard";
import LogoutButton from "@/components/auth/LogoutButton";

import { useAppSelector } from "@/lib/redux/hooks";
import { selectCurrentUser } from "@/lib/redux/features/auth/authSelectors";

function AccountContent() {
  const user = useAppSelector(selectCurrentUser);

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <div className="rounded-2xl border border-gray-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-bold">حساب کاربری من</h1>

        <div className="mt-8 space-y-4">
          <div>
            <span className="text-sm text-gray-500">ایمیل</span>
            <p className="font-medium">{user?.email}</p>
          </div>

          <div>
            <span className="text-sm text-gray-500">نقش کاربر</span>
            <p className="font-medium">{user?.role}</p>
          </div>

          <div>
            <span className="text-sm text-gray-500">وضعیت تأیید ایمیل</span>
            <p className="font-medium">
              {user?.is_email_verified ? "تأیید شده" : "تأیید نشده"}
            </p>
          </div>
        </div>

        <div className="mt-8 flex flex-wrap gap-4">
          <Link
            href="/"
            className="rounded-lg border border-gray-300 px-5 py-3"
          >
            صفحه اصلی
          </Link>

          <LogoutButton />
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