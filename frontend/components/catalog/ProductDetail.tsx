"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import ProductGallery from "@/components/catalog/ProductGallery";
import ProductVariantSelector from "@/components/catalog/ProductVariantSelector";

import { useGetProductBySlugQuery } from "@/lib/redux/services/catalogApi";
import AddToCartButton from "@/components/cart/AddToCartButton";
interface ProductDetailProps {
  slug: string;
}

export default function ProductDetail({
  slug,
}: ProductDetailProps) {
  const {
    data: product,
    isLoading,
    isError,
    refetch,
  } = useGetProductBySlugQuery(slug);

  const [selectedVariantId, setSelectedVariantId] =
    useState<number | null>(null);

  useEffect(() => {
    if (!product) return;

    const firstAvailableVariant = product.variants.find(
      (variant) => variant.stock > 0
    );

    setSelectedVariantId(
      firstAvailableVariant?.id ??
        product.variants[0]?.id ??
        null
    );
  }, [product]);

  const selectedVariant = product?.variants.find(
    (variant) => variant.id === selectedVariantId
  );

  if (isLoading) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-16">
        <div className="grid animate-pulse gap-10 md:grid-cols-2">
          <div className="aspect-square rounded-3xl bg-gray-200" />

          <div className="space-y-5">
            <div className="h-5 w-1/3 rounded bg-gray-200" />
            <div className="h-9 w-3/4 rounded bg-gray-200" />
            <div className="h-5 w-1/2 rounded bg-gray-200" />
            <div className="h-32 rounded bg-gray-200" />
          </div>
        </div>
      </main>
    );
  }

  if (isError || !product) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-20 text-center">
        <h1 className="text-xl font-bold text-gray-900">
          دریافت اطلاعات محصول ناموفق بود.
        </h1>

        <button
          type="button"
          onClick={() => void refetch()}
          className="mt-5 rounded-xl bg-pink-600 px-6 py-3 text-sm text-white"
        >
          تلاش مجدد
        </button>

        <div>
          <Link
            href="/products"
            className="mt-5 inline-block text-sm text-gray-500 hover:text-pink-600"
          >
            بازگشت به فروشگاه
          </Link>
        </div>
      </main>
    );
  }

  const hasAvailableVariant = product.variants.some(
    (variant) => variant.stock > 0
  );

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <nav className="mb-8 text-sm text-gray-500">
          <Link href="/" className="hover:text-pink-600">
            خانه
          </Link>

          <span className="mx-2">/</span>

          <Link href="/products" className="hover:text-pink-600">
            فروشگاه
          </Link>

          <span className="mx-2">/</span>

          <span className="text-gray-800">
            {product.name}
          </span>
        </nav>

        <div className="grid items-start gap-10 rounded-3xl border border-gray-100 bg-white p-5 md:grid-cols-2 md:p-8">
          <ProductGallery
            images={product.images}
            productName={product.name}
          />

          <div>
            <div className="mb-4 flex flex-wrap gap-2">
              <span className="rounded-full bg-pink-50 px-3 py-1 text-xs font-medium text-pink-700">
                {product.category.name}
              </span>

              {product.brand && (
                <span className="rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-600">
                  {product.brand.name}
                </span>
              )}
            </div>

            <h1 className="text-2xl font-bold text-gray-900 md:text-3xl">
              {product.name}
            </h1>

            <p className="mt-5 whitespace-pre-line text-sm leading-8 text-gray-600">
              {product.description || "توضیحاتی برای این محصول ثبت نشده است."}
            </p>

            <div className="my-7 border-t border-gray-100" />

            <ProductVariantSelector
              variants={product.variants}
              selectedVariantId={selectedVariantId}
              onSelect={setSelectedVariantId}
            />

            {selectedVariant && (
              <>
                <div className="mt-7 rounded-2xl bg-gray-50 p-5">
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-sm text-gray-500">
                      قیمت
                    </span>

                    <strong className="text-xl font-bold text-gray-900">
                      {Number(selectedVariant.price).toLocaleString("fa-IR")}
                    </strong>
                  </div>

                  <div className="mt-4 flex items-center justify-between gap-4">
                    <span className="text-sm text-gray-500">
                      موجودی
                    </span>

                    <span
                      className={`text-sm font-semibold ${
                        selectedVariant.stock > 0
                          ? "text-green-600"
                          : "text-red-600"
                      }`}
                    >
                      {selectedVariant.stock > 0
                        ? `${selectedVariant.stock.toLocaleString("fa-IR")} عدد`
                        : "ناموجود"}
                    </span>
                  </div>

                  <div className="mt-4 flex items-center justify-between gap-4">
                    <span className="text-sm text-gray-500">
                      کد محصول
                    </span>

                    <span className="text-sm font-medium text-gray-700">
                      {selectedVariant.sku}
                    </span>
                  </div>
                </div>

                <AddToCartButton variant={selectedVariant} />
              </>
            )}

            {!hasAvailableVariant && (
              <div className="mt-6 rounded-xl bg-red-50 p-4 text-sm text-red-600">
                تمام تنوع‌های این محصول ناموجود هستند.
              </div>
            )}

            <p className="mt-6 text-xs text-gray-400">
              شناسه محصول: {product.id}
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}