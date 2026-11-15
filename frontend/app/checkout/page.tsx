
"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { useAppSelector } from "@/lib/redux/hooks";

import { useGetCartQuery } from "@/lib/redux/services/cartApi";

import {
  useGetAddressesQuery,
  useCreateAddressMutation,
  useUpdateAddressMutation,
  useDeleteAddressMutation,
} from "@/lib/redux/services/addressApi";

import {
  useInitializePaymentMutation,
  useGetPaymentQuery,
} from "@/lib/redux/services/paymentApi";

import {
  useCreateOrderMutation,
  useGetOrderQuery,
} from "@/lib/redux/services/orderApi";

import type { Cart } from "@/lib/redux/features/cart/cartTypes";

import type {
  Address,
  AddressPayload,
} from "@/lib/redux/features/addresses/addressTypes";

import type { Order } from "@/lib/redux/features/orders/orderTypes";

import {
  createCheckoutSession,
  getCheckoutSession,
  saveCheckoutSession,
  clearCheckoutSession,
  type CheckoutSession,
} from "@/lib/utils/checkoutStorage";
import {
  selectIsAuthenticated,
  selectIsAuthInitialized,
} from "@/lib/redux/features/auth/authSelectors";

import AddressForm from "@/components/checkout/AddressForm";
import AddressSelector from "@/components/checkout/AddressSelector";
import CheckoutSummary from "@/components/checkout/CheckoutSummary";

// --------------------------------------------------
// Error helper
// --------------------------------------------------

function getErrorMessage(error: unknown): string {
  const apiError = error as {
    data?: {
      detail?: string;
      error?: string;
      [key: string]: unknown;
    };
    message?: string;
  };

  const data = apiError.data;

  if (typeof data?.detail === "string") {
    return data.detail;
  }

  if (typeof data?.error === "string") {
    return data.error;
  }

  if (data) {
    const firstFieldError = Object.values(data).find(
      (value) =>
        Array.isArray(value) &&
        typeof value[0] === "string"
    );

    if (
      Array.isArray(firstFieldError) &&
      typeof firstFieldError[0] === "string"
    ) {
      return firstFieldError[0];
    }
  }

  return (
    apiError.message ||
    "عملیات انجام نشد. لطفاً دوباره تلاش کنید."
  );
}

// ==================================================
// Checkout page
// ==================================================

