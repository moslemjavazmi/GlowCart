"use client";

import { useMemo } from "react";

import ProductCard from "@/components/home/ProductCard";
import ProductFilters from "@/components/catalog/ProductFilters";
import ProductPagination from "@/components/catalog/ProductPagination";

import { useProductFilters } from "@/lib/redux/features/catalog/useProductFilters";
import { useGetProductsQuery } from "@/lib/redux/services/catalogApi";

const PAGE_SIZE = 12;

export default function ProductListing() {
  const { filters } = useProductFilters();

  const queryParams = useMemo(() => {
    const minPrice =
      filters.min_price.trim() !== ""
        ? Number(filters.min_price)
        : undefined;

    const maxPrice =
      filters.max_price.trim() !== ""
        ? Number(filters.max_price)
        : undefined;

    return {
      page: filters.page,
      page_size: PAGE_SIZE,

      search: filters.q.trim() || undefined,

      category: filters.category || undefined,
      brand: filters.brand || undefined,

      in_stock:
        filters.in_stock === "all"
          ? undefined
          : filters.in_stock === "true",

      min_price:
        minPrice !== undefined && Number.isFinite(minPrice)
          ? minPrice
          : undefined,

      max_price:
        maxPrice !== undefined && Number.isFinite(maxPrice)
          ? maxPrice
          : undefined,

      ordering: filters.ordering,
    };
  }, [filters]);

  const {
    data,
    isLoading,
    isFetching,
    isError,
    refetch,
  } = useGetProductsQuery(queryParams);

  const products = data?.results ?? [];
  const count = data?.count ?? 0;

  return (
    <main className="min-h-screen bg-gray-50">
      <section className="border-b border-gray-100 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-10">
          <p className="mb-2 text-sm font-medium text-pink-600">
            GLOWCART STORE
          </p>

          <h1 className="text-3xl font-bold text-gray-900">
            فروشگاه محصولات
          </h1>

          <p className="mt-3 text-sm text-gray-500">
            محصولات آرایشی و مراقبت از پوست را پیدا کن.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-10">
        <div className="grid grid-cols-1 items-start gap-8 lg:grid-cols-[280px_1fr]">
          <ProductFilters />

          <div className="min-w-0">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-gray-900">
                  محصولات
                </h2>

                <p className="mt-1 text-xs text-gray-500">
                  {count.toLocaleString("fa-IR")} محصول
                </p>
              </div>

              {isFetching && (
                <span className="text-xs text-pink-600">
                  در حال بروزرسانی محصولات...
                </span>
              )}
            </div>

            {isLoading ? (
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
                {Array.from({ length: PAGE_SIZE }).map((_, index) => (
                  <div
                    key={index}
                    className="animate-pulse overflow-hidden rounded-2xl bg-white"
                  >
                    <div className="aspect-[4/3] bg-gray-200" />

                    <div className="space-y-3 p-4">
                      <div className="h-4 w-1/3 rounded bg-gray-200" />
                      <div className="h-5 w-3/4 rounded bg-gray-200" />
                      <div className="h-4 w-1/2 rounded bg-gray-200" />
                    </div>
                  </div>
                ))}
              </div>
            ) : isError ? (
              <div className="rounded-2xl border border-red-100 bg-white p-10 text-center">
                <p className="mb-4 text-red-600">
                  دریافت محصولات با خطا مواجه شد.
                </p>

                <button
                  type="button"
                  onClick={() => void refetch()}
                  className="rounded-lg bg-pink-600 px-5 py-2 text-sm text-white"
                >
                  تلاش مجدد
                </button>
              </div>
            ) : products.length === 0 ? (
              <div className="rounded-2xl border border-gray-100 bg-white p-12 text-center">
                <h3 className="mb-3 text-lg font-bold text-gray-800">
                  محصولی پیدا نشد
                </h3>

                <p className="mb-5 text-sm text-gray-500">
                  فیلترها را تغییر بده یا جستجوی دیگری انجام بده.
                </p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
                  {products.map((product) => (
                    <ProductCard
                      key={product.id}
                      product={product}
                    />
                  ))}
                </div>

                <ProductPagination
                  count={count}
                  pageSize={PAGE_SIZE}
                />
              </>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}