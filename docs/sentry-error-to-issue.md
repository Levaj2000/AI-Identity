# Sentry error to GitHub issue bridge

The hourly `Sentry error to issue` workflow creates a GitHub issue for each recent,
unresolved Sentry error in an explicitly selected project. The issue contains a
stable Sentry ID and a link, not the event title, stack trace, request, or user
data. Only Sentry users with access to the project can inspect the error. Closed
GitHub issues are not recreated. The job limits new issues to 10 per run to
avoid a sudden backlog flooding the public issue tracker.

## Enable

1. Identify a Sentry project whose errors belong in **this public repository**.
   Do not select a project for the private platform, or one whose existence
   should not appear in the public issue tracker.
2. Create a Sentry internal integration token with `project:read` and
   `event:read` access to that project. In the repository Actions settings,
   save it as the secret `SENTRY_AUTH_TOKEN`.
3. In the repository Actions settings, set variables `SENTRY_ORG` and
   `SENTRY_PROJECT` to the Sentry organization and project slugs. Both
   variables must be set to enable the scheduled job. Do not put the token in
   a variable or commit it to the repository.
4. Run `Sentry error to issue` manually from the Actions tab, and confirm that
   its run log reports the number of created issues. With no recent errors it
   should report zero. The scheduled job runs hourly after that.

The workflow uses the built-in `GITHUB_TOKEN` with `issues:write`. The Sentry
token reads the project issue list only. Missing credentials or API failures
fail the job instead of silently dropping errors. It considers errors seen
within the last 14 days, including fatal errors, and does not reopen closed
GitHub issues. For older errors, investigate directly in Sentry. If the
repository is moved or made private, review the project selection and GitHub
Actions settings before reenabling the job.
