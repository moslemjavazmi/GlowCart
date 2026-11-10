export type PaymentProvider = "zarinpal";

export type PaymentStatus =
  | "initiated"
  | "pending"
  | "success"
  | "failed"
  | "cancelled"
  | "unknown"
  | "review_required";

export interface InitializePaymentRequest {
  order_id: string;
  provider: PaymentProvider;
  idempotency_key: string;
}

export interface InitializePaymentResponse {
  payment_id: string;
  order_id: string;
  status: PaymentStatus;
  amount: string;
  payment_url: string | null;
  reused: boolean;
}

export interface PaymentDetail {
  payment_id: string;
  order_id: string;
  order_number: string;
  status: PaymentStatus;
  amount: string;
  provider: PaymentProvider;
  provider_reference: string | null;
  review_reason: string | null;
  paid_at: string | null;
  created_at: string;
}