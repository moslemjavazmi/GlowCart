
"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { useGetPaymentQuery } from "@/lib/redux/services/paymentApi";
import type { PaymentStatus } from "@/lib/redux/features/payments/paymentTypes";

const FINAL_STATUSES: PaymentStatus[] = [
  "success",
  "failed",
  "cancelled",
  "review_required",
];

const STATUS_CONTENT: Record<
  PaymentStatus,
  { title: string; description: string }
> = {
  initiated: {
    title: "درخواست پرداخت ثبت شد",
    description: "در حال آماده‌سازی اطلاعات پرداخت هستیم.",
  },
  pending: {
    title: "پرداخت در انتظار تأیید است",
    description: "در حال بررسی نتیجه تراکنش از درگاه پرداخت هستیم.",
  },
  unknown: {
    title: "نتیجه پرداخت هنوز مشخص نیست",
    description:
      "نتیجه تراکنش هنوز قطعی نیست. لطفاً تا مشخص شدن وضعیت نهایی، پرداخت دیگری انجام ندهید.",
  },
  success: {
    title: "پرداخت با موفقیت انجام شد",
    description: "پرداخت شما تأیید شده و سفارش ثبت نهایی شده است.",
  },
  failed: {
    title: "پرداخت ناموفق بود",
    description:
      "پرداخت توسط درگاه تأیید نشد. اگر مبلغی از حساب شما کسر شده است، موضوع را پیگیری کنید.",
  },
  cancelled: {
    title: "پرداخت لغو شد",
    description: "تراکنش پرداخت لغو شده است.",
  },
  review_required: {
    title: "پرداخت نیازمند بررسی است",
    description:
      "نتیجه تراکنش نیاز به بررسی بیشتر دارد. لطفاً از انجام پرداخت مجدد خودداری کنید.",
  },
};

