import { baseApi } from "./baseApi";

import { cartStorage } from "./cartStorage";

import {
  setGuestToken,
  clearGuestToken,
} from "../features/cart/cartSlice";

import type {
  Cart,
  AddCartItemRequest,
  UpdateCartItemRequest,
  MergeGuestCartRequest,
} from "../features/cart/cartTypes";

import type { AppDispatch } from "../store";

function syncGuestToken(
  data: Cart,
  dispatch: AppDispatch
): void {
  if (!data.guest_token) return;

  cartStorage.setGuestToken(data.guest_token);
  dispatch(setGuestToken(data.guest_token));
}

export const cartApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    // GET /cart/
    getCart: builder.query<Cart, void>({
      query: () => ({
        url: "/cart/",
        method: "GET",
      }),

      providesTags: ["Cart"],

      async onQueryStarted(_, { dispatch, queryFulfilled }) {
        try {
          const { data } = await queryFulfilled;

          await syncGuestToken(data, dispatch);
        } catch {
          // خطا توسط RTK Query مدیریت می‌شود.
        }
      },
    }),

    // POST /cart/items/
    addCartItem: builder.mutation<Cart, AddCartItemRequest>({
      query: (body) => ({
        url: "/cart/items/",
        method: "POST",
        body,
      }),

      invalidatesTags: ["Cart"],

      async onQueryStarted(_, { dispatch, queryFulfilled }) {
        try {
          const { data } = await queryFulfilled;

          await syncGuestToken(data, dispatch);
        } catch {
          // خطا توسط RTK Query مدیریت می‌شود.
        }
      },
    }),

    // PATCH /cart/items/:itemId/
    updateCartItem: builder.mutation<Cart, UpdateCartItemRequest>({
      query: ({ itemId, quantity }) => ({
        url: `/cart/items/${itemId}/`,
        method: "PATCH",
        body: { quantity },
      }),

      invalidatesTags: ["Cart"],
    }),

    // DELETE /cart/items/:itemId/remove/
    removeCartItem: builder.mutation<Cart, string>({
      query: (itemId) => ({
        url: `/cart/items/${itemId}/remove/`,
        method: "DELETE",
      }),

      invalidatesTags: ["Cart"],
    }),

    // DELETE /cart/clear/
    clearCart: builder.mutation<Cart, void>({
      query: () => ({
        url: "/cart/clear/",
        method: "DELETE",
      }),

      invalidatesTags: ["Cart"],
    }),

    // POST /cart/merge/
    mergeGuestCart: builder.mutation<Cart, MergeGuestCartRequest>({
      query: (body) => ({
        url: "/cart/merge/",
        method: "POST",
        body,
      }),

      invalidatesTags: ["Cart"],

      async onQueryStarted(_, { dispatch, queryFulfilled }) {
          try {
            await queryFulfilled;

            cartStorage.clearGuestToken();
            dispatch(clearGuestToken());
        } catch {
          // در صورت شکست Merge، Guest Token را حفظ می‌کنیم.
        }
      },
    }),
  }),
});

export const {
  useGetCartQuery,
  useAddCartItemMutation,
  useUpdateCartItemMutation,
  useRemoveCartItemMutation,
  useClearCartMutation,
  useMergeGuestCartMutation,
} = cartApi;