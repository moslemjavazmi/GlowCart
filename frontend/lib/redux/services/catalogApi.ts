
import { baseApi } from "@/lib/redux/services/baseApi";

import type {
  GetProductsParams,
  PaginatedResponse,
  Product,
} from "@/lib/redux/features/catalog/catalogTypes";

export const catalogApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getProducts: builder.query<
      PaginatedResponse<Product>,
      GetProductsParams | void
    >({
      query: (params) => ({
        url: "/catalog/products/",
        method: "GET",
        params: params ?? undefined,
      }),
    }),

    getProductBySlug: builder.query<Product, string>({
      query: (slug) => ({
        url: `/catalog/products/${slug}/`,
        method: "GET",
      }),
    }),
  }),
});

export const {
  useGetProductsQuery,
  useGetProductBySlugQuery,
} = catalogApi;
