export type OrderStatus =
  | "pending"
  | "awaiting_payment"
  | "paid"
  | "processing"
  | "shipped"
  | "delivered"
  | "cancelled"
  | "refunded"
  | "expired";

export interface OrderItem {
  id: string;
  product_name: string;
  variant_name: string;
  sku: string;
  unit_price: string;
  quantity: number;
  line_total: string;
}

export interface Order {
  id: string;
  order_number: string;
  status: OrderStatus;

  subtotal: string;
  shipping_cost: string;
  discount_amount: string;
  total_amount: string;

  recipient_name: string | null;
  phone_number: string | null;
  province: string | null;
  city: string | null;
  postal_code: string | null;
  address_line: string | null;

  items: OrderItem[];

  created_at: string;
  updated_at: string;
}

export interface CreateOrderRequest {
  address_id: string;
  coupon_code?: string;
  idempotency_key: string;
}

export interface CancelledOrderSummary {
  id: string;
  order_number: string;
  status: OrderStatus;
  inventory_released: boolean;
}

export interface CancelOrderResponse {
  message: string;
  order: CancelledOrderSummary;
}