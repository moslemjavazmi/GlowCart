import { baseApi } from "@/lib/redux/services/baseApi";

import type {
  CatalogBrand,
  CatalogCategory,
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

    getCategories: builder.query<
        PaginatedResponse<CatalogCategory>,
        void
        >({
        query: () => ({
            url: "/catalog/categories/",
            method: "GET",
        }),
        }),

    getBrands: builder.query<
        PaginatedResponse<CatalogBrand>,
        void
        >({
        query: () => ({
            url: "/catalog/brands/",
            method: "GET",
        }),
    }),
  }),
});

export const {
  useGetProductsQuery,
  useGetProductBySlugQuery,
  useGetCategoriesQuery,
  useGetBrandsQuery,
} = catalogApi;