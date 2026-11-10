"use client";

import { useEffect, useState } from "react";

import type {
  Address,
  AddressPayload,
} from "@/lib/redux/features/addresses/addressTypes";

interface AddressFormProps {
  initialAddress?: Address | null;
  isSaving: boolean;
  onSubmit: (data: AddressPayload) => void;
  onCancel: () => void;
}

const emptyForm: AddressPayload = {
  title: "",
  recipient_name: "",
  phone_number: "",
  province: "",
  city: "",
  postal_code: "",
  address_line: "",
  is_default: false,
};

export default function AddressForm({
  initialAddress,
  isSaving,
  onSubmit,
  onCancel,
}: AddressFormProps) {
  const [form, setForm] = useState<AddressPayload>(emptyForm);

  useEffect(() => {
    if (initialAddress) {
      setForm({
        title: initialAddress.title,
        recipient_name: initialAddress.recipient_name,
        phone_number: initialAddress.phone_number,
        province: initialAddress.province,
        city: initialAddress.city,
        postal_code: initialAddress.postal_code,
        address_line: initialAddress.address_line,
        is_default: initialAddress.is_default,
      });
    } else {
      setForm(emptyForm);
    }
  }, [initialAddress]);

  const handleChange = (
    event: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement
    >
  ) => {
    const { name, value } = event.target;

    setForm((current) => ({
      ...current,
      [name]: value,
    }));
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    onSubmit({
      ...form,
      title: form.title.trim(),
      recipient_name: form.recipient_name.trim(),
      phone_number: form.phone_number.trim(),
      province: form.province.trim(),
      city: form.city.trim(),
      postal_code: form.postal_code.trim(),
      address_line: form.address_line.trim(),
    });
  };

  const inputClass =
    "w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-pink-500 focus:ring-2 focus:ring-pink-100";

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-5 rounded-2xl border border-gray-100 bg-white p-5 sm:p-6"
    >
      <div>
        <h3 className="font-bold text-gray-900">
          {initialAddress ? "ویرایش آدرس" : "افزودن آدرس جدید"}
        </h3>

        <p className="mt-1 text-xs text-gray-500">
          اطلاعات گیرنده و نشانی محل تحویل سفارش را وارد کنید.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="space-y-2">
          <span className="text-sm font-medium text-gray-700">
            عنوان آدرس
          </span>

          <input
            name="title"
            value={form.title}
            onChange={handleChange}
            required
            maxLength={100}
            placeholder="مثلاً خانه یا محل کار"
            className={inputClass}
          />
        </label>

        <label className="space-y-2">
          <span className="text-sm font-medium text-gray-700">
            نام تحویل‌گیرنده
          </span>

          <input
            name="recipient_name"
            value={form.recipient_name}
            onChange={handleChange}
            required
            maxLength={150}
            className={inputClass}
          />
        </label>

        <label className="space-y-2">
          <span className="text-sm font-medium text-gray-700">
            شماره موبایل
          </span>

          <input
            name="phone_number"
            value={form.phone_number}
            onChange={handleChange}
            required
            maxLength={20}
            inputMode="tel"
            className={inputClass}
          />
        </label>

        <label className="space-y-2">
          <span className="text-sm font-medium text-gray-700">
            استان
          </span>

          <input
            name="province"
            value={form.province}
            onChange={handleChange}
            required
            maxLength={100}
            className={inputClass}
          />
        </label>

        <label className="space-y-2">
          <span className="text-sm font-medium text-gray-700">
            شهر
          </span>

          <input
            name="city"
            value={form.city}
            onChange={handleChange}
            required
            maxLength={100}
            className={inputClass}
          />
        </label>

        <label className="space-y-2">
          <span className="text-sm font-medium text-gray-700">
            کد پستی
          </span>

          <input
            name="postal_code"
            value={form.postal_code}
            onChange={handleChange}
            required
            maxLength={20}
            inputMode="numeric"
            className={inputClass}
          />
        </label>
      </div>

      <label className="block space-y-2">
        <span className="text-sm font-medium text-gray-700">
          نشانی کامل
        </span>

        <textarea
          name="address_line"
          value={form.address_line}
          onChange={handleChange}
          required
          rows={4}
          className={inputClass}
          placeholder="خیابان، کوچه، پلاک، واحد و..."
        />
      </label>

      <label className="flex cursor-pointer items-center gap-2 text-sm text-gray-600">
        <input
          type="checkbox"
          checked={form.is_default}
          onChange={(event) =>
            setForm((current) => ({
              ...current,
              is_default: event.target.checked,
            }))
          }
          className="h-4 w-4 accent-pink-600"
        />

        ثبت به عنوان آدرس پیش‌فرض
      </label>

      <div className="flex flex-wrap gap-3">
        <button
          type="submit"
          disabled={isSaving}
          className="rounded-xl bg-pink-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-pink-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSaving
            ? "در حال ذخیره..."
            : initialAddress
              ? "ذخیره تغییرات"
              : "ثبت آدرس"}
        </button>

        <button
          type="button"
          onClick={onCancel}
          disabled={isSaving}
          className="rounded-xl border border-gray-200 px-6 py-3 text-sm font-medium text-gray-600 hover:bg-gray-50"
        >
          انصراف
        </button>
      </div>
    </form>
  );
}