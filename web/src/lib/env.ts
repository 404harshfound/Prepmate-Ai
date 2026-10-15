/**
 * Build-time settings. Everything here ships to the browser, so it must
 * never contain a secret. Problems are collected rather than thrown, so a
 * misconfigured deploy shows a clear page instead of a blank screen.
 */

export interface AppConfig {
  supabaseUrl: string;
  supabaseKey: string;
  apiUrl: string;
  googleEnabled: boolean;
}

function readUrl(name: string, value: string | undefined, problems: string[]): string {
  if (!value) {
    problems.push(`${name} is not set.`);
    return "";
  }
  try {
    const url = new URL(value);
    if (import.meta.env.PROD && url.protocol !== "https:") {
      problems.push(`${name} must use https in production.`);
    }
    return url.origin;
  } catch {
    problems.push(`${name} is not a valid URL.`);
    return "";
  }
}

function load(): { config: AppConfig; problems: string[] } {
  const env = import.meta.env;
  const problems: string[] = [];
  const supabaseUrl = readUrl("VITE_SUPABASE_URL", env.VITE_SUPABASE_URL as string | undefined, problems);
  const apiUrl = readUrl("VITE_API_URL", env.VITE_API_URL as string | undefined, problems);
  const supabaseKey = (env.VITE_SUPABASE_PUBLISHABLE_KEY as string | undefined) ?? "";

  if (!supabaseKey) {
    problems.push("VITE_SUPABASE_PUBLISHABLE_KEY is not set.");
  } else if (supabaseKey.startsWith("sb_secret_")) {
    // A secret key in the browser would hand every visitor full database access.
    problems.push("VITE_SUPABASE_PUBLISHABLE_KEY holds a secret key. Use the publishable key.");
  }

  return {
    config: {
      supabaseUrl,
      supabaseKey,
      apiUrl,
      googleEnabled: env.VITE_ENABLE_GOOGLE === "true",
    },
    problems,
  };
}

export const { config, problems: configProblems } = load();
