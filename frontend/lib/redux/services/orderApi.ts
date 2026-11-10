import { baseApi } from "./baseApi";

import type {
  Order,
  CreateOrderRequest,
} from "../features/orders/orderTypes";

export const orderApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    createOrder: builder.mutation<Order, CreateOrderRequest>({
      query: (body) => ({
        url: "/orders/create/",
        method: "POST",
        body,
      }),

    invalidatesTags: [
    { type: "Order", id: "LIST" },
    "Cart",
    ],
    }),

    getOrders: builder.query<Order[], void>({
      query: () => ({
        url: "/orders/",
        method: "GET",
      }),

      transformResponse: (
        response: Order[] | { results: Order[] }
      ) => {
        return Array.isArray(response)
          ? response
          : response.results;
      },

      providesTags: (result) =>
        result
          ? [
              ...result.map(({ id }) => ({
                type: "Order" as const,
                id,
              })),
              { type: "Order" as const, id: "LIST" },
            ]
          : [{ type: "Order" as const, id: "LIST" }],
    }),

    getOrder: builder.query<Order, string>({
      query: (id) => ({
        url: `/orders/${id}/`,
        method: "GET",
      }),

      providesTags: (_result, _error, id) => [
        { type: "Order", id },
      ],
    }),

    cancelOrder: builder.mutation<
      Order,
      string
    >({
      query: (orderId) => ({
        url: `/orders/${orderId}/cancel/`,
        method: "POST",
      }),

      invalidatesTags: (_result, _error, id) => [
        { type: "Order", id },
        { type: "Order", id: "LIST" },
      ],
    }),
  }),

  overrideExisting: false,
});

export const {
  useCreateOrderMutation,
  useGetOrdersQuery,
  useGetOrderQuery,
  useCancelOrderMutation,
} = orderApi;