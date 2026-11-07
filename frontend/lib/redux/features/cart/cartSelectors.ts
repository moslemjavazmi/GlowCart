import { createSelector } from "@reduxjs/toolkit";

import type { RootState } from "../../store";
import { cartApi } from "../../services/cartApi";

const selectCartQuery = cartApi.endpoints.getCart.select();

export const selectCart = createSelector(
  [selectCartQuery],
  (result) => result.data
);

export const selectCartItems = createSelector(
  [selectCart],
  (cart) => cart?.items ?? []
);

export const selectCartTotalItems = createSelector(
  [selectCart],
  (cart) => cart?.total_items ?? 0
);

export const selectCartSubtotal = createSelector(
  [selectCart],
  (cart) => cart?.subtotal ?? "0"
);

export const selectGuestCartToken = (state: RootState) =>
  state.cart.guestToken;