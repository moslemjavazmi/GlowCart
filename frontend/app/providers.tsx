"use client";

import StoreProvider from "@/lib/redux/StoreProvider";
import AuthInitializer from "@/lib/redux/features/auth/AuthInitializer";

export default function Providers({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <StoreProvider>
      <AuthInitializer />
      {children}
    </StoreProvider>
  );
}