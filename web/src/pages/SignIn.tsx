import { useState, type SubmitEvent } from "react";
import { Navigate, useLocation } from "react-router";

import { useAuth } from "../auth/context";
import { Wordmark } from "../components/Wordmark";
import { config } from "../lib/env";
import { authRedirectUrl, supabase } from "../lib/supabase";

type Stage = { kind: "form" } | { kind: "sending" } | { kind: "sent"; email: string };

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function friendlyAuthError(status: number | undefined, message: string): string {
  if (status === 429) {
    return "Too many sign-in emails were requested. Wait a few minutes, then try again.";
  }
  if (/rate limit/i.test(message)) {
    return "Too many sign-in emails were requested. Wait a few minutes, then try again.";
  }
  return "We couldn't send the sign-in email. Check the address and try again.";
}

export function SignIn() {
  const { session, loading } = useAuth();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [stage, setStage] = useState<Stage>({ kind: "form" });
  const [error, setError] = useState<string | null>(null);

  const from = (location.state as { from?: string } | null)?.from;
  if (!loading && session) return <Navigate to={from ?? "/"} replace />;

  async function sendLink(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    const address = email.trim().toLowerCase();
    if (!EMAIL_PATTERN.test(address)) {
      setError("Enter a full email address, like name@example.com.");
      return;
    }
    setError(null);
    setStage({ kind: "sending" });
    const { error: sendError } = await supabase.auth.signInWithOtp({
      email: address,
      options: { emailRedirectTo: authRedirectUrl(), shouldCreateUser: true },
    });
    if (sendError) {
      setError(friendlyAuthError(sendError.status, sendError.message));
      setStage({ kind: "form" });
      return;
    }
    setStage({ kind: "sent", email: address });
  }

  async function continueWithGoogle() {
    setError(null);
    const { error: oauthError } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: authRedirectUrl() },
    });
    if (oauthError) setError("Google sign-in isn't available right now. Use your email instead.");
  }

  return (
    <div className="grid min-h-dvh md:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
      <section
        aria-labelledby="pitch"
        className="sheet border-b border-rule pr-6 md:border-r md:border-b-0 md:pr-12"
      >
        <Wordmark />
        <div className="rules-2 max-w-xl md:rules-5">
          <h1 id="pitch" className="sheet-title">
            Practise the answer before the interview asks for it.
          </h1>
          <p className="rules-1 max-w-md text-graphite">
            Answer real placement questions out loud. Get a score on structure, clarity and
            pace, with the exact sentences to fix.
          </p>
        </div>
      </section>

      <main className="flex items-start px-4 py-10 md:items-center md:px-12">
        <div className="w-full max-w-sm">
          {stage.kind === "sent" ? (
            <div role="status" aria-live="polite">
              <h2 className="font-display text-2xl font-medium text-ink">Check your inbox</h2>
              <p className="mt-3">
                We sent a sign-in link to <strong className="break-all">{stage.email}</strong>.
                Open it in this browser to finish signing in.
              </p>
              <button
                type="button"
                className="btn btn-quiet mt-6"
                onClick={() => {
                  setStage({ kind: "form" });
                }}
              >
                Use a different email
              </button>
            </div>
          ) : (
            <>
              <h2 className="font-display text-2xl font-medium text-ink">Sign in</h2>
              <p className="mt-2 text-pencil">We'll email you a link. No password to remember.</p>

              <form className="mt-6" noValidate onSubmit={(event) => void sendLink(event)}>
                <label htmlFor="email" className="field-label">
                  Email address
                </label>
                <input
                  id="email"
                  type="email"
                  inputMode="email"
                  autoComplete="email"
                  autoCapitalize="none"
                  spellCheck={false}
                  required
                  maxLength={254}
                  className="field-input"
                  value={email}
                  onChange={(event) => {
                    setEmail(event.target.value);
                  }}
                  aria-invalid={error ? true : undefined}
                  aria-describedby={error ? "sign-in-error" : undefined}
                />
                <button
                  type="submit"
                  className="btn btn-primary mt-4 w-full"
                  disabled={stage.kind === "sending"}
                >
                  {stage.kind === "sending" ? "Sending link" : "Email me a sign-in link"}
                </button>
              </form>

              {config.googleEnabled ? (
                <button
                  type="button"
                  className="btn btn-quiet mt-3 w-full"
                  onClick={() => void continueWithGoogle()}
                >
                  Continue with Google
                </button>
              ) : null}

              {error ? (
                <p id="sign-in-error" role="alert" className="mt-4 text-danger">
                  {error}
                </p>
              ) : null}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
