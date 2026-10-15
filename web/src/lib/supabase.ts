import { createClient } from "@supabase/supabase-js";

import { config, configProblems } from "./env";

export const supabase = createClient(
  // Placeholder values keep the client constructible when config is broken;
  // the app shows the configuration page instead of using it.
  configProblems.length === 0 ? config.supabaseUrl : "https://invalid.localhost",
  configProblems.length === 0 ? config.supabaseKey : "invalid",
  {
    auth: {
      flowType: "pkce", // the sign-in code is useless without this browser's secret
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  },
);

export function authRedirectUrl(): string {
  return `${window.location.origin}/auth/callback`;
}
