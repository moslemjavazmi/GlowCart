export interface Address {
  id: string;
  title: string;
  recipient_name: string;
  phone_number: string;
  province: string;
  city: string;
  postal_code: string;
  address_line: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface AddressPayload {
  title: string;
  recipient_name: string;
  phone_number: string;
  province: string;
  city: string;
  postal_code: string;
  address_line: string;
  is_default: boolean;
}

export interface AddressListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Address[];
}

export interface AddressFormValues {
  title: string;
  recipient_name: string;
  phone_number: string;
  province: string;
  city: string;
  postal_code: string;
  address_line: string;
  is_default: boolean;
}