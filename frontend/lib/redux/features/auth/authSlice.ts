import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { AuthUser } from "./authTypes";

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isInitialized: boolean;
}

const initialState: AuthState = {
  user: null,
  accessToken: null,
  isAuthenticated: false,
  isInitialized: false,
};

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setCredentials: (
      state,
      action: PayloadAction<{ user: AuthUser; access: string }>
    ) => {
      state.user = action.payload.user;
      state.accessToken = action.payload.access;
      state.isAuthenticated = true;
      state.isInitialized = true;
    },

    setAccessToken: (state, action: PayloadAction<string>) => {
      state.accessToken = action.payload;
      state.isAuthenticated = true;
    },

    setCurrentUser: (state, action: PayloadAction<AuthUser>) => {
      state.user = action.payload;
      state.isAuthenticated = true;
    },

    setAuthInitialized: (state) => {
      state.isInitialized = true;
    },

    clearCredentials: (state) => {
      state.user = null;
      state.accessToken = null;
      state.isAuthenticated = false;
      state.isInitialized = true;
    },
  },
});

export const {
  setCredentials,
  setAccessToken,
  setCurrentUser,
  setAuthInitialized,
  clearCredentials,
} = authSlice.actions;

export default authSlice.reducer;