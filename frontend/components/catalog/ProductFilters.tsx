"use client";

import { useEffect, useState } from "react";

import {
  useGetBrandsQuery,
  useGetCategoriesQuery,
} from "@/lib/redux/services/catalogApi";

import { useProductFilters } from "@/lib/redux/features/catalog/useProductFilters";

export default function ProductFilters() {
  const {
    filters,
    updateFilters,
    clearFilters,
  } = useProductFilters();

  const { data: categories = [], isLoading: categoriesLoading } =
    useGetCategoriesQuery();

  const { data: brands = [], isLoading: brandsLoading } =
    useGetBrandsQuery();

  const [search, setSearch] = useState(filters.q);
  const [minPrice, setMinPrice] = useState(filters.min_price);
  const [maxPrice, setMaxPrice] = useState(filters.max_price);

  useEffect(() => {
    setSearch(filters.q);
    setMinPrice(filters.min_price);
    setMaxPrice(filters.max_price);
  }, [filters.q, filters.min_price, filters.max_price]);

  const applyFilters = () => {
    void updateFilters({
      q: search.trim(),
      min_price: minPrice.trim(),
      max_price: maxPrice.trim(),
    });
  };

  return (
    <aside className="rounded-2xl border border-gray-100 bg-white p-5">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-lg font-bold text-gray-900">
          فیلتر محصولات
        </h2>

        <button
          type="button"
          onClick={() => void clearFilters()}
          className="text-xs font-medium text-pink-600 hover:text-pink-700"
        >
          حذف فیلترها
        </button>
      </div>

      {/* Search */}
      <div className="mb-6">
        <label
          htmlFor="product-search"
          className="mb-2 block text-sm font-medium text-gray-700"
        >
          جستجوی محصول
        </label>

        <input
          id="product-search"
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              applyFilters();
            }
          }}
          placeholder="نام محصول..."
          className="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm outline-none transition focus:border-pink-500 focus:ring-2 focus:ring-pink-100"
        />
      </div>

      {/* Category */}
      <div className="mb-6">
        <label
          htmlFor="product-category"
          className="mb-2 block text-sm font-medium text-gray-700"
        >
          دسته‌بندی
        </label>

        <select
          id="product-category"
          value={filters.category}
          onChange={(event) =>
            void updateFilters({
              category: event.target.value,
            })
          }
          disabled={categoriesLoading}
          className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-pink-500"
        >
          <option value="">
            همه دسته‌بندی‌ها
          </option>

          {categories.map((category) => (
            <option
              key={category.id}
              value={category.slug}
            >
              {category.name}
            </option>
          ))}
        </select>
      </div>

      {/* Brand */}
      <div className="mb-6">
        <label
          htmlFor="product-brand"
          className="mb-2 block text-sm font-medium text-gray-700"
        >
          برند
        </label>

        <select
          id="product-brand"
          value={filters.brand}
          onChange={(event) =>
            void updateFilters({
              brand: event.target.value,
            })
          }
          disabled={brandsLoading}
          className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-pink-500"
        >
          <option value="">
            همه برندها
          </option>

          {brands.map((brand) => (
            <option
              key={brand.id}
              value={brand.slug}
            >
              {brand.name}
            </option>
          ))}
        </select>
      </div>

      {/* Availability */}
      <div className="mb-6">
        <label
          htmlFor="product-stock"
          className="mb-2 block text-sm font-medium text-gray-700"
        >
          وضعیت موجودی
        </label>

        <select
          id="product-stock"
          value={filters.in_stock}
          onChange={(event) =>
            void updateFilters({
              in_stock: event.target.value,
            })
          }
          className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-pink-500"
        >
          <option value="all">همه محصولات</option>
          <option value="true">فقط موجود</option>
          <option value="false">فقط ناموجود</option>
        </select>
      </div>

      {/* Price range */}
      <div className="mb-6">
        <h3 className="mb-3 text-sm font-medium text-gray-700">
          محدوده قیمت
        </h3>

        <div className="space-y-3">
          <input
            type="number"
            min="0"
            value={minPrice}
            onChange={(event) => setMinPrice(event.target.value)}
            placeholder="حداقل قیمت"
            className="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm outline-none focus:border-pink-500"
          />

          <input
            type="number"
            min="0"
            value={maxPrice}
            onChange={(event) => setMaxPrice(event.target.value)}
            placeholder="حداکثر قیمت"
            className="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm outline-none focus:border-pink-500"
          />
        </div>
      </div>

      {/* Ordering */}
      <div className="mb-6">
        <label
          htmlFor="product-ordering"
          className="mb-2 block text-sm font-medium text-gray-700"
        >
          مرتب‌سازی
        </label>

        <select
          id="product-ordering"
          value={filters.ordering}
          onChange={(event) =>
            void updateFilters({
              ordering: event.target.value,
            })
          }
          className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-pink-500"
        >
          <option value="-created_at">جدیدترین</option>
          <option value="created_at">قدیمی‌ترین</option>
          <option value="min_variant_price">ارزان‌ترین</option>
          <option value="-min_variant_price">گران‌ترین</option>
          <option value="name">نام محصول (الف تا ی)</option>
          <option value="-name">نام محصول (ی تا الف)</option>
        </select>
      </div>

      <button
        type="button"
        onClick={applyFilters}
        className="w-full rounded-xl bg-pink-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-pink-700"
      >
        اعمال فیلتر قیمت و جستجو
      </button>
    </aside>
  );
}