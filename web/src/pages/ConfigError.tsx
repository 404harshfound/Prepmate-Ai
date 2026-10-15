import { PageStatus } from "../components/PageStatus";

/** Shown instead of the app when a deploy is missing its settings. */
export function ConfigError({ problems }: { problems: string[] }) {
  return (
    <PageStatus title="PrepMate isn't set up correctly">
      <p>This copy of the app is missing settings, so sign-in is turned off.</p>
      {import.meta.env.DEV ? (
        <ul className="mt-4 list-disc pl-5 text-pencil">
          {problems.map((problem) => (
            <li key={problem}>{problem}</li>
          ))}
        </ul>
      ) : null}
    </PageStatus>
  );
}
