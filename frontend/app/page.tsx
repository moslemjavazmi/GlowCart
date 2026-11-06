import Link from "next/link";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-gray-50">
      <h1 className="text-4xl font-bold text-pink-600">
        GlowCart
      </h1>

      <p className="text-gray-600">
        فروشگاه اینترنتی لوازم آرایشی
      </p>

      <div className="flex gap-4">
        <Link
          href="/login"
          className="rounded-lg bg-pink-600 px-6 py-3 text-white"
        >
          ورود
        </Link>

        <Link
          href="/register"
          className="rounded-lg border border-pink-600 px-6 py-3 text-pink-600"
        >
          ثبت‌نام
        </Link>

        <Link
          href="/account"
          className="rounded-lg border border-gray-300 px-6 py-3"
        >
          حساب کاربری
        </Link>
      </div>
    </main>
  );
}