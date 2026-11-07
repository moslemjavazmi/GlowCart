
"use client";

import Link from "next/link";

import { useAppSelector } from "@/lib/redux/hooks";
import LogoutButton from "@/components/auth/LogoutButton";

export default function Header() {
  const user = useAppSelector((state) => state.auth.user);
  const isAuthenticated = useAppSelector(
    (state) => state.auth.isAuthenticated
  );
  const isInitialized = useAppSelector(
    (state) => state.auth.isInitialized
  );

  return (
    <header className="sticky top-0 z-50 border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
        {/* Logo */}
        <Link href="/" className="text-2xl font-bold tracking-tight">
          Glow<span className="text-pink-600">Cart</span>
        </Link>

        {/* Navigation */}
        <nav className="hidden items-center gap-7 md:flex">
          <Link
            href="/"
            className="text-sm text-gray-700 transition hover:text-pink-600"
          >
            خانه
          </Link>

          <Link
            href="/products"
            className="text-sm text-gray-700 transition hover:text-pink-600"
          >
            همه محصولات
          </Link>

          <Link
            href="/products?category=makeup"
            className="text-sm text-gray-700 transition hover:text-pink-600"
          >
            آرایشی
          </Link>

          <Link
            href="/products?category=skincare"
            className="text-sm text-gray-700 transition hover:text-pink-600"
          >
            مراقبت پوست
          </Link>
        </nav>

        {/* User Actions */}
        <div className="flex items-center gap-3">
          {!isInitialized ? (
            <span className="text-sm text-gray-400">
              ...
            </span>
          ) : isAuthenticated && user ? (
            <>
              <Link
                href="/account"
                className="hidden text-sm text-gray-700 hover:text-pink-600 sm:block"
              >
                حساب کاربری
              </Link>

              <LogoutButton />
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="text-sm text-gray-700 hover:text-pink-600"
              >
                ورود
              </Link>

              <Link
                href="/register"
                className="rounded-lg bg-pink-600 px-4 py-2 text-sm text-white transition hover:bg-pink-700"
              >
                ثبت‌نام
              </Link>
            </>
          )}
        </div>
      </div>

      {/* Mobile Navigation */}
      <nav className="flex items-center justify-center gap-6 border-t border-gray-100 px-4 py-3 md:hidden">
        <Link href="/" className="text-xs text-gray-700">
          خانه
        </Link>

        <Link href="/products" className="text-xs text-gray-700">
          محصولات
        </Link>

        <Link
          href="/products?category=makeup"
          className="text-xs text-gray-700"
        >
          آرایشی
        </Link>

        <Link
          href="/products?category=skincare"
          className="text-xs text-gray-700"
        >
          مراقبت پوست
        </Link>
      </nav>
    </header>
  );
}