export default function CheckoutPage() {
  const router = useRouter();

  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const isAuthInitialized = useAppSelector(selectIsAuthInitialized);

  // --------------------------------------------------
  // Local state
  // --------------------------------------------------

  const [selectedAddressId, setSelectedAddressId] =
    useState<string | null>(null);

  const [showAddressForm, setShowAddressForm] =
    useState(false);

  const [editingAddress, setEditingAddress] =
    useState<Address | null>(null);

  const [couponCode, setCouponCode] = useState("");

  const [message, setMessage] = useState("");

  const [pendingOrder, setPendingOrder] =
    useState<Order | null>(null);

  const [pendingPaymentId, setPendingPaymentId] =
    useState<string | null>(null);

  const [cartSnapshot, setCartSnapshot] =
    useState<Cart | null>(null);

  const [checkoutReady, setCheckoutReady] =
    useState(false);

  const checkoutSessionRef =
    useRef<CheckoutSession | null>(null);

  // --------------------------------------------------
  // Queries
  // --------------------------------------------------

  const {
    data: cart,
    isLoading: isCartLoading,
    isError: isCartError,
    refetch: refetchCart,
  } = useGetCartQuery(undefined, {
    skip: !isAuthenticated,
  });

  const {
    data: addresses = [],
    isLoading: isAddressesLoading,
    isError: isAddressesError,
    refetch: refetchAddresses,
  } = useGetAddressesQuery(undefined, {
    skip: !isAuthenticated,
  });

  // Payment query
  const {
    currentData: payment,
    isLoading: isPaymentLoading,
  } = useGetPaymentQuery(pendingPaymentId ?? "", {
    skip: !pendingPaymentId,
    pollingInterval: 5000,
    skipPollingIfUnfocused: true,
  });

  // Recover previously created order
  const {
    currentData: recoveredOrder,
    isLoading: isRecoveredOrderLoading,
    isError: isRecoveredOrderError,
    refetch: refetchRecoveredOrder,
  } = useGetOrderQuery(
    checkoutSessionRef.current?.orderId ?? "",
    {
      skip:
        !checkoutReady ||
        !checkoutSessionRef.current?.orderId,
    }
  );

  // Prefer the order already in state.
  // Otherwise use the order recovered from the backend.
  const activeOrder = pendingOrder ?? recoveredOrder ?? null;

  // --------------------------------------------------
  // Mutations
  // --------------------------------------------------

  const [createAddress, createAddressState] =
    useCreateAddressMutation();

  const [updateAddress, updateAddressState] =
    useUpdateAddressMutation();

  const [deleteAddress, deleteAddressState] =
    useDeleteAddressMutation();

  const [createOrder, createOrderState] =
    useCreateOrderMutation();

  const [initializePayment, paymentState] =
    useInitializePaymentMutation();

// --------------------------------------------------
// Authentication
// --------------------------------------------------

useEffect(() => {
  if (!isAuthInitialized) return;

  if (!isAuthenticated) {
    router.replace("/login?next=%2Fcheckout");
  }
}, [isAuthenticated, isAuthInitialized, router]);

  // --------------------------------------------------
  // Restore checkout session
  // --------------------------------------------------

  useEffect(() => {
    if (!isAuthenticated) return;

    const savedSession = getCheckoutSession();

    if (savedSession) {
      checkoutSessionRef.current = savedSession;

      setPendingPaymentId(savedSession.paymentId);
      setCartSnapshot(savedSession.cartSnapshot);
    } else {
      const newSession = createCheckoutSession();

      checkoutSessionRef.current = newSession;
    }

    setCheckoutReady(true);
  }, [isAuthenticated]);

  // --------------------------------------------------
  // Recover order
  // --------------------------------------------------

  useEffect(() => {
    if (recoveredOrder) {
      setPendingOrder(recoveredOrder);
    }
  }, [recoveredOrder]);

  useEffect(() => {
    if (!isRecoveredOrderError) return;

    setMessage(
      "بازیابی سفارش از سرور ناموفق بود. برای جلوگیری از ثبت سفارش تکراری، ابتدا بازیابی سفارش را دوباره امتحان کنید."
    );
  }, [isRecoveredOrderError]);

  // --------------------------------------------------
  // Payment status handling
  // --------------------------------------------------

  useEffect(() => {
    if (!payment || !checkoutSessionRef.current) {
      return;
    }

    const session = checkoutSessionRef.current;

    // Payment succeeded
    if (payment.status === "success") {
      const paymentId = payment.payment_id;

      clearCheckoutSession();

      checkoutSessionRef.current = null;

      router.replace(
        `/payment/result?payment_id=${encodeURIComponent(
          paymentId
        )}`
      );

      return;
    }

    // Payment failed or cancelled:
    // Keep the order, but create a new payment attempt key.
    if (
      (payment.status === "failed" ||
        payment.status === "cancelled") &&
      session.paymentId === payment.payment_id
    ) {
      session.paymentId = null;
      session.paymentIdempotencyKey =
        crypto.randomUUID();

      checkoutSessionRef.current = session;

      saveCheckoutSession(session);

      setPendingPaymentId(null);
    }
  }, [payment, router]);

  // --------------------------------------------------
  // Select default address
  // --------------------------------------------------

  useEffect(() => {
    if (!addresses.length || selectedAddressId) {
      return;
    }

    const defaultAddress = addresses.find(
      (address) => address.is_default
    );

    setSelectedAddressId(
      defaultAddress?.id ?? addresses[0].id
    );
  }, [addresses, selectedAddressId]);

  // --------------------------------------------------
  // Address handlers
  // --------------------------------------------------

  const handleAddressSubmit = async (
    payload: AddressPayload
  ) => {
    setMessage("");

    try {
      if (editingAddress) {
        const updated = await updateAddress({
          id: editingAddress.id,
          body: payload,
        }).unwrap();

        setSelectedAddressId(updated.id);
      } else {
        const created = await createAddress(
          payload
        ).unwrap();

        setSelectedAddressId(created.id);
      }

      setEditingAddress(null);
      setShowAddressForm(false);
    } catch (error) {
      setMessage(getErrorMessage(error));
    }
  };

  const handleEditAddress = (address: Address) => {
    setEditingAddress(address);
    setShowAddressForm(true);
    setMessage("");
  };

  const handleDeleteAddress = async (id: string) => {
    if (
      !window.confirm(
        "آیا از حذف این آدرس مطمئن هستید؟"
      )
    ) {
      return;
    }

    setMessage("");

    try {
      await deleteAddress(id).unwrap();

      if (selectedAddressId === id) {
        const remaining = addresses.filter(
          (address) => address.id !== id
        );

        setSelectedAddressId(
          remaining[0]?.id ?? null
        );
      }
    } catch (error) {
      setMessage(getErrorMessage(error));
    }
  };

  const handleAddAddress = () => {
    setEditingAddress(null);
    setShowAddressForm(true);
    setMessage("");
  };

  const handleCancelAddressForm = () => {
    setEditingAddress(null);
    setShowAddressForm(false);
  };

  // --------------------------------------------------
  // Payment initialization
  // --------------------------------------------------

  const startPayment = async (order: Order) => {
    setMessage("");

    const session = checkoutSessionRef.current;

    if (!session) {
      setMessage(
        "اطلاعات نشست پرداخت در دسترس نیست. صفحه را مجدداً بارگذاری کنید."
      );
      return;
    }

    try {
      // Save the key before sending the request.
      saveCheckoutSession(session);

      const result = await initializePayment({
        order_id: order.id,
        provider: "zarinpal",
        idempotency_key:
          session.paymentIdempotencyKey,
      }).unwrap();

      session.orderId = order.id;
      session.paymentId = result.payment_id;

      checkoutSessionRef.current = session;

      saveCheckoutSession(session);

      setPendingPaymentId(result.payment_id);

      if (result.payment_url) {
        window.location.assign(result.payment_url);
        return;
      }

      setMessage(
        "درخواست پرداخت ثبت شد، اما هنوز لینک انتقال به درگاه آماده نیست. وضعیت پرداخت در همین صفحه پیگیری می‌شود."
      );
    } catch (error) {
      // Keep the same idempotency key after network errors.
      saveCheckoutSession(session);

      setMessage(getErrorMessage(error));
    }
  };

  // --------------------------------------------------
  // Create order
  // --------------------------------------------------

  const handleCheckout = async () => {
    setMessage("");

    if (!checkoutReady) {
      setMessage("لطفاً چند لحظه صبر کنید.");
      return;
    }

    // If the order already exists, never create another one.
    if (activeOrder) {
      await startPayment(activeOrder);
      return;
    }

    if (isRecoveredOrderError) {
      setMessage(
        "ابتدا باید سفارش قبلی را از سرور بازیابی کنید."
      );
      return;
    }

    if (!selectedAddressId) {
      setMessage(
        "لطفاً ابتدا آدرس تحویل سفارش را انتخاب کنید."
      );
      return;
    }

    if (!cart || cart.items.length === 0) {
      setMessage("سبد خرید شما خالی است.");
      return;
    }

    const hasStockProblem = cart.items.some(
      (item) =>
        item.available_stock < 1 ||
        item.quantity > item.available_stock
    );

    if (hasStockProblem) {
      setMessage(
        "موجودی بعضی از محصولات تغییر کرده است. لطفاً سبد خرید را بررسی کنید."
      );
      return;
    }

    const session =
      checkoutSessionRef.current ??
      createCheckoutSession();

    checkoutSessionRef.current = session;

    // Persist cart snapshot and order key before request.
    session.cartSnapshot = cart;

    saveCheckoutSession(session);

    setCartSnapshot(cart);

    try {
      const order = await createOrder({
        address_id: selectedAddressId,
        idempotency_key:
          session.orderIdempotencyKey,
        ...(couponCode.trim()
          ? { coupon_code: couponCode.trim() }
          : {}),
      }).unwrap();

      // Save order ID immediately.
      session.orderId = order.id;

      checkoutSessionRef.current = session;

      saveCheckoutSession(session);

      setPendingOrder(order);

      await startPayment(order);
    } catch (error) {
      // Keep the same order idempotency key.
      saveCheckoutSession(session);

      setMessage(getErrorMessage(error));
    }
  };

  // --------------------------------------------------
  // Derived state
  // --------------------------------------------------

  const currentCart = cart ?? cartSnapshot;

  const displayCart: Cart | null = activeOrder
    ? cartSnapshot ?? currentCart
    : currentCart;

  const hasStockProblem = Boolean(
    displayCart?.items.some(
      (item) =>
        item.available_stock < 1 ||
        item.quantity > item.available_stock
    )
  );

  const isSavingAddress =
    createAddressState.isLoading ||
    updateAddressState.isLoading;

  const isSubmitting =
    createOrderState.isLoading ||
    paymentState.isLoading;

  // Prevent a second attempt while payment is unresolved.
  const paymentBlocksNewAttempt =
    payment?.status === "unknown" ||
    payment?.status === "review_required" ||
    payment?.status === "pending" ||
    payment?.status === "initiated";

  // This becomes true when a previous order ID exists,
  // but the backend has not returned that order yet.
  const isRecoveringOrder =
    checkoutReady &&
    Boolean(checkoutSessionRef.current?.orderId) &&
    isRecoveredOrderLoading &&
    !activeOrder;

  // --------------------------------------------------
  // Loading states
  // --------------------------------------------------

  if (
    !isAuthInitialized ||
    (isAuthenticated && !checkoutReady) ||
    isRecoveringOrder
  ) {
    return (
      <main
        dir="rtl"
        className="px-4 py-20 text-center"
      >
        <div className="mx-auto h-10 w-10 animate-spin rounded-full border-4 border-pink-100 border-t-pink-600" />

        <p className="mt-5 text-sm text-gray-500">
          در حال بازیابی اطلاعات سفارش...
        </p>
      </main>
    );
  }

  if (!isAuthenticated) {
    return (
      <main
        dir="rtl"
        className="mx-auto max-w-7xl px-4 py-24 text-center"
      >
        <p className="text-gray-500">
          در حال انتقال به صفحه ورود...
        </p>
      </main>
    );
  }

  if (isCartLoading || isAddressesLoading) {
    return (
      <main
        dir="rtl"
        className="mx-auto max-w-7xl animate-pulse px-4 py-16"
      >
        <div className="mb-8 h-8 w-48 rounded bg-gray-200" />

        <div className="grid gap-8 lg:grid-cols-3">
          <div className="space-y-4 lg:col-span-2">
            <div className="h-40 rounded-2xl bg-gray-200" />
            <div className="h-40 rounded-2xl bg-gray-200" />
          </div>

          <div className="h-72 rounded-2xl bg-gray-200" />
        </div>
      </main>
    );
  }

  // --------------------------------------------------
  // Cart availability
  // --------------------------------------------------

  if (!displayCart) {
    return (
      <main
        dir="rtl"
        className="px-4 py-20 text-center"
      >
        <h1 className="font-bold text-gray-900">
          {isCartError
            ? "دریافت سبد خرید ناموفق بود."
            : "اطلاعات سبد خرید در دسترس نیست."}
        </h1>

        <button
          type="button"
          onClick={() => void refetchCart()}
          className="mt-5 rounded-xl bg-pink-600 px-6 py-3 text-sm text-white"
        >
          تلاش مجدد
        </button>
      </main>
    );
  }

  // --------------------------------------------------
  // Empty cart
  // --------------------------------------------------

  if (
    displayCart.items.length === 0 &&
    !activeOrder
  ) {
    return (
      <main
        dir="rtl"
        className="px-4 py-20 text-center"
      >
        <h1 className="text-xl font-bold text-gray-900">
          سبد خرید شما خالی است.
        </h1>

        <Link
          href="/products"
          className="mt-6 inline-block rounded-xl bg-pink-600 px-6 py-3 text-sm font-bold text-white"
        >
          مشاهده محصولات
        </Link>
      </main>
    );
  }

  // --------------------------------------------------
  // Payment status labels
  // --------------------------------------------------

  const paymentStatusLabels: Record<string, string> = {
    initiated: "درخواست پرداخت در حال ثبت است.",
    pending: "پرداخت در انتظار تأیید درگاه است.",
    success: "پرداخت با موفقیت انجام شده است.",
    failed: "پرداخت ناموفق بوده است.",
    cancelled: "پرداخت لغو شده است.",
    unknown: "وضعیت پرداخت هنوز مشخص نیست. لطفاً پرداخت دیگری انجام ندهید.",
    review_required:
      "پرداخت نیازمند بررسی پشتیبانی است. لطفاً پرداخت جدیدی انجام ندهید.",
  };

  // --------------------------------------------------
  // Render
  // --------------------------------------------------

  return (
    <main
      dir="rtl"
      className="min-h-screen bg-gray-50 text-gray-600"
    >
      <div className="mx-auto max-w-7xl px-4 py-10">
        {/* Header */}

        <div className="mb-10">
          <h1 className="text-2xl font-bold text-gray-900">
            تکمیل سفارش
          </h1>

          <p className="mt-2 text-sm text-gray-500">
            آدرس تحویل و اطلاعات سفارش خود را بررسی کنید.
          </p>
        </div>

        {/* General message */}

        {message && (
          <div
            role="alert"
            className="mb-6 rounded-xl border border-red-100 bg-red-50 p-4 text-sm leading-7 text-red-600"
          >
            {message}
          </div>
        )}

        {/* Address error */}

        {isAddressesError && (
          <div
            role="alert"
            className="mb-6 rounded-xl bg-red-50 p-4 text-sm text-red-600"
          >
            دریافت آدرس‌ها ناموفق بود.

            <button
              type="button"
              onClick={() => void refetchAddresses()}
              className="mr-3 font-bold underline"
            >
              تلاش مجدد
            </button>
          </div>
        )}

        {/* Order recovery error */}

        {isRecoveredOrderError && (
          <div
            role="alert"
            className="mb-6 rounded-xl border border-red-100 bg-red-50 p-4 text-sm leading-7 text-red-600"
          >
            <p>
              بازیابی سفارش از سرور ناموفق بود. برای
              جلوگیری از ثبت سفارش تکراری، ابتدا بازیابی
              سفارش را دوباره امتحان کنید.
            </p>

            <button
              type="button"
              onClick={() => void refetchRecoveredOrder()}
              className="mt-3 font-bold underline"
            >
              تلاش مجدد برای بازیابی سفارش
            </button>
          </div>
        )}

        <div className="grid items-start gap-8 lg:grid-cols-3">
          {/* Main column */}

          <div className="space-y-8 lg:col-span-2">
            {/* Address section */}

            <section className="rounded-2xl border border-gray-100 bg-white p-5 sm:p-6">
              <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-bold text-gray-900">
                    آدرس تحویل سفارش
                  </h2>

                  <p className="mt-1 text-xs text-gray-500">
                    آدرس موردنظر برای ارسال سفارش را انتخاب کنید.
                  </p>
                </div>

                {!showAddressForm && !activeOrder && (
                  <button
                    type="button"
                    onClick={handleAddAddress}
                    className="rounded-xl border border-pink-200 px-4 py-2.5 text-sm font-semibold text-pink-600 hover:bg-pink-50"
                  >
                    افزودن آدرس جدید
                  </button>
                )}
              </div>

              {showAddressForm && !activeOrder ? (
                <AddressForm
                  initialAddress={editingAddress}
                  isSaving={isSavingAddress}
                  onSubmit={handleAddressSubmit}
                  onCancel={handleCancelAddressForm}
                />
              ) : (
                <AddressSelector
                  addresses={addresses}
                  selectedAddressId={selectedAddressId}
                  onSelect={setSelectedAddressId}
                  onEdit={handleEditAddress}
                  onDelete={handleDeleteAddress}
                  isDeleting={deleteAddressState.isLoading}
                />
              )}
            </section>

            {/* Order items */}

            <section className="rounded-2xl border border-gray-100 bg-white p-5 sm:p-6">
              <div className="mb-5 flex items-center justify-between">
                <h2 className="text-lg font-bold text-gray-900">
                  محصولات سفارش
                </h2>

                {!activeOrder && (
                  <Link
                    href="/cart"
                    className="text-sm font-medium text-pink-600"
                  >
                    ویرایش سبد خرید
                  </Link>
                )}
              </div>

              <div className="space-y-4">
                {displayCart.items.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center gap-4 border-b border-gray-100 pb-4 last:border-0 last:pb-0"
                  >
                    <div className="h-16 w-16 shrink-0 overflow-hidden rounded-xl bg-gray-100">
                      {item.product_image ? (
                        <img
                          src={item.product_image}
                          alt={item.product_name}
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <div className="flex h-full items-center justify-center text-xs text-gray-400">
                          بدون تصویر
                        </div>
                      )}
                    </div>

                    <div className="min-w-0 flex-1">
                      <h3 className="truncate text-sm font-semibold text-gray-800">
                        {item.product_name}
                      </h3>

                      <p className="mt-1 text-xs text-gray-500">
                        {item.variant_name || item.sku}
                      </p>

                      <p className="mt-1 text-xs text-gray-400">
                        تعداد:{" "}
                        {item.quantity.toLocaleString("fa-IR")}
                      </p>
                    </div>

                    <strong className="shrink-0 text-sm text-gray-800">
                      {Number(item.line_total).toLocaleString("fa-IR")}
                      {" تومان"}
                    </strong>
                  </div>
                ))}
              </div>
            </section>

            {/* Payment status */}

            {pendingPaymentId && (
              <section className="rounded-2xl border border-gray-100 bg-white p-5">
                <h2 className="font-bold text-gray-900">
                  وضعیت پرداخت
                </h2>

                {isPaymentLoading && !payment ? (
                  <p className="mt-3 text-sm text-gray-500">
                    در حال دریافت وضعیت پرداخت...
                  </p>
                ) : payment ? (
                  <>
                    <p className="mt-3 text-sm leading-7 text-gray-600">
                      {paymentStatusLabels[payment.status] ??
                        payment.status}
                    </p>

                    <p className="mt-2 text-xs text-gray-400">
                      شماره سفارش: {payment.order_number}
                    </p>

                    {payment.review_reason && (
                      <p className="mt-2 text-xs text-amber-600">
                        علت نیاز به بررسی: {payment.review_reason}
                      </p>
                    )}
                  </>
                ) : (
                  <p className="mt-3 text-sm text-gray-500">
                    دریافت اطلاعات پرداخت امکان‌پذیر نبود.
                  </p>
                )}
              </section>
            )}
          </div>

          {/* Summary column */}

          <div className="space-y-4 lg:sticky lg:top-6">
            {activeOrder && (
              <div className="rounded-xl border border-amber-100 bg-amber-50 p-4 text-sm leading-7 text-amber-800">
                سفارش شما با شماره{" "}
                <strong>{activeOrder.order_number}</strong>{" "}
                ثبت شده است. برای ادامه، از دکمه پرداخت مجدد
                استفاده کنید. این کار سفارش جدیدی ایجاد نمی‌کند.
              </div>
            )}

            <CheckoutSummary
              cart={displayCart}
              order={activeOrder}
              couponCode={couponCode}
              onCouponChange={setCouponCode}
              disabled={
                isRecoveringOrder ||
                isRecoveredOrderError ||
                paymentBlocksNewAttempt ||
                (!activeOrder &&
                  (!selectedAddressId || hasStockProblem))
              }
              isSubmitting={isSubmitting}
              hasPendingOrder={Boolean(activeOrder)}
              onSubmit={() => void handleCheckout()}
            />

            {activeOrder && (
              <Link
                href={`/orders/${activeOrder.id}`}
                className="block w-full rounded-xl border border-gray-200 bg-white px-5 py-3 text-center text-sm font-semibold text-gray-600 hover:bg-gray-50"
              >
                مشاهده جزئیات سفارش
              </Link>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
