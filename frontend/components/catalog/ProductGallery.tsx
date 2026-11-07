"use client";

import { useEffect, useMemo, useState } from "react";

import type { ProductImage } from "@/lib/redux/features/catalog/catalogTypes";

interface ProductGalleryProps {
  images: ProductImage[];
  productName: string;
}

export default function ProductGallery({
  images,
  productName,
}: ProductGalleryProps) {
  const sortedImages = useMemo(
    () =>
      [...images].sort((a, b) => {
        if (a.is_primary !== b.is_primary) {
          return a.is_primary ? -1 : 1;
        }

        return a.sort_order - b.sort_order;
      }),
    [images]
  );

  const [selectedImageId, setSelectedImageId] =
    useState<number | null>(null);

  useEffect(() => {
    setSelectedImageId(sortedImages[0]?.id ?? null);
  }, [sortedImages]);

  const selectedImage = sortedImages.find(
    (image) => image.id === selectedImageId
  );

  if (sortedImages.length === 0) {
    return (
      <div className="flex aspect-square items-center justify-center rounded-3xl bg-gray-100 text-sm text-gray-400">
        تصویری برای این محصول ثبت نشده است.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="overflow-hidden rounded-3xl border border-gray-100 bg-white">
        {selectedImage && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={selectedImage.image}
            alt={selectedImage.alt_text || productName}
            className="aspect-square w-full object-contain p-4"
          />
        )}
      </div>

      {sortedImages.length > 1 && (
        <div className="flex flex-wrap gap-3">
          {sortedImages.map((image) => {
            const isSelected = image.id === selectedImageId;

            return (
              <button
                key={image.id}
                type="button"
                onClick={() => setSelectedImageId(image.id)}
                aria-label={`نمایش تصویر ${image.alt_text || productName}`}
                aria-pressed={isSelected}
                className={`h-20 w-20 overflow-hidden rounded-xl border-2 bg-white transition ${
                  isSelected
                    ? "border-pink-500"
                    : "border-gray-200 hover:border-pink-300"
                }`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={image.image}
                  alt={image.alt_text || productName}
                  className="h-full w-full object-contain p-1"
                />
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}