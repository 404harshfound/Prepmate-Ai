import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type SubmitEvent } from "react";
import { Link } from "react-router";

import { PageStatus } from "../components/PageStatus";
import { Wordmark } from "../components/Wordmark";
import { api, ApiError, type ExperienceLevel, type Me } from "../lib/api";
import { supabase } from "../lib/supabase";

const LEVELS: { value: ExperienceLevel; label: string; hint: string }[] = [
  { value: "student", label: "Student", hint: "Preparing for campus placements" },
  { value: "fresher", label: "Fresher", hint: "Graduated, looking for a first job" },
  { value: "experienced", label: "Experienced", hint: "Already working, switching roles" },
];

function signOut() {
  void supabase.auth.signOut();
}

export function Home() {
  const query = useQuery({ queryKey: ["me"], queryFn: api.me });

  if (query.isPending) return <PageStatus title="Opening your sheet" />;

  if (query.isError) {
    const error = query.error;
    if (error instanceof ApiError && error.isAuthError) {
      signOut();
      return <PageStatus title="Your session has ended" />;
    }
    return (
      <PageStatus title="We couldn't load your profile">
        <p>{error.message}</p>
        {error instanceof ApiError && error.requestId ? (
          <p className="mt-2 text-pencil">Reference: {error.requestId}</p>
        ) : null}
        <button type="button" className="btn btn-primary mt-6" onClick={() => void query.refetch()}>
          Try again
        </button>
      </PageStatus>
    );
  }

  return <Workspace me={query.data} />;
}

function Workspace({ me }: { me: Me }) {
  const firstName = me.profile.display_name?.split(" ")[0];

  return (
    <div className="min-h-dvh">
      <header className="border-b border-rule">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3">
          <Wordmark />
          <button type="button" className="btn btn-quiet" onClick={signOut}>
            Sign out
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-10">
        <div className="sheet pr-4">
          <h1 className="sheet-title">{firstName ? `Hello, ${firstName}.` : "Hello."}</h1>
          <p className="rules-1 max-w-xl">
            Tell us what you're preparing for, so the questions match the job you want.
          </p>
        </div>

        <ProfileForm me={me} />

        <section aria-labelledby="practice-heading" className="mt-14 border-t border-rule pt-8">
          <h2 id="practice-heading" className="font-display text-2xl font-medium text-ink">
            Practice
          </h2>
          <p className="mt-2 max-w-xl text-pencil">
            Answer real placement questions and get scored feedback on structure, clarity and depth.
            Your profile above decides which questions you'll get first.
          </p>
          <Link to="/practice" className="btn btn-primary mt-4">
            Start practising
          </Link>
        </section>
      </main>
    </div>
  );
}

function ProfileForm({ me }: { me: Me }) {
  const queryClient = useQueryClient();
  const [displayName, setDisplayName] = useState(me.profile.display_name ?? "");
  const [targetRole, setTargetRole] = useState(me.profile.target_role ?? "");
  const [level, setLevel] = useState<ExperienceLevel>(me.profile.experience_level);

  const save = useMutation({
    mutationFn: api.updateMe,
    onSuccess: (updated) => {
      queryClient.setQueryData(["me"], updated);
    },
  });

  function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    const changes: Parameters<typeof api.updateMe>[0] = { experience_level: level };
    if (displayName.trim()) changes.display_name = displayName.trim();
    if (targetRole.trim()) changes.target_role = targetRole.trim();
    save.mutate(changes);
  }

  return (
    <form className="mt-10 grid max-w-xl gap-6" onSubmit={submit} aria-labelledby="profile-heading">
      <h2 id="profile-heading" className="font-display text-2xl font-medium text-ink">
        Your profile
      </h2>

      <div>
        <label htmlFor="display-name" className="field-label">
          Name
        </label>
        <input
          id="display-name"
          className="field-input"
          autoComplete="name"
          maxLength={80}
          value={displayName}
          onChange={(event) => {
            setDisplayName(event.target.value);
          }}
        />
      </div>

      <div>
        <label htmlFor="target-role" className="field-label">
          Role you're preparing for
        </label>
        <input
          id="target-role"
          className="field-input"
          maxLength={80}
          placeholder="For example, Backend SDE or Data Analyst"
          value={targetRole}
          onChange={(event) => {
            setTargetRole(event.target.value);
          }}
        />
      </div>

      <fieldset>
        <legend className="field-label">Where you are now</legend>
        <div className="mt-1 grid gap-2">
          {LEVELS.map((option) => (
            <label
              key={option.value}
              className="flex cursor-pointer items-start gap-3 rounded-[3px] border border-rule bg-paper-raised px-3 py-2.5 has-[:checked]:border-ink"
            >
              <input
                type="radio"
                name="experience-level"
                value={option.value}
                checked={level === option.value}
                onChange={() => {
                  setLevel(option.value);
                }}
                className="mt-1.5 accent-[var(--ink)]"
              />
              <span>
                <span className="block font-semibold">{option.label}</span>
                <span className="block text-sm text-pencil">{option.hint}</span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <div className="flex flex-wrap items-center gap-4">
        <button type="submit" className="btn btn-primary" disabled={save.isPending}>
          {save.isPending ? "Saving profile" : "Save profile"}
        </button>
        <p role="status" aria-live="polite" className="text-sm">
          {save.isSuccess ? <span className="text-success">Profile saved.</span> : null}
          {save.isError ? <span className="text-danger">{save.error.message}</span> : null}
        </p>
      </div>
    </form>
  );
}
