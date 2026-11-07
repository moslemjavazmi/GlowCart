import {
  createApi,
  fetchBaseQuery,
  type BaseQueryFn,
  type FetchArgs,
  type FetchBaseQueryError,
} from "@reduxjs/toolkit/query/react";

import { Mutex } from "async-mutex";

import type { RootState } from "../store";
import {
  clearCredentials,
  setAccessToken,
} from "../features/auth/authSlice";
import { authStorage } from "../features/auth/authStorage";
import { cartStorage } from "./cartStorage";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

const rawBaseQuery = fetchBaseQuery({
  baseUrl: API_BASE_URL,

  prepareHeaders: (headers, { getState }) => {
    const token = (getState() as RootState).auth.accessToken;

    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    const guestCartToken = cartStorage.getGuestToken();

    if (guestCartToken) {
      headers.set("X-Guest-Cart-Token", guestCartToken);
    }

    headers.set("Accept", "application/json");

    return headers;
  },
});

const mutex = new Mutex();

const baseQueryWithReauth: BaseQueryFn<
  string | FetchArgs,
  unknown,
  FetchBaseQueryError
> = async (args, api, extraOptions) => {
  // اگر درخواست دیگری در حال Refresh است، منتظر پایان آن می‌مانیم.
  await mutex.waitForUnlock();

  let result = await rawBaseQuery(args, api, extraOptions);

  if (result.error?.status !== 401) {
    return result;
  }

  // خود درخواست Refresh نباید دوباره وارد چرخه Refresh شود.
  const requestUrl = typeof args === "string" ? args : args.url;

  if (requestUrl.includes("/auth/refresh/")) {
    authStorage.clearRefreshToken();
    api.dispatch(clearCredentials());
    return result;
  }

  // اگر درخواست دیگری در حال Refresh نیست، این درخواست مسئول Refresh می‌شود.
  if (!mutex.isLocked()) {
    const release = await mutex.acquire();

    try {
      const refreshToken = authStorage.getRefreshToken();

      if (!refreshToken) {
        authStorage.clearRefreshToken();
        api.dispatch(clearCredentials());
        return result;
      }

      const refreshResult = await rawBaseQuery(
        {
          url: "/auth/refresh/",
          method: "POST",
          body: { refresh: refreshToken },
        },
        api,
        extraOptions
      );

      if (refreshResult.data) {
        const data = refreshResult.data as {
          access: string;
          refresh?: string;
        };

        api.dispatch(setAccessToken(data.access));

        // در صورت فعال بودن Refresh Token Rotation،
        // توکن جدید را ذخیره می‌کنیم.
        if (data.refresh) {
          authStorage.setRefreshToken(data.refresh);
        }

        // درخواست اولیه را با Access Token جدید تکرار می‌کنیم.
        result = await rawBaseQuery(args, api, extraOptions);
      } else {
        authStorage.clearRefreshToken();
        api.dispatch(clearCredentials());
      }
    } finally {
      release();
    }
  } else {
    // درخواست دیگری Refresh را انجام داده؛ پس از پایان آن،
    // درخواست فعلی را با توکن جدید تکرار می‌کنیم.
    await mutex.waitForUnlock();

    const newAccessToken = (api.getState() as RootState).auth.accessToken;

    if (newAccessToken) {
      result = await rawBaseQuery(args, api, extraOptions);
    } else {
      authStorage.clearRefreshToken();
      api.dispatch(clearCredentials());
    }
  }

  return result;
};

export const baseApi = createApi({
  reducerPath: "api",
  baseQuery: baseQueryWithReauth,

  tagTypes: [
    "User",
    "Product",
    "Category",
    "Cart",
    "Order",
    "Address",
    "Wishlist",
    "Payment",
    "Coupon",
  ],

  endpoints: () => ({}),
});