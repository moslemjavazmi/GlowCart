
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import {
  resetPasswordSchema,
  type ResetPasswordFormValues,
} from "@/lib/redux/features/auth/authValidation";

import { useResetPasswordMutation } from "@/lib/redux/services/authApi";
import { getApiErrorMessage } from "@/components/auth/apiError";

import { useAppDispatch } from "@/lib/redux/hooks";
import { clearCredentials } from "@/lib/redux/features/auth/authSlice";
import { authStorage } from "@/lib/redux/features/auth/authStorage";
import { baseApi } from "@/lib/redux/services/baseApi";

export default function ResetPasswordForm() {
  const router = useRouter();
  const dispatch = useAppDispatch();

  const [uid, setUid] = useState("");
  const [token, setToken] = useState("");
  const [linkError, setLinkError] = useState("");
  const [apiError, setApiError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const [resetPassword, { isLoading }] =
    useResetPasswordMutation();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetPasswordFormValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: {
      new_password: "",
      password_confirm: "",
    },
  });

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);

    const queryUid = params.get("uid");
    const queryToken = params.get("token");

    if (!queryUid || !queryToken) {
      setLinkError("لینک بازیابی ناقص یا نامعتبر است.");
      return;
    }

    setUid(queryUid);
    setToken(queryToken);
  }, []);

  const onSubmit = async (values: ResetPasswordFormValues) => {
    setApiError("");
    setSuccessMessage("");

    if (!uid || !token) {
      setLinkError("اطلاعات لینک بازیابی در دسترس نیست.");
      return;
    }

    try {
      const response = await resetPassword({
        uid,
        token,
        new_password: values.new_password,
        password_confirm: values.password_confirm,
      }).unwrap();

      setSuccessMessage(response.message);

      // حذف Refresh Token و اطلاعات نشست قبلی
      authStorage.clearRefreshToken();
      dispatch(clearCredentials());
      dispatch(baseApi.util.resetApiState());

      router.replace("/login?passwordReset=1");
    } catch (error) {
      setApiError(getApiErrorMessage(error));
    }
  };

  if (linkError) {
    return (
      <div className="mx-auto w-full max-w-md">
        <h1 className="mb-3 text-2xl font-bold">
          لینک بازیابی نامعتبر است
        </h1>
        <p className="text-sm text-red-600">{linkError}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-md">
      <h1 className="mb-2 text-2xl font-bold">
        تعیین رمز عبور جدید
      </h1>

      <p className="mb-6 text-sm text-gray-600">
        رمز عبور جدید خود را وارد کنید.
      </p>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label
            htmlFor="new_password"
            className="mb-1 block text-sm"
          >
            رمز عبور جدید
          </label>

          <input
            id="new_password"
            type="password"
            autoComplete="new-password"
            {...register("new_password")}
            className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-black"
          />

          {errors.new_password && (
            <p className="mt-1 text-sm text-red-600">
              {errors.new_password.message}
            </p>
          )}
        </div>

        <div>
          <label
            htmlFor="password_confirm"
            className="mb-1 block text-sm"
          >
            تکرار رمز عبور جدید
          </label>

          <input
            id="password_confirm"
            type="password"
            autoComplete="new-password"
            {...register("password_confirm")}
            className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-black"
          />

          {errors.password_confirm && (
            <p className="mt-1 text-sm text-red-600">
              {errors.password_confirm.message}
            </p>
          )}
        </div>

        {apiError && (
          <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
            {apiError}
          </p>
        )}

        {successMessage && (
          <p className="rounded-lg bg-green-50 p-3 text-sm text-green-700">
            {successMessage}
          </p>
        )}

        <button
          type="submit"
          disabled={isLoading || !uid || !token}
          className="w-full rounded-lg bg-black px-4 py-3 text-white disabled:opacity-50"
        >
          {isLoading ? "در حال تغییر رمز..." : "ثبت رمز عبور جدید"}
        </button>
      </form>
    </div>
  );
}
