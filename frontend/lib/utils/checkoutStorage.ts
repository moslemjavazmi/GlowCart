
import type { Cart } from "@/lib/redux/features/cart/cartTypes";

const STORAGE_KEY = "glowcart_checkout_v1";

export interface CheckoutSession {
  orderIdempotencyKey: string;
  orderId: string | null;
  paymentIdempotencyKey: string;
  paymentId: string | null;
  cartSnapshot: Cart | null;
}

function isBrowser() {
  return typeof window !== "undefined";
}

export function createCheckoutSession(): CheckoutSession {
  return {
    orderIdempotencyKey: crypto.randomUUID(),
    orderId: null,
    paymentIdempotencyKey: crypto.randomUUID(),
    paymentId: null,
    cartSnapshot: null,
  };
}

export function getCheckoutSession(): CheckoutSession | null {
  if (!isBrowser()) return null;

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;

    const parsed = JSON.parse(raw) as CheckoutSession;

    if (
      !parsed.orderIdempotencyKey ||
      !parsed.paymentIdempotencyKey
    ) {
      return null;
    }

    return parsed;
  } catch {
    return null;
  }
}

export function saveCheckoutSession(
  session: CheckoutSession
): void {
  if (!isBrowser()) return;

  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify(session)
  );
}

export function clearCheckoutSession(): void {
  if (!isBrowser()) return;

  localStorage.removeItem(STORAGE_KEY);
}
