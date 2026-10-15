import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router";

import { AuthProvider } from "./auth/AuthProvider";
import { RequireAuth } from "./auth/RequireAuth";
import { ApiError } from "./lib/api";
import { AuthCallback } from "./pages/AuthCallback";
import { Home } from "./pages/Home";
import { NotFound } from "./pages/NotFound";
import { Practice } from "./pages/Practice";
import { SignIn } from "./pages/SignIn";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      // Retry network blips and server errors, never "you're not signed in".
      retry: (failureCount, error) =>
        failureCount < 2 && !(error instanceof ApiError && error.status > 0 && error.status < 500),
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/sign-in" element={<SignIn />} />
            <Route path="/auth/callback" element={<AuthCallback />} />
            <Route
              path="/"
              element={
                <RequireAuth>
                  <Home />
                </RequireAuth>
              }
            />
            <Route
              path="/practice"
              element={
                <RequireAuth>
                  <Practice />
                </RequireAuth>
              }
            />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
