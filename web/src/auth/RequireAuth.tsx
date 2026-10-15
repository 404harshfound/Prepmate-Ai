import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router";

import { PageStatus } from "../components/PageStatus";
import { useAuth } from "./context";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { session, loading } = useAuth();
  const location = useLocation();

  if (loading) return <PageStatus title="Opening your sheet" />;
  if (!session) {
    return <Navigate to="/sign-in" replace state={{ from: location.pathname }} />;
  }
  return children;
}
