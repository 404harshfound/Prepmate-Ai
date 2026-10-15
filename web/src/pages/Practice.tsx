import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type SubmitEvent } from "react";
import { Link } from "react-router";

import { PageStatus } from "../components/PageStatus";
import { Wordmark } from "../components/Wordmark";
import {
  api,
  ApiError,
  type Answer,
  type Question,
  type RoundType,
  type Session,
} from "../lib/api";
import { supabase } from "../lib/supabase";

const ROUND_LABELS: Record<RoundType, string> = {
  hr: "HR",
  behavioural: "Behavioural",
  technical: "Technical",
  aptitude: "Aptitude",
};

const DIFFICULTY_LABELS: Record<number, string> = {
  1: "Easy",
  2: "Medium",
  3: "Hard",
};

function signOut() {
  void supabase.auth.signOut();
}

// ------------------------------------------------------------------ main

export function Practice() {
  const [session, setSession] = useState<Session | null>(null);
  const [roundType, setRoundType] = useState<RoundType>("hr");

  if (!session) {
    return <RoundPicker roundType={roundType} setRoundType={setRoundType} onStart={setSession} />;
  }

  return <ActiveSession session={session} onDone={() => setSession(null)} />;
}

// ------------------------------------------------------------------ round picker

function RoundPicker({
  roundType,
  setRoundType,
  onStart,
}: {
  roundType: RoundType;
  setRoundType: (r: RoundType) => void;
  onStart: (s: Session) => void;
}) {
  const queryClient = useQueryClient();
  const usage = useQuery({ queryKey: ["usage"], queryFn: api.usage });

  const start = useMutation({
    mutationFn: () => api.createSession(roundType),
    onSuccess: (created) => {
      void queryClient.invalidateQueries({ queryKey: ["sessions"] });
      onStart(created);
    },
  });

  return (
    <div className="min-h-dvh">
      <Header />
      <main className="mx-auto max-w-4xl px-4 py-10">
        <div className="sheet pr-4">
          <h1 className="sheet-title">Start practising</h1>
          <p className="rules-1 max-w-xl">
            Pick a round type and answer one question at a time. You'll get scored feedback on
            structure, relevance, clarity and depth.
          </p>
        </div>

        <div className="mt-10 max-w-xl">
          <fieldset>
            <legend className="field-label">Round type</legend>
            <div className="mt-1 grid gap-2">
              {(Object.keys(ROUND_LABELS) as RoundType[]).map((rt) => (
                <label
                  key={rt}
                  className="flex cursor-pointer items-center gap-3 rounded-[3px] border border-rule bg-paper-raised px-3 py-2.5 has-[:checked]:border-ink"
                >
                  <input
                    type="radio"
                    name="round-type"
                    value={rt}
                    checked={roundType === rt}
                    onChange={() => setRoundType(rt)}
                    className="accent-[var(--ink)]"
                  />
                  <span className="font-semibold">{ROUND_LABELS[rt]}</span>
                </label>
              ))}
            </div>
          </fieldset>

          {usage.data ? (
            <p className="mt-4 text-sm text-pencil">
              {usage.data.feedback_calls} / {usage.data.feedback_limit} feedback calls used today
            </p>
          ) : null}

          <button
            type="button"
            className="btn btn-primary mt-6"
            disabled={start.isPending}
            onClick={() => start.mutate()}
          >
            {start.isPending ? "Starting…" : `Start ${ROUND_LABELS[roundType]} round`}
          </button>

          {start.isError ? (
            <p className="mt-3 text-danger">{start.error.message}</p>
          ) : null}
        </div>

        <PastSessions />
      </main>
    </div>
  );
}

// ------------------------------------------------------------------ active session

function ActiveSession({ session, onDone }: { session: Session; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [answers, setAnswers] = useState<Answer[]>([]);

  const question = useQuery({
    queryKey: ["next-question", session.round_type],
    queryFn: () => api.nextQuestion(session.round_type as RoundType),
  });

  const submit = useMutation({
    mutationFn: (transcript: string) =>
      api.submitAnswer(session.id, question.data!.id, transcript),
    onSuccess: (answer) => {
      setAnswers((prev) => [...prev, answer]);
    },
  });

  const complete = useMutation({
    mutationFn: () => api.completeSession(session.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["sessions"] });
      void queryClient.invalidateQueries({ queryKey: ["usage"] });
      onDone();
    },
  });

  if (question.isPending) return <PageStatus title="Finding a question…" />;
  if (question.isError) {
    return (
      <PageStatus title="Couldn't load a question">
        <p>{question.error.message}</p>
        <button
          type="button"
          className="btn btn-primary mt-6"
          onClick={() => void question.refetch()}
        >
          Try again
        </button>
      </PageStatus>
    );
  }

  const latestAnswer = answers[answers.length - 1] ?? null;
  const showingFeedback = latestAnswer && latestAnswer.question_id === question.data.id;

  return (
    <div className="min-h-dvh">
      <Header />
      <main className="mx-auto max-w-4xl px-4 py-10">
        <div className="flex items-center gap-3 text-sm text-pencil">
          <span className="rounded bg-paper-raised px-2 py-0.5 font-semibold text-ink">
            {ROUND_LABELS[question.data.round_type as RoundType]}
          </span>
          <span>{question.data.topic}</span>
          <span>·</span>
          <span>{DIFFICULTY_LABELS[question.data.difficulty] ?? "Medium"}</span>
          <span className="ml-auto">{answers.length} answered</span>
        </div>

        <div className="sheet mt-6 pr-4">
          <h1 className="sheet-title">{question.data.prompt}</h1>
        </div>

        {showingFeedback ? (
          <FeedbackCard answer={latestAnswer} />
        ) : (
          <AnswerForm
            onSubmit={(transcript) => submit.mutate(transcript)}
            isPending={submit.isPending}
            error={submit.isError ? submit.error.message : null}
          />
        )}

        <div className="mt-8 flex gap-3">
          {showingFeedback ? (
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => void question.refetch()}
            >
              Next question
            </button>
          ) : null}
          <button
            type="button"
            className="btn btn-quiet"
            disabled={complete.isPending}
            onClick={() => complete.mutate()}
          >
            {complete.isPending ? "Finishing…" : "Finish session"}
          </button>
        </div>
      </main>
    </div>
  );
}

