
"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { useForgotPasswordMutation } from "@/lib/redux/services/authApi";
import {
  forgotPasswordSchema,
  type ForgotPasswordFormValues,
} from "@/lib/redux/features/auth/authValidation";
import { getApiErrorMessage } from "@/components/auth/apiError";

export default function ForgotPasswordForm() {
  const [successMessage, setSuccessMessage] = useState("");
    const [apiError, setApiError] = useState("");
  const [forgotPassword, { isLoading }] =
    useForgotPasswordMutation();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordFormValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: {
      email: "",
    },
  });

  const onSubmit = async (values: ForgotPasswordFormValues) => {
    setSuccessMessage("");
    setApiError("");

    try {
      const response = await forgotPassword({
        email: values.email.trim().toLowerCase(),
      }).unwrap();

      setSuccessMessage(response.message);
    } catch (error) {
      setSuccessMessage("");
       setApiError(getApiErrorMessage(error));
      console.error(getApiErrorMessage(error));
    }
  };

  return (
    <div className="mx-auto w-full max-w-md">
      <h1 className="mb-2 text-2xl font-bold">
        بازیابی رمز عبور
      </h1>

      <p className="mb-6 text-sm text-gray-600">
        ایمیل حساب کاربری خود را وارد کنید تا لینک بازیابی
        رمز عبور برای شما ارسال شود.
      </p>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label htmlFor="email" className="mb-1 block text-sm">
            ایمیل
          </label>

          <input
            id="email"
            type="email"
            autoComplete="email"
            {...register("email")}
            className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-black"
            placeholder="example@email.com"
          />

          {errors.email && (
            <p className="mt-1 text-sm text-red-600">
              {errors.email.message}
            </p>
          )}
        </div>

        {successMessage && (
          <p className="rounded-lg bg-green-50 p-3 text-sm text-green-700">
            {successMessage}
          </p>
        )}
        {apiError && (
            <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
                {apiError}
            </p>
        )}
        <button
          type="submit"
          disabled={isLoading}
          className="w-full rounded-lg bg-black px-4 py-3 text-white disabled:opacity-50"
        >
          {isLoading ? "در حال ارسال..." : "ارسال لینک بازیابی"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm">
        رمز عبورت را به خاطر آوردی؟{" "}
        <Link href="/login" className="font-semibold underline">
          ورود
        </Link>
      </p>
    </div>
  );
}
