
export interface CatalogCategory {
  id: number;
  name: string;
  slug: string;
}

export interface CatalogBrand {
  id: number;
  name: string;
  slug: string;
}

export interface ProductVariant {
  id: number;
  sku: string;
  name: string;
  price: string;
  stock: number;
}

export interface Product {
  id: number;
  name: string;
  slug: string;
  description: string;
  category: CatalogCategory;
  brand: CatalogBrand | null;
  variants: ProductVariant[];
  created_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface GetProductsParams {
  page?: number;
  page_size?: number;
  category?: string;
  brand?: string;
  search?: string;
  in_stock?: boolean;
}
