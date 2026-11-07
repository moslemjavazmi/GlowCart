
"use client";

import Link from "next/link";

import ProductCard from "@/components/home/ProductCard";
import { useGetProductsQuery } from "@/lib/redux/services/catalogApi";

export default function HomePage() {
  const {
    data,
    isLoading,
    isError,
    refetch,
  } = useGetProductsQuery({
    page: 1,
    page_size: 8,
  });

  const products = data?.results ?? [];

  return (
    <main>
      {/* Hero */}
      <section className="overflow-hidden bg-gradient-to-l from-pink-100 via-rose-50 to-purple-50">
        <div className="mx-auto grid max-w-7xl items-center gap-10 px-4 py-20 md:grid-cols-2 md:py-28">
          <div>
            <span className="mb-5 inline-block rounded-full bg-white/80 px-4 py-2 text-sm font-medium text-pink-600">
              زیبایی، با انتخاب تو آغاز می‌شود
            </span>

            <h1 className="mb-6 text-4xl font-extrabold leading-tight text-gray-900 md:text-6xl">
              زیبایی خودت را
              <span className="block text-pink-600">
                کشف کن
              </span>
            </h1>

            <p className="mb-8 max-w-lg leading-8 text-gray-600">
              محصولات آرایشی و مراقبت از پوست را با تجربه‌ای
              ساده و لذت‌بخش در GlowCart پیدا کن.
            </p>

            <Link
              href="/products"
              className="inline-flex rounded-xl bg-pink-600 px-7 py-4 font-semibold text-white transition hover:bg-pink-700"
            >
              مشاهده محصولات
            </Link>
          </div>

          <div className="relative flex min-h-64 items-center justify-center md:min-h-96">
            <div className="absolute h-64 w-64 rounded-full bg-pink-200/70 blur-3xl md:h-80 md:w-80" />

            <div className="relative flex h-56 w-56 rotate-6 items-center justify-center rounded-[3rem] border border-white/70 bg-white/60 shadow-2xl backdrop-blur md:h-72 md:w-72">
              <span className="text-6xl font-black tracking-tight text-pink-200 md:text-8xl">
                G
              </span>
              <span className="absolute bottom-8 text-sm font-semibold tracking-widest text-pink-600">
                GLOWCART
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Categories */}
      <section className="mx-auto max-w-7xl px-4 py-16">
        <div className="mb-8 flex items-end justify-between">
          <div>
            <p className="mb-2 text-sm font-medium text-pink-600">
              EXPLORE
            </p>

            <h2 className="text-2xl font-bold text-gray-900">
              دسته‌بندی محصولات
            </h2>
          </div>

          <Link
            href="/products"
            className="text-sm font-medium text-pink-600 hover:text-pink-700"
          >
            همه محصولات
          </Link>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <Link
            href="/products?category=makeup"
            className="group rounded-2xl bg-gradient-to-l from-rose-100 to-pink-50 p-8 transition hover:shadow-md"
          >
            <span className="mb-4 block text-4xl">💄</span>
            <h3 className="text-xl font-bold text-gray-900">
              محصولات آرایشی
            </h3>
            <p className="mt-2 text-sm text-gray-600">
              محصولات مورد علاقه‌ات را کشف کن.
            </p>
            <span className="mt-5 inline-block text-sm font-semibold text-pink-600 group-hover:underline">
              مشاهده محصولات ←
            </span>
          </Link>

          <Link
            href="/products"
            className="group rounded-2xl bg-gradient-to-l from-purple-100 to-fuchsia-50 p-8 transition hover:shadow-md"
          >
            <span className="mb-4 block text-4xl">✨</span>
            <h3 className="text-xl font-bold text-gray-900">
              مراقبت و زیبایی
            </h3>
            <p className="mt-2 text-sm text-gray-600">
              برای مراقبت روزانه از خودت انتخاب کن.
            </p>
            <span className="mt-5 inline-block text-sm font-semibold text-purple-600 group-hover:underline">
              مشاهده محصولات ←
            </span>
          </Link>
        </div>
      </section>

      {/* Featured Products */}
      <section className="bg-gray-50 py-16">
        <div className="mx-auto max-w-7xl px-4">
          <div className="mb-8 flex items-end justify-between">
            <div>
              <p className="mb-2 text-sm font-medium text-pink-600">
                OUR PRODUCTS
              </p>

              <h2 className="text-2xl font-bold text-gray-900">
                محصولات فروشگاه
              </h2>

              <p className="mt-2 text-sm text-gray-500">
                جدیدترین محصولات موجود در GlowCart
              </p>
            </div>

            <Link
              href="/products"
              className="text-sm font-medium text-pink-600 hover:text-pink-700"
            >
              مشاهده همه
            </Link>
          </div>

          {isLoading ? (
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {Array.from({ length: 8 }).map((_, index) => (
                <div
                  key={index}
                  className="overflow-hidden rounded-2xl border border-gray-100 bg-white"
                >
                  <div className="aspect-[4/3] animate-pulse bg-gray-200" />
                  <div className="space-y-3 p-4">
                    <div className="h-3 w-1/3 animate-pulse rounded bg-gray-200" />
                    <div className="h-5 w-3/4 animate-pulse rounded bg-gray-200" />
                    <div className="h-4 w-1/2 animate-pulse rounded bg-gray-200" />
                  </div>
                </div>
              ))}
            </div>
          ) : isError ? (
            <div className="rounded-2xl border border-red-100 bg-white p-8 text-center">
              <p className="mb-4 text-red-600">
                دریافت محصولات با مشکل مواجه شد.
              </p>

              <button
                onClick={() => refetch()}
                className="rounded-lg bg-pink-600 px-5 py-2 text-sm text-white hover:bg-pink-700"
              >
                تلاش مجدد
              </button>
            </div>
          ) : products.length === 0 ? (
            <div className="rounded-2xl bg-white p-10 text-center">
              <p className="mb-4 text-gray-500">
                هنوز محصولی برای نمایش وجود ندارد.
              </p>

              <Link
                href="/products"
                className="font-medium text-pink-600"
              >
                مشاهده فروشگاه
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {products.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                />
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Newsletter placeholder / brand message */}
      <section className="mx-auto max-w-7xl px-4 py-20 text-center">
        <p className="mb-3 text-sm font-semibold text-pink-600">
          GLOWCART
        </p>

        <h2 className="mb-4 text-2xl font-bold text-gray-900 md:text-3xl">
          زیبایی، انتخابی برای هر روز
        </h2>

        <p className="mx-auto max-w-xl leading-8 text-gray-500">
          در GlowCart تلاش می‌کنیم انتخاب محصولات آرایشی و
          مراقبتی را برایت ساده‌تر و لذت‌بخش‌تر کنیم.
        </p>
      </section>
    </main>
  );
}
