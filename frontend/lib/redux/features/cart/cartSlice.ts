import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

interface CartState {
  guestToken: string | null;
}

const initialState: CartState = {
  guestToken: null,
};

const cartSlice = createSlice({
  name: "cart",
  initialState,

  reducers: {
    setGuestToken: (
      state,
      action: PayloadAction<string>
    ) => {
      state.guestToken = action.payload;
    },

    clearGuestToken: (state) => {
      state.guestToken = null;
    },
  },
});

export const {
  setGuestToken,
  clearGuestToken,
} = cartSlice.actions;

export default cartSlice.reducer;