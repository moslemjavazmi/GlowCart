
"use client";

import { useEffect, useRef } from "react";

import { useAppDispatch, useAppSelector } from "@/lib/redux/hooks";

import { setGuestToken } from "@/lib/redux/features/cart/cartSlice";

import { cartStorage } from "@/lib/redux/services/cartStorage";

import {
  useGetCartQuery,
  useMergeGuestCartMutation,
} from "@/lib/redux/services/cartApi";

export default function CartInitializer() {
  const dispatch = useAppDispatch();

  const isAuthenticated = useAppSelector(
    (state) => state.auth.isAuthenticated
  );

  const guestToken = useAppSelector(
    (state) => state.cart.guestToken
  );

  const attemptedTokenRef = useRef<string | null>(null);

  const { isLoading, error } = useGetCartQuery();

  const [mergeGuestCart, { isLoading: isMerging }] =
    useMergeGuestCartMutation();

  // Restore guest token from localStorage on application startup.
  useEffect(() => {
    const token = cartStorage.getGuestToken();

    if (token) {
      dispatch(setGuestToken(token));
    }
  }, [dispatch]);

  // Automatically merge guest cart after authentication.
  useEffect(() => {
    if (!isAuthenticated || !guestToken || isMerging) {
      return;
    }

    // Prevent repeated attempts for the same token.
    if (attemptedTokenRef.current === guestToken) {
      return;
    }

    attemptedTokenRef.current = guestToken;

    const merge = async () => {
      try {
        await mergeGuestCart({
          guest_token: guestToken,
        }).unwrap();

        console.info("[CartInitializer] Guest cart merged successfully");
      } catch (error) {
        // Keep the token so the cart can be merged in a later attempt.
        console.error(
          "[CartInitializer] Guest cart merge failed:",
          error
        );
      }
    };

    void merge();
  }, [
    isAuthenticated,
    guestToken,
    isMerging,
    mergeGuestCart,
  ]);

  if (error) {
    console.error("[CartInitializer] Cart request failed:", error);
  }

  if (isLoading) {
    console.log("[CartInitializer] Loading cart...");
  }

  return null;
}
