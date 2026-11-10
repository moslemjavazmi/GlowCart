export interface CartItem {
  id: string;
  variant_id: number;

  product_name: string;
  variant_name: string;
  sku: string;

  available_stock: number;
  product_image: string | null;

  unit_price: string;
  quantity: number;
  line_total: string;
}

export interface Cart {
  id: string;
  items: CartItem[];

  total_items: number;
  subtotal: string;

  guest_token?: string;

  created_at: string;
  updated_at: string;
}

export interface AddCartItemRequest {
  variant_id: number;
  quantity?: number;
}

export interface UpdateCartItemRequest {
  itemId: string;
  quantity: number;
}

export interface RemoveCartItemRequest {
  itemId: string;
}

export interface MergeGuestCartRequest {
  guest_token: string;
}

export interface CartError {
  error?: string;
  detail?: string;
}