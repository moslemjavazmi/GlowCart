"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import {
  useVerifyEmailMutation,
  useResendVerificationMutation,
} from "@/lib/redux/services/authApi";

import {
  verifyEmailSchema,
  type VerifyEmailFormValues,
} from "@/lib/redux/features/auth/authValidation";

import { getApiErrorMessage } from "./apiError";

export default function VerifyEmailForm() {
  const router = useRouter();

  const [verifyEmail, { isLoading: isVerifying }] =
    useVerifyEmailMutation();

  const [resendVerification, { isLoading: isResending }] =
    useResendVerificationMutation();

  const [serverError, setServerError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<VerifyEmailFormValues>({
    resolver: zodResolver(verifyEmailSchema),
    defaultValues: {
      email: "",
      code: "",
    },
  });

  const email = watch("email");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const emailFromUrl = params.get("email");

    if (emailFromUrl) {
      setValue("email", emailFromUrl);
    }
  }, [setValue]);

  const onSubmit = async (values: VerifyEmailFormValues) => {
    setServerError("");
    setSuccessMessage("");

    try {
      await verifyEmail(values).unwrap();

      setSuccessMessage("ایمیل شما با موفقیت تأیید شد.");

      setTimeout(() => {
        router.replace("/login?verified=1");
      }, 1200);
    } catch (error) {
      setServerError(getApiErrorMessage(error));
    }
  };

  const handleResend = async () => {
    if (!email) {
      setServerError("ابتدا ایمیل خود را وارد کنید.");
      return;
    }

    setServerError("");
    setSuccessMessage("");

    try {
      const result = await resendVerification({ email }).unwrap();
      setSuccessMessage(
        result.message || "کد تأیید جدید ارسال شد."
      );
    } catch (error) {
      setServerError(getApiErrorMessage(error));
    }
  };

  return (
    <div className="w-full max-w-md rounded-2xl border border-gray-200 bg-white p-8 shadow-sm">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold text-gray-900">
          تأیید ایمیل
        </h1>

        <p className="mt-2 text-sm text-gray-500">
          کد ۶ رقمی ارسال‌شده به ایمیل خود را وارد کنید.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        <div>
          <label htmlFor="email" className="mb-2 block text-sm font-medium">
            ایمیل
          </label>

          <input
            id="email"
            type="email"
            autoComplete="email"
            {...register("email")}
            className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-pink-500"
            placeholder="example@email.com"
          />

          {errors.email && (
            <p className="mt-1 text-sm text-red-600">
              {errors.email.message}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="code" className="mb-2 block text-sm font-medium">
            کد تأیید
          </label>

          <input
            id="code"
            type="text"
            inputMode="numeric"
            maxLength={6}
            autoComplete="one-time-code"
            {...register("code")}
            className="w-full rounded-lg border border-gray-300 px-4 py-3 text-center tracking-[0.5em] outline-none focus:border-pink-500"
            placeholder="------"
          />

          {errors.code && (
            <p className="mt-1 text-sm text-red-600">
              {errors.code.message}
            </p>
          )}
        </div>

        {serverError && (
          <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
            {serverError}
          </p>
        )}

        {successMessage && (
          <p className="rounded-lg bg-green-50 p-3 text-sm text-green-700">
            {successMessage}
          </p>
        )}

        <button
          type="submit"
          disabled={isVerifying}
          className="w-full rounded-lg bg-pink-600 px-4 py-3 font-semibold text-white transition hover:bg-pink-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isVerifying ? "در حال تأیید..." : "تأیید ایمیل"}
        </button>
      </form>

      <button
        type="button"
        onClick={handleResend}
        disabled={isResending || !email}
        className="mt-4 w-full rounded-lg border border-pink-200 px-4 py-3 text-sm font-semibold text-pink-700 transition hover:bg-pink-50 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isResending ? "در حال ارسال..." : "ارسال مجدد کد"}
      </button>

      <p className="mt-6 text-center text-sm text-gray-600">
        <Link href="/login" className="font-semibold text-pink-600">
          بازگشت به صفحه ورود
        </Link>
      </p>
    </div>
  );
}