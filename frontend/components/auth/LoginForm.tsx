"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { useAppDispatch } from "@/lib/redux/hooks";
import { useLoginMutation } from "@/lib/redux/services/authApi";

import { setCredentials } from "@/lib/redux/features/auth/authSlice";
import { authStorage } from "@/lib/redux/features/auth/authStorage";

import {
  loginSchema,
  type LoginFormValues,
} from "@/lib/redux/features/auth/authValidation";

import { getApiErrorMessage } from "./apiError";

export default function LoginForm() {
  const router = useRouter();
  const dispatch = useAppDispatch();

  const [login, { isLoading }] = useLoginMutation();
  const [serverError, setServerError] = useState("");

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  const onSubmit = async (values: LoginFormValues) => {
    setServerError("");

    try {
      const result = await login(values).unwrap();

      authStorage.setRefreshToken(result.refresh);

      dispatch(
        setCredentials({
          user: result.user,
          access: result.access,
        })
      );

      router.replace("/");
    } catch (error) {
      setServerError(getApiErrorMessage(error));
    }
  };

  return (
    <div className="w-full max-w-md rounded-2xl border border-gray-200 bg-white p-8 shadow-sm">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold text-gray-900">ورود به GlowCart</h1>
        <p className="mt-2 text-sm text-gray-500">
          برای ادامه وارد حساب کاربری خود شوید.
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
            autoComplete="current-password"
            {...register("password")}
            className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-pink-500"
            placeholder="رمز عبور"
          />

          {errors.password && (
            <p className="mt-1 text-sm text-red-600">
              {errors.password.message}
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
          {isLoading ? "در حال ورود..." : "ورود"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-gray-600">
        حساب کاربری ندارید؟{" "}
        <Link href="/register" className="font-semibold text-pink-600">
          ثبت‌نام کنید
        </Link>
      </p>
    </div>
  );
}