"use client";

import {
  parseAsInteger,
  parseAsString,
  useQueryStates,
} from "nuqs";

export const productFilterParsers = {
  q: parseAsString.withDefault(""),

  category: parseAsString.withDefault(""),

  brand: parseAsString.withDefault(""),

  in_stock: parseAsString.withDefault("all"),

  min_price: parseAsString.withDefault(""),

  max_price: parseAsString.withDefault(""),

  ordering: parseAsString.withDefault("-created_at"),

  page: parseAsInteger.withDefault(1),
};

export function useProductFilters() {
  const [filters, setFilters] = useQueryStates(
    productFilterParsers,
    {
      history: "replace",
      shallow: true,
      scroll: false,
    }
  );

  const updateFilters = async (
    values: Partial<typeof filters>
  ) => {
    return setFilters({
      ...values,
      page: 1,
    });
  };

  const changePage = async (page: number) => {
    return setFilters({
      page: Math.max(1, page),
    });
  };

  const clearFilters = async () => {
    return setFilters({
      q: null,
      category: null,
      brand: null,
      in_stock: null,
      min_price: null,
      max_price: null,
      ordering: null,
      page: null,
    });
  };

  return {
    filters,
    setFilters,
    updateFilters,
    changePage,
    clearFilters,
  };
}