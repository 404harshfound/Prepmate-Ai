/**
 * The one place the frontend talks to our API. Every request carries the
 * current Supabase access token; errors come back in one shape.
 */

import { config } from "./env";
import { supabase } from "./supabase";

const TIMEOUT_MS = 20_000; // generous: the free API host can take a while to wake

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | null;

  constructor(status: number, code: string, message: string, requestId: string | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }

  get isAuthError(): boolean {
    return this.status === 401;
  }
}

interface ErrorEnvelope {
  error?: { code?: unknown; message?: unknown; request_id?: unknown };
}

export async function toApiError(response: Response): Promise<ApiError> {
  let body: ErrorEnvelope = {};
  try {
    body = (await response.json()) as ErrorEnvelope;
  } catch {
    // Not JSON (a proxy error page, say). Fall back to a generic message.
  }
  const error = body.error ?? {};
  const message =
    typeof error.message === "string" && error.message
      ? error.message
      : response.status >= 500
        ? "The server had a problem. Try again in a minute."
        : "That request didn't work.";
  return new ApiError(
    response.status,
    typeof error.code === "string" ? error.code : "request_failed",
    message,
    typeof error.request_id === "string" ? error.request_id : response.headers.get("X-Request-ID"),
  );
}

type Method = "GET" | "POST" | "PATCH" | "DELETE";

export async function apiRequest<T>(method: Method, path: string, body?: unknown): Promise<T> {
  const { data } = await supabase.auth.getSession(); // refreshes the token if needed
  const token = data.session?.access_token;
  if (!token) {
    throw new ApiError(401, "unauthenticated", "Sign in to continue.", null);
  }

  const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(`${config.apiUrl}${path}`, {
      method,
      headers,
      body: body === undefined ? null : JSON.stringify(body),
      signal: AbortSignal.timeout(TIMEOUT_MS),
      credentials: "omit",
    });
  } catch (cause) {
    const timedOut = cause instanceof DOMException && cause.name === "TimeoutError";
    throw new ApiError(
      0,
      timedOut ? "timeout" : "network_error",
      timedOut
        ? "The server took too long to answer. Try again."
        : "Couldn't reach the server. Check your connection and try again.",
      null,
    );
  }

  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as T;
}

// ------------------------------------------------------------------ types

export type ExperienceLevel = "student" | "fresher" | "experienced";

export interface Profile {
  display_name: string | null;
  target_role: string | null;
  experience_level: ExperienceLevel;
  created_at: string;
}

export interface Me {
  id: string;
  email: string | null;
  profile: Profile;
}

export type ProfileUpdate = Partial<{
  display_name: string;
  target_role: string;
  experience_level: ExperienceLevel;
}>;

export type RoundType = "hr" | "behavioural" | "technical" | "aptitude";

export interface Question {
  id: string;
  round_type: RoundType;
  topic: string;
  difficulty: number;
  prompt: string;
}

export interface Scores {
  structure: number;
  relevance: number;
  clarity: number;
  depth: number;
  overall: number;
}

export interface Improvement {
  issue: string;
  suggestion: string;
}

export interface Feedback {
  overall: string;
  improvements: Improvement[];
}

export interface Answer {
  id: string;
  question_id: string;
  transcript: string;
  feedback_status: "pending" | "ready" | "failed";
  scores: Scores | null;
  feedback: Feedback | null;
  model: string | null;
  created_at: string;
}

export interface Session {
  id: string;
  round_type: RoundType;
  status: "in_progress" | "completed" | "abandoned";
  started_at: string;
  completed_at: string | null;
  answer_count: number;
  average_score: number | null;
}

export interface Usage {
  feedback_calls: number;
  feedback_limit: number;
  audio_seconds: number;
  audio_seconds_limit: number;
}

export const api = {
  me: () => apiRequest<Me>("GET", "/v1/me"),
  updateMe: (changes: ProfileUpdate) => apiRequest<Me>("PATCH", "/v1/me", changes),

  // Practice (Phase 2)
  nextQuestion: (roundType?: RoundType) =>
    apiRequest<Question>("GET", `/v1/questions/next${roundType ? `?round_type=${roundType}` : ""}`),
  createSession: (roundType: RoundType) =>
    apiRequest<Session>("POST", "/v1/sessions", { round_type: roundType }),
  submitAnswer: (sessionId: string, questionId: string, transcript: string) =>
    apiRequest<Answer>("POST", `/v1/sessions/${sessionId}/answers`, {
      question_id: questionId,
      transcript,
    }),
  completeSession: (sessionId: string) =>
    apiRequest<Session>("POST", `/v1/sessions/${sessionId}/complete`),
  listSessions: () => apiRequest<Session[]>("GET", "/v1/sessions"),
  usage: () => apiRequest<Usage>("GET", "/v1/usage"),
};
