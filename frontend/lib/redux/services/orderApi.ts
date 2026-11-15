import { baseApi } from "./baseApi";

import type {
  Order,
  CreateOrderRequest,
  CancelOrderResponse,
} from "../features/orders/orderTypes";

interface PaginatedOrdersResponse {
  count?: number;
  next?: string | null;
  previous?: string | null;
  results: Order[];
}

export const orderApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    // --------------------------------------------------
    // Create order
    // --------------------------------------------------

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

    // --------------------------------------------------
    // Get all orders
    // --------------------------------------------------

    getOrders: builder.query<Order[], void>({
      query: () => ({
        url: "/orders/",
        method: "GET",
      }),

      transformResponse: (
        response: Order[] | PaginatedOrdersResponse
      ): Order[] => {
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
          : [
              { type: "Order" as const, id: "LIST" },
            ],
    }),

    // --------------------------------------------------
    // Get single order
    // --------------------------------------------------

    getOrder: builder.query<Order, string>({
      query: (id) => ({
        url: `/orders/${id}/`,
        method: "GET",
      }),

      providesTags: (_result, _error, id) => [
        { type: "Order", id },
      ],
    }),

    // --------------------------------------------------
    // Cancel order
    // --------------------------------------------------

    cancelOrder: builder.mutation<
      CancelOrderResponse,
      string
    >({
      query: (orderId) => ({
        url: `/orders/${orderId}/cancel/`,
        method: "POST",
      }),

      invalidatesTags: (_result, _error, id) => [
        { type: "Order", id },
        { type: "Order", id: "LIST" },
        "Cart",
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