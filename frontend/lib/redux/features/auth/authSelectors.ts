import type { RootState } from "../../store";

export const selectCurrentUser = (state: RootState) =>
  state.auth.user;

export const selectAccessToken = (state: RootState) =>
  state.auth.accessToken;

export const selectIsAuthenticated = (state: RootState) =>
  state.auth.isAuthenticated;

export const selectIsAuthInitialized = (state: RootState) =>
  state.auth.isInitialized;

export const selectUserRole = (state: RootState) =>
  state.auth.user?.role ?? null;