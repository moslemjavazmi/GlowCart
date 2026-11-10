
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

// ذخیره و همگام‌سازی Guest Token
function syncGuestToken(
  data: Cart,
  dispatch: AppDispatch
): void {
  console.log("[Cart] syncGuestToken executed");
  console.log("[Cart] Received cart:", data);

  const guestToken = data?.guest_token;

  console.log("[Cart] Guest token:", guestToken);

  if (!guestToken) {
    console.warn("[Cart] Response does not contain guest_token");
    return;
  }

  try {
    cartStorage.setGuestToken(guestToken);
    dispatch(setGuestToken(guestToken));

    console.log(
      "[Cart] Token saved successfully:",
      cartStorage.getGuestToken()
    );
  } catch (error) {
    console.error("[Cart] Failed to save guest token:", error);
  }
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
        console.log("[Cart] getCart started");

        try {
          const { data } = await queryFulfilled;

          console.log("[Cart] getCart fulfilled:", data);

          syncGuestToken(data, dispatch);
        } catch (error) {
          console.error("[Cart] getCart failed:", error);
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
          syncGuestToken(data, dispatch);
        } catch (error) {
          console.error("[Cart] addCartItem failed:", error);
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

          console.log("[Cart] Guest cart merged successfully");
        } catch (error) {
          console.error("[Cart] Guest cart merge failed:", error);
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
