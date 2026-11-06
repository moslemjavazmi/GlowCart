"use client";

import { useEffect, useRef } from "react";

import { useAppDispatch } from "../../hooks";
import { authApi } from "../../services/authApi";

import {
  clearCredentials,
  setAccessToken,
  setAuthInitialized,
  setCredentials,
} from "./authSlice";

import { authStorage } from "./authStorage";

export default function AuthInitializer() {
  const dispatch = useAppDispatch();
  const initializedRef = useRef(false);

  useEffect(() => {
    if (initializedRef.current) return;

    initializedRef.current = true;

    const initializeAuth = async () => {
      const refreshToken = authStorage.getRefreshToken();

      if (!refreshToken) {
        dispatch(setAuthInitialized());
        return;
      }

      try {
        // دریافت Access Token جدید
       const tokens = await dispatch(
            authApi.endpoints.refreshToken.initiate({
                refresh: refreshToken,
            })
            ).unwrap();

            if (tokens.refresh) {
            authStorage.setRefreshToken(tokens.refresh);
            }

            dispatch(setAccessToken(tokens.access));

            const user = await dispatch(
            authApi.endpoints.getMe.initiate(undefined, {
                forceRefetch: true,
            })
            ).unwrap();

            dispatch(
            setCredentials({
                user,
                access: tokens.access,
            })
            );
      } catch {
        authStorage.clearRefreshToken();
        dispatch(clearCredentials());
      }
    };

    void initializeAuth();
  }, [dispatch]);

  return null;
}