// ------------------------------------------------------------------ answer form

function AnswerForm({
  onSubmit,
  isPending,
  error,
}: {
  onSubmit: (transcript: string) => void;
  isPending: boolean;
  error: string | null;
}) {
  const [text, setText] = useState("");

  function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = text.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
  }

  return (
    <form className="mt-8" onSubmit={handleSubmit}>
      <label htmlFor="answer-text" className="field-label">
        Your answer
      </label>
      <textarea
        id="answer-text"
        className="field-input min-h-[10rem] resize-y"
        placeholder="Type your answer here…"
        maxLength={8000}
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={isPending}
      />
      <div className="mt-1 text-right text-xs text-pencil">{text.length} / 8000</div>

      <button type="submit" className="btn btn-primary mt-4" disabled={isPending || !text.trim()}>
        {isPending ? "Getting feedback…" : "Submit answer"}
      </button>

      {error ? <p className="mt-3 text-danger">{error}</p> : null}
    </form>
  );
}

// ------------------------------------------------------------------ feedback card

function FeedbackCard({ answer }: { answer: Answer }) {
  if (answer.feedback_status === "failed") {
    return (
      <div className="mt-8 rounded border border-danger/30 bg-paper-raised p-5">
        <p className="font-semibold text-danger">Feedback unavailable</p>
        <p className="mt-1 text-sm text-pencil">
          The AI couldn't score this answer. Your daily quota was not used. Try again with the next
          question.
        </p>
      </div>
    );
  }

  if (!answer.scores || !answer.feedback) return null;

  const { scores, feedback } = answer;

  return (
    <div className="mt-8 space-y-6">
      {/* Score grid */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <ScoreBadge label="Structure" value={scores.structure} />
        <ScoreBadge label="Relevance" value={scores.relevance} />
        <ScoreBadge label="Clarity" value={scores.clarity} />
        <ScoreBadge label="Depth" value={scores.depth} />
        <ScoreBadge label="Overall" value={scores.overall} highlight />
      </div>

      {/* Overall assessment */}
      <div className="rounded border border-rule bg-paper-raised p-4">
        <p className="font-semibold text-ink">Assessment</p>
        <p className="mt-1">{feedback.overall}</p>
      </div>

      {/* Improvements */}
      {feedback.improvements.length > 0 ? (
        <div>
          <p className="font-semibold text-ink">How to improve</p>
          <ul className="mt-2 space-y-3">
            {feedback.improvements.map((imp, i) => (
              <li key={i} className="rounded border border-rule bg-paper-raised p-4">
                <p className="text-sm font-semibold text-danger">{imp.issue}</p>
                <p className="mt-1 text-sm">{imp.suggestion}</p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {answer.model ? (
        <p className="text-xs text-pencil">Scored by {answer.model}</p>
      ) : null}
    </div>
  );
}

function ScoreBadge({
  label,
  value,
  highlight,
}: {
  label: string;
  value: number;
  highlight?: boolean;
}) {
  const colour = value >= 7 ? "text-success" : value >= 4 ? "text-ink" : "text-danger";
  return (
    <div
      className={`rounded border p-3 text-center ${highlight ? "border-ink bg-paper-raised" : "border-rule"}`}
    >
      <p className="text-xs text-pencil">{label}</p>
      <p className={`text-xl font-bold ${colour}`}>{value}</p>
    </div>
  );
}

// ------------------------------------------------------------------ past sessions

function PastSessions() {
  const sessions = useQuery({ queryKey: ["sessions"], queryFn: api.listSessions });

  if (!sessions.data || sessions.data.length === 0) return null;

  return (
    <section className="mt-14 border-t border-rule pt-8">
      <h2 className="font-display text-2xl font-medium text-ink">Past sessions</h2>
      <div className="mt-4 space-y-2">
        {sessions.data.map((s) => (
          <div
            key={s.id}
            className="flex items-center justify-between rounded border border-rule bg-paper-raised px-4 py-3"
          >
            <div>
              <span className="font-semibold">{ROUND_LABELS[s.round_type]}</span>
              <span className="ml-2 text-sm text-pencil">
                {s.answer_count} question{s.answer_count !== 1 ? "s" : ""}
              </span>
            </div>
            <div className="text-right">
              {s.average_score !== null ? (
                <span className="font-bold text-ink">{s.average_score}/10</span>
              ) : (
                <span className="text-sm text-pencil">—</span>
              )}
              <p className="text-xs text-pencil">
                {new Date(s.started_at).toLocaleDateString()}
              </p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ------------------------------------------------------------------ shared header

function Header() {
  return (
    <header className="border-b border-rule">
      <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3">
        <Link to="/">
          <Wordmark />
        </Link>
        <div className="flex gap-2">
          <Link to="/" className="btn btn-quiet">
            Home
          </Link>
          <button type="button" className="btn btn-quiet" onClick={signOut}>
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}
