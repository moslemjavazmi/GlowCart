import { baseApi } from "./baseApi";

import type {
  Address,
  AddressPayload,
  AddressListResponse,
} from "../features/addresses/addressTypes";

type AddressListResult = Address[] | AddressListResponse;

export const addressApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getAddresses: builder.query<Address[], void>({
      query: () => ({
        url: "/orders/addresses/",
        method: "GET",
      }),

      transformResponse: (response: AddressListResult) => {
        return Array.isArray(response)
          ? response
          : response.results;
      },

      providesTags: (result) =>
        result
          ? [
              ...result.map(({ id }) => ({
                type: "Address" as const,
                id,
              })),
              { type: "Address" as const, id: "LIST" },
            ]
          : [{ type: "Address" as const, id: "LIST" }],
    }),

    createAddress: builder.mutation<Address, AddressPayload>({
      query: (body) => ({
        url: "/orders/addresses/",
        method: "POST",
        body,
      }),

      invalidatesTags: [{ type: "Address", id: "LIST" }],
    }),

    updateAddress: builder.mutation<
      Address,
      { id: string; body: Partial<AddressPayload> }
    >({
      query: ({ id, body }) => ({
        url: `/orders/addresses/${id}/`,
        method: "PATCH",
        body,
      }),

      invalidatesTags: (_result, _error, { id }) => [
        { type: "Address", id },
        { type: "Address", id: "LIST" },
      ],
    }),

    deleteAddress: builder.mutation<void, string>({
      query: (id) => ({
        url: `/orders/addresses/${id}/`,
        method: "DELETE",
      }),

      invalidatesTags: [{ type: "Address", id: "LIST" }],
    }),
  }),

  overrideExisting: false,
});

export const {
  useGetAddressesQuery,
  useCreateAddressMutation,
  useUpdateAddressMutation,
  useDeleteAddressMutation,
} = addressApi;