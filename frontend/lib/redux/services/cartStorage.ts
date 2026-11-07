const GUEST_CART_TOKEN_KEY = "glowcart_guest_cart_token";

export const cartStorage = {
  getGuestToken(): string | null {
    if (typeof window === "undefined") {
      return null;
    }

    return localStorage.getItem(GUEST_CART_TOKEN_KEY);
  },

  setGuestToken(token: string): void {
    if (typeof window === "undefined") {
      return;
    }

    localStorage.setItem(GUEST_CART_TOKEN_KEY, token);
  },

  clearGuestToken(): void {
    if (typeof window === "undefined") {
      return;
    }

    localStorage.removeItem(GUEST_CART_TOKEN_KEY);
  },
};