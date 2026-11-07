
"use client";

import { useProductFilters } from "@/lib/redux/features/catalog/useProductFilters";

interface ProductPaginationProps {
  count: number;
  pageSize: number;
}

export default function ProductPagination({
  count,
  pageSize,
}: ProductPaginationProps) {
  const { filters, changePage } = useProductFilters();

  const totalPages = Math.ceil(count / pageSize);
  const currentPage = filters.page;

  if (totalPages <= 1) return null;

  const pages = Array.from(
    { length: totalPages },
    (_, index) => index + 1
  ).filter(
    (page) =>
      page === 1 ||
      page === totalPages ||
      Math.abs(page - currentPage) <= 1
  );

  return (
    <nav
      aria-label="صفحه‌بندی محصولات"
      className="mt-10 flex flex-wrap items-center justify-center gap-2"
    >
      <button
        type="button"
        disabled={currentPage <= 1}
        onClick={() => void changePage(currentPage - 1)}
        className="rounded-lg border border-gray-200 px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-40"
      >
        قبلی
      </button>

      {pages.map((page, index) => {
        const previous = pages[index - 1];
        const hasGap = previous && page - previous > 1;

        return (
          <span key={page} className="contents">
            {hasGap && (
              <span className="px-2 text-gray-400">...</span>
            )}

            <button
              type="button"
              onClick={() => void changePage(page)}
              aria-current={
                page === currentPage ? "page" : undefined
              }
              className={`h-10 min-w-10 rounded-lg border px-3 text-sm ${
                page === currentPage
                  ? "border-pink-600 bg-pink-600 text-white"
                  : "border-gray-200 bg-white text-gray-700 hover:border-pink-400"
              }`}
            >
              {page}
            </button>
          </span>
        );
      })}

      <button
        type="button"
        disabled={currentPage >= totalPages}
        onClick={() => void changePage(currentPage + 1)}
        className="rounded-lg border border-gray-200 px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-40"
      >
        بعدی
      </button>
    </nav>
  );
}
