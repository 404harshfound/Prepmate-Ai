import { Link } from "react-router";

import { PageStatus } from "../components/PageStatus";

export function NotFound() {
  return (
    <PageStatus title="This page isn't on the sheet">
      <p>The link may be old or mistyped.</p>
      <Link to="/" className="btn btn-primary mt-6">
        Go to PrepMate
      </Link>
    </PageStatus>
  );
}
