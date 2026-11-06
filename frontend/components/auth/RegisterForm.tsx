"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { useRegisterMutation } from "@/lib/redux/services/authApi";

import {
  registerSchema,
  type RegisterFormValues,
} from "@/lib/redux/features/auth/authValidation";

import { getApiErrorMessage } from "./apiError";

export default function RegisterForm() {
  const router = useRouter();

  const [registerUser, { isLoading }] = useRegisterMutation();
  const [serverError, setServerError] = useState("");

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      email: "",
      password: "",
      password_confirm: "",
    },
  });

  const onSubmit = async (values: RegisterFormValues) => {
    setServerError("");

    try {
      const result = await registerUser(values).unwrap();

      router.push(
        `/verify-email?email=${encodeURIComponent(result.email)}`
      );
    } catch (error) {
      setServerError(getApiErrorMessage(error));
    }
  };

  return (
    <div className="w-full max-w-md rounded-2xl border border-gray-200 bg-white p-8 shadow-sm">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold text-gray-900">
          ایجاد حساب کاربری
        </h1>
        <p className="mt-2 text-sm text-gray-500">
          برای عضویت در GlowCart اطلاعات خود را وارد کنید.
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
          <label htmlFor="password" className="mb-2 block text-sm font-medium">
            رمز عبور
          </label>

          <input
            id="password"
            type="password"
            autoComplete="new-password"
            {...register("password")}
            className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-pink-500"
            placeholder="حداقل ۸ کاراکتر"
          />

          {errors.password && (
            <p className="mt-1 text-sm text-red-600">
              {errors.password.message}
            </p>
          )}
        </div>

        <div>
          <label
            htmlFor="password_confirm"
            className="mb-2 block text-sm font-medium"
          >
            تکرار رمز عبور
          </label>

          <input
            id="password_confirm"
            type="password"
            autoComplete="new-password"
            {...register("password_confirm")}
            className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-pink-500"
            placeholder="رمز عبور را دوباره وارد کنید"
          />

          {errors.password_confirm && (
            <p className="mt-1 text-sm text-red-600">
              {errors.password_confirm.message}
            </p>
          )}
        </div>

        {serverError && (
          <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
            {serverError}
          </p>
        )}

        <button
          type="submit"
          disabled={isLoading}
          className="w-full rounded-lg bg-pink-600 px-4 py-3 font-semibold text-white transition hover:bg-pink-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isLoading ? "در حال ثبت‌نام..." : "ثبت‌نام"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-gray-600">
        قبلاً ثبت‌نام کرده‌اید؟{" "}
        <Link href="/login" className="font-semibold text-pink-600">
          وارد شوید
        </Link>
      </p>
    </div>
  );
}