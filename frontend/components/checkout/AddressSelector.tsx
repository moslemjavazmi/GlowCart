"use client";

import type { Address } from "@/lib/redux/features/addresses/addressTypes";

interface AddressSelectorProps {
  addresses: Address[];
  selectedAddressId: string | null;
  onSelect: (id: string) => void;
  onEdit: (address: Address) => void;
  onDelete: (id: string) => void;
  isDeleting: boolean;
}

export default function AddressSelector({
  addresses,
  selectedAddressId,
  onSelect,
  onEdit,
  onDelete,
  isDeleting,
}: AddressSelectorProps) {
  if (addresses.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-8 text-center">
        <p className="font-semibold text-gray-800">
          هنوز آدرسی ثبت نکرده‌اید.
        </p>

        <p className="mt-2 text-sm text-gray-500">
          برای ادامه خرید ابتدا یک آدرس تحویل ثبت کنید.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {addresses.map((address) => {
        const selected = selectedAddressId === address.id;

        return (
          <article
            key={address.id}
            className={`rounded-2xl border bg-white p-5 transition ${
              selected
                ? "border-pink-500 ring-2 ring-pink-100"
                : "border-gray-200"
            }`}
          >
            <div className="flex items-start gap-3">
              <input
                type="radio"
                name="selected-address"
                checked={selected}
                onChange={() => onSelect(address.id)}
                className="mt-1 h-4 w-4 accent-pink-600"
                aria-label={`انتخاب آدرس ${address.title}`}
              />

              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-bold text-gray-900">
                    {address.title}
                  </h3>

                  {address.is_default && (
                    <span className="rounded-full bg-pink-50 px-3 py-1 text-xs text-pink-600">
                      پیش‌فرض
                    </span>
                  )}
                </div>

                <p className="mt-3 text-sm text-gray-700">
                  {address.recipient_name}
                  {" · "}
                  {address.phone_number}
                </p>

                <p className="mt-2 text-sm leading-7 text-gray-500">
                  {address.province}، {address.city}،{" "}
                  {address.address_line}
                </p>

                <p className="mt-1 text-xs text-gray-400">
                  کد پستی: {address.postal_code}
                </p>

                <div className="mt-4 flex gap-4">
                  <button
                    type="button"
                    onClick={() => onEdit(address)}
                    className="text-xs font-semibold text-pink-600 hover:text-pink-700"
                  >
                    ویرایش
                  </button>

                  <button
                    type="button"
                    disabled={isDeleting}
                    onClick={() => onDelete(address.id)}
                    className="text-xs font-semibold text-red-500 hover:text-red-700 disabled:opacity-50"
                  >
                    حذف
                  </button>
                </div>
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}