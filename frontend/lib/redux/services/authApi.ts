import { baseApi } from "./baseApi";

import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  VerifyEmailRequest,
  RefreshResponse,
  ForgotPasswordRequest,
  ResetPasswordRequest,
  AuthMessageResponse,
} from "../features/auth/authTypes";

export const authApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    register: builder.mutation<
      RegisterResponse,
      RegisterRequest
    >({
      query: (body) => ({
        url: "/auth/register/",
        method: "POST",
        body,
      }),
    }),

    verifyEmail: builder.mutation<
      { message: string },
      VerifyEmailRequest
    >({
      query: (body) => ({
        url: "/auth/verify-email/",
        method: "POST",
        body,
      }),
    }),

    resendVerification: builder.mutation<
      { message: string },
      { email: string }
    >({
      query: (body) => ({
        url: "/auth/resend-verification/",
        method: "POST",
        body,
      }),
    }),

    login: builder.mutation<LoginResponse, LoginRequest>({
      query: (body) => ({
        url: "/auth/login/",
        method: "POST",
        body,
      }),
    }),

    refreshToken: builder.mutation<
      RefreshResponse,
      { refresh: string }
    >({
      query: (body) => ({
        url: "/auth/refresh/",
        method: "POST",
        body,
      }),
    }),

    logout: builder.mutation<
      { message: string },
      { refresh: string }
    >({
      query: (body) => ({
        url: "/auth/logout/",
        method: "POST",
        body,
      }),
    }),

    getMe: builder.query<LoginResponse["user"], void>({
      query: () => ({
        url: "/auth/me/",
        method: "GET",
      }),
      providesTags: ["User"],
    }),
    forgotPassword: builder.mutation<
      AuthMessageResponse,
      ForgotPasswordRequest
    >({
      query: (body) => ({
        url: "/auth/forgot-password/",
        method: "POST",
        body,
      }),
    }),

    resetPassword: builder.mutation<
      AuthMessageResponse,
      ResetPasswordRequest
    >({
      query: (body) => ({
        url: "/auth/reset-password/",
        method: "POST",
        body,
      }),
    }),
  }),
});

export const {
  useRegisterMutation,
  useVerifyEmailMutation,
  useResendVerificationMutation,
  useLoginMutation,
  useRefreshTokenMutation,
  useLogoutMutation,
  useGetMeQuery,
  useForgotPasswordMutation,
  useResetPasswordMutation,
} = authApi;