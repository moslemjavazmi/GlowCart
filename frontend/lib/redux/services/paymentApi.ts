import { baseApi } from "./baseApi";

import type {
  InitializePaymentRequest,
  InitializePaymentResponse,
  PaymentDetail,
} from "../features/payments/paymentTypes";

export const paymentApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    initializePayment: builder.mutation<
      InitializePaymentResponse,
      InitializePaymentRequest
    >({
      query: (body) => ({
        url: "/payments/initialize/",
        method: "POST",
        body,
      }),

      invalidatesTags: (_result, _error, arg) => [
        { type: "Payment", id: "LIST" },
        { type: "Order", id: arg.order_id },
      ],
    }),

    getPayment: builder.query<PaymentDetail, string>({
      query: (paymentId) => ({
        url: `/payments/${paymentId}/`,
        method: "GET",
      }),

      providesTags: (_result, _error, paymentId) => [
        { type: "Payment", id: paymentId },
      ],
    }),
  }),

  overrideExisting: false,
});

export const {
  useInitializePaymentMutation,
  useGetPaymentQuery,
} = paymentApi;