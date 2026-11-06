"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAppDispatch } from "@/lib/redux/hooks";

import { clearCredentials } from "@/lib/redux/features/auth/authSlice";
import { authStorage } from "@/lib/redux/features/auth/authStorage";

import { useLogoutMutation } from "@/lib/redux/services/authApi";
import { baseApi } from "@/lib/redux/services/baseApi";

export default function LogoutButton() {
  const router = useRouter();
  const dispatch = useAppDispatch();

  const [logout, { isLoading }] = useLogoutMutation();
  const [error, setError] = useState("");

  const handleLogout = async () => {
    setError("");

    const refreshToken = authStorage.getRefreshToken();

    try {
      if (refreshToken) {
        await logout({ refresh: refreshToken }).unwrap();
      }
    } catch {
      setError("ارتباط با سرور برای خروج برقرار نشد؛ نشست محلی پاک شد.");
    } finally {
      authStorage.clearRefreshToken();

      dispatch(clearCredentials());

      dispatch(baseApi.util.resetApiState());

      router.replace("/login");
    }
  };

  return (
    <div>
      <button
        type="button"
        onClick={handleLogout}
        disabled={isLoading}
        className="rounded-lg bg-red-600 px-5 py-3 font-semibold text-white transition hover:bg-red-700 disabled:opacity-50"
      >
        {isLoading ? "در حال خروج..." : "خروج از حساب"}
      </button>

      {error && (
        <p className="mt-3 text-sm text-red-600">{error}</p>
      )}
    </div>
  );
}