function PaymentResultContent() {
  const searchParams = useSearchParams();

  const paymentId = searchParams.get("payment_id");

  const {
    currentData: payment,
    isLoading,
    isFetching,
    isError,
    refetch,
  } = useGetPaymentQuery(paymentId ?? "", {
    skip: !paymentId,
    pollingInterval: 5000,
    skipPollingIfUnfocused: true,
  });

  const status = payment?.status;

  const isFinal = status
    ? FINAL_STATUSES.includes(status)
    : false;

  const isSuccess = status === "success";
  const isReviewRequired = status === "review_required";

  const canRetry =
    status === "failed" || status === "cancelled";

  const content = status
    ? STATUS_CONTENT[status]
    : null;

  if (!paymentId) {
    return (
      <main
        dir="rtl"
        className="mx-auto flex min-h-[70vh] max-w-2xl items-center justify-center px-4 py-12"
      >
        <section className="w-full rounded-2xl border border-gray-200 bg-white p-8 text-center shadow-sm">
          <h1 className="mb-3 text-xl font-bold text-gray-900">
            اطلاعات پرداخت پیدا نشد
          </h1>

          <p className="mb-6 text-sm leading-7 text-gray-600">
            شناسه پرداخت در آدرس صفحه وجود ندارد. برای بررسی وضعیت سفارش،
            از حساب کاربری خود وارد بخش سفارش‌ها شوید.
          </p>

          <Link
            href="/"
            className="inline-flex rounded-lg bg-gray-900 px-6 py-3 text-sm font-medium text-white transition hover:bg-gray-700"
          >
            بازگشت به فروشگاه
          </Link>
        </section>
      </main>
    );
  }

  if (isLoading && !payment) {
    return (
      <main
        dir="rtl"
        className="mx-auto flex min-h-[70vh] max-w-2xl items-center justify-center px-4 py-12"
      >
        <section className="w-full rounded-2xl border border-gray-200 bg-white p-8 text-center">
          <div className="mx-auto mb-5 h-10 w-10 animate-spin rounded-full border-4 border-gray-200 border-t-gray-900" />

          <h1 className="text-lg font-bold text-gray-900">
            در حال دریافت نتیجه پرداخت
          </h1>

          <p className="mt-2 text-sm text-gray-600">
            لطفاً چند لحظه صبر کنید.
          </p>
        </section>
      </main>
    );
  }

  if (isError && !payment) {
    return (
      <main
        dir="rtl"
        className="mx-auto flex min-h-[70vh] max-w-2xl items-center justify-center px-4 py-12"
      >
        <section className="w-full rounded-2xl border border-red-200 bg-white p-8 text-center">
          <h1 className="mb-3 text-xl font-bold text-gray-900">
            دریافت نتیجه پرداخت ناموفق بود
          </h1>

          <p className="mb-6 text-sm leading-7 text-gray-600">
            در حال حاضر نتوانستیم وضعیت تراکنش را از سرور دریافت کنیم.
            این موضوع لزوماً به معنی ناموفق بودن پرداخت نیست.
          </p>

          <button
            type="button"
            onClick={() => void refetch()}
            className="rounded-lg bg-gray-900 px-6 py-3 text-sm font-medium text-white transition hover:bg-gray-700"
          >
            تلاش مجدد
          </button>
        </section>
      </main>
    );
  }

  return (
    <main
      dir="rtl"
      className="mx-auto flex min-h-[70vh] max-w-2xl items-center justify-center px-4 py-12"
    >
      <section className="w-full rounded-2xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
        <div className="mb-6 text-center">
          <div
            className={`mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full text-2xl font-bold ${
              isSuccess
                ? "bg-green-100 text-green-700"
                : isReviewRequired
                  ? "bg-amber-100 text-amber-700"
                  : status === "failed" || status === "cancelled"
                    ? "bg-red-100 text-red-700"
                    : "bg-blue-100 text-blue-700"
            }`}
          >
            {isSuccess
              ? "✓"
              : isReviewRequired
                ? "!"
                : status === "failed" || status === "cancelled"
                  ? "×"
                  : "…"}
          </div>

          <h1 className="text-xl font-bold text-gray-900">
            {content?.title ?? "در حال بررسی پرداخت"}
          </h1>

          <p className="mt-3 text-sm leading-7 text-gray-600">
            {content?.description ??
              "وضعیت پرداخت هنوز از سرور دریافت نشده است."}
          </p>
        </div>

        <div className="space-y-4 rounded-xl bg-gray-50 p-4">
          <div className="flex items-center justify-between gap-4 text-sm">
            <span className="text-gray-500">شماره سفارش</span>
            <span className="font-medium text-gray-900">
              {payment?.order_number ?? "—"}
            </span>
          </div>

          <div className="flex items-center justify-between gap-4 text-sm">
            <span className="text-gray-500">مبلغ پرداخت</span>
            <span className="font-medium text-gray-900">
              {payment?.amount
                ? `${Number(payment.amount).toLocaleString("fa-IR")} تومان`
                : "—"}
            </span>
          </div>

          <div className="flex items-center justify-between gap-4 text-sm">
            <span className="text-gray-500">شناسه پرداخت</span>
            <span className="max-w-[65%] break-all text-left text-xs text-gray-700">
              {payment?.payment_id ?? paymentId}
            </span>
          </div>

          <div className="flex items-center justify-between gap-4 text-sm">
            <span className="text-gray-500">وضعیت</span>
            <span className="font-medium text-gray-900">
              {status ?? "در انتظار دریافت"}
            </span>
          </div>

          {payment?.provider_reference && (
            <div className="flex items-center justify-between gap-4 text-sm">
              <span className="text-gray-500">کد پیگیری</span>
              <span className="font-medium text-gray-900">
                {payment.provider_reference}
              </span>
            </div>
          )}
        </div>

        {isReviewRequired && payment?.review_reason && (
          <p className="mt-4 rounded-lg bg-amber-50 p-3 text-sm leading-7 text-amber-800">
            علت نیاز به بررسی: {payment.review_reason}
          </p>
        )}

        {!isFinal && (
          <div className="mt-5 flex items-center justify-center gap-2 text-xs text-gray-500">
            <span className="h-2 w-2 animate-pulse rounded-full bg-blue-500" />

            {isFetching
              ? "در حال به‌روزرسانی وضعیت..."
              : "وضعیت پرداخت به‌صورت خودکار بررسی می‌شود."}
          </div>
        )}

        <div className="mt-7 flex flex-col gap-3 sm:flex-row">
          {!isFinal && (
            <button
              type="button"
              onClick={() => void refetch()}
              className="flex-1 rounded-lg border border-gray-300 px-5 py-3 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
            >
              بررسی مجدد وضعیت
            </button>
          )}

          {canRetry && (
            <Link
              href="/checkout"
              className="flex-1 rounded-lg bg-pink-600 px-5 py-3 text-center text-sm font-medium text-white transition hover:bg-pink-700"
            >
              تلاش مجدد برای پرداخت
            </Link>
          )}

          <Link
            href={isSuccess ? "/orders" : "/"}
            className="flex-1 rounded-lg bg-gray-900 px-5 py-3 text-center text-sm font-medium text-white transition hover:bg-gray-700"
          >
            {isSuccess ? "مشاهده سفارش‌ها" : "بازگشت به فروشگاه"}
          </Link>
        </div>
      </section>
    </main>
  );
}

export default function PaymentResultPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[70vh] items-center justify-center">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-gray-200 border-t-gray-900" />
        </div>
      }
    >
      <PaymentResultContent />
    </Suspense>
  );
}
