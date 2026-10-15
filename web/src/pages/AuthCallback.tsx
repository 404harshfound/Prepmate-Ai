import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router";

import { useAuth } from "../auth/context";
import { PageStatus } from "../components/PageStatus";

const GIVE_UP_AFTER_MS = 15_000;

/**
 * Where the email link and Google send people back to. The Supabase client
 * swaps the one-time code in the URL for a session by itself; this page just
 * waits for that, and explains what to do if it can't happen.
 */
export function AuthCallback() {
  const { session } = useAuth();
  const [linkError] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    const hash = new URLSearchParams(window.location.hash.slice(1));
    return params.get("error_description") ?? hash.get("error_description");
  });
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setTimedOut(true);
    }, GIVE_UP_AFTER_MS);
    return () => {
      window.clearTimeout(timer);
    };
  }, []);

  if (session) return <Navigate to="/" replace />;

  if (linkError || timedOut) {
    return (
      <PageStatus title="That sign-in link didn't work">
        <p>
          Links work once, expire after a while, and only in the browser you requested them
          from.
        </p>
        <Link to="/sign-in" className="btn btn-primary mt-6">
          Get a new link
        </Link>
      </PageStatus>
    );
  }

  return <PageStatus title="Signing you in" />;
}
