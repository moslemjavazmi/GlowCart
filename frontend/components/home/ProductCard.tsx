
import Link from "next/link";

import type { Product } from "@/lib/redux/features/catalog/catalogTypes";

interface ProductCardProps {
  product: Product;
}

function formatPrice(price: string): string {
  const value = Number(price);

  if (!Number.isFinite(value)) {
    return price;
  }

  return new Intl.NumberFormat("fa-IR").format(value);
}

export default function ProductCard({ product }: ProductCardProps) {
  const availableVariant = product.variants.find(
    (variant) => variant.stock > 0
  );

  const firstVariant = product.variants[0];

  const priceVariant = availableVariant ?? firstVariant;

  const isAvailable = Boolean(availableVariant);

  return (
    <article className="group overflow-hidden rounded-2xl border border-gray-100 bg-white transition duration-300 hover:-translate-y-1 hover:shadow-lg">
      <Link href={`/products/${product.slug}`}>
        {/* Temporary product image placeholder */}
        <div className="relative flex aspect-[4/3] items-center justify-center overflow-hidden bg-gradient-to-br from-pink-50 via-rose-50 to-purple-50">
          <span className="text-5xl font-bold text-pink-200 transition duration-300 group-hover:scale-110">
            G
          </span>

          {!isAvailable && (
            <span className="absolute right-3 top-3 rounded-full bg-gray-900 px-3 py-1 text-xs text-white">
              ناموجود
            </span>
          )}
        </div>

        <div className="p-4">
          {product.brand && (
            <p className="mb-2 text-xs text-gray-400">
              {product.brand.name}
            </p>
          )}

          <h3 className="mb-2 line-clamp-2 min-h-12 font-semibold text-gray-800 transition group-hover:text-pink-600">
            {product.name}
          </h3>

          <p className="mb-4 text-xs text-gray-500">
            {product.category.name}
          </p>

          <div className="flex items-center justify-between gap-2">
            {priceVariant ? (
              <div>
                <p className="text-xs text-gray-400">
                  {isAvailable ? "قیمت" : "آخرین قیمت ثبت‌شده"}
                </p>

                <p className="mt-1 font-bold text-gray-900">
                  {formatPrice(priceVariant.price)}
                  <span className="mr-1 text-xs font-normal text-gray-500">
                    تومان
                  </span>
                </p>
              </div>
            ) : (
              <p className="text-sm text-gray-400">
                قیمت ثبت نشده
              </p>
            )}

            <span className="rounded-lg bg-pink-50 px-3 py-2 text-xs font-medium text-pink-600 transition group-hover:bg-pink-600 group-hover:text-white">
              مشاهده
            </span>
          </div>
        </div>
      </Link>
    </article>
  );
}
