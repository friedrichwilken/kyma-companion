# Custom Review Focus

## Security Gate for `pull_request_target` Workflows

A `pull_request_target` workflow runs with the secrets and token of the base repository, also for pull requests from forks. Any job in such a workflow that checks out pull request code or uses secrets **must** be gated by the `e2e` environment, which requires codeowner approval before the job starts. Flag a violation if any of the following are true:

1. **Missing environment gate** — A job checks out pull request code or uses secrets, but neither declares `environment: e2e` itself nor depends (directly or transitively through `needs`) on a job that does. A job that calls a reusable workflow cannot declare an environment, so it must either depend on a gate job or call a reusable workflow whose jobs declare `environment: e2e`.
2. **Environment is not a literal** — The gate is written as an expression, for example `environment: ${{ matrix.env_name }}`. An expression can evaluate to an empty value for some matrix legs or inputs, and those runs are then not gated. The value must be the literal `e2e`.
3. **Checkout by branch name** — The pull request code is checked out with `github.event.pull_request.head.ref`, or that value is passed on as the ref to check out. A branch can move after the approval was given. The checkout must use `github.event.pull_request.head.sha`.
4. **Unsafe checkout outside a gated job** — `allow-unsafe-pr-checkout: true` is set in a job that is not gated as described in 1, or it is set without the `# Safe: ...` comment that names the gate.
5. **Gate removed or weakened** — A PR modifies an existing `pull_request_target` workflow and removes the `environment: e2e` line, replaces it with an expression, removes a `needs` dependency on the gate job, or adds a job that is not covered by the gate.
6. **Wrong trigger** — A workflow that only runs tests or linting and needs no secrets uses `pull_request_target`. It belongs on `pull_request`.

### Expected Pattern

A job that checks out and runs pull request code:

```yaml
on:
  pull_request_target:

jobs:
  integration-test:
    runs-on: ubuntu-latest
    environment: e2e
    steps:
      - name: Checkout code
        uses: actions/checkout@v7
        with:
          ref: ${{ github.event.pull_request.head.sha }}
          repository: ${{ github.event.pull_request.head.repo.full_name }}
          # Safe: the `environment: e2e` gate above requires codeowner approval before
          # this job runs, so secrets are never exposed to unreviewed fork code.
          allow-unsafe-pr-checkout: true
```

A gate job in front of jobs that cannot declare an environment themselves, such as a call to a reusable workflow:

```yaml
jobs:
  gate:
    runs-on: ubuntu-latest
    environment: e2e
    steps:
      - run: echo "environment gate passed"

  # Every subsequent job must include `needs: gate`
  # (directly, or transitively via another job that needs gate)
  build:
    needs: gate
    uses: kyma-project/test-infra/.github/workflows/image-builder.yml@main
```

### Scope

- Applies to **new, modified, and existing** workflow files under `.github/workflows/`.
- Only workflows with `pull_request_target` in their `on:` trigger are in scope.
- Workflows using only `pull_request`, `push`, `schedule`, or `workflow_dispatch` are **not** in scope.

---

## Exception Leakage in Logging and HTTP Responses

Flag any code that embeds exception objects in log messages or returns exception details in HTTP responses.

### Rule 1 — No explicit exception interpolation in log calls

`logger.exception(...)` already captures and appends the full traceback automatically. `logger.error(...)` should only be used for simple messages without exception context; if exception context is needed, use `logger.exception(...)` instead. Embedding the exception in the message string is redundant and produces duplicate or incomplete error output.

**Flag any of the following patterns:**

```python
# BAD — redundant interpolation in logger.exception
logger.exception(f"Something failed: {e}")
logger.exception(f"Something failed: {str(e)}")
logger.exception("Something failed: %s", e)

# BAD — embedding exception in logger.error when logger.exception should be used
logger.error(f"Something failed: {e}")
logger.error(f"Something failed: {str(e)}")
logger.error("Something failed: %s", e)
```

**Expected pattern:**

```python
# GOOD — clean message, traceback appended automatically
logger.exception("Something failed")

# GOOD — logger.error with a plain message (no exception context needed)
logger.error("Validation failed for field X")
```

### Rule 2 — No exception details in HTTP response bodies

Exception messages must not be forwarded to HTTP clients. Leaking internal error details (stack traces, exception strings, library internals) can expose sensitive implementation information.

**Flag any of the following patterns:**

```python
# BAD — exception forwarded to client
raise HTTPException(status_code=500, detail=str(e))
raise HTTPException(status_code=500, detail=f"Error: {e}")
return JSONResponse(status_code=500, content={"error": str(e)})
```

**Expected pattern:**

```python
# GOOD — generic message to client, full detail captured in logs
logger.exception("Unexpected error processing request")
raise HTTPException(status_code=500, detail="Internal server error")
```

### Scope

- Applies to all Python source files (`.py`) in the PR diff.
- Both new code and modifications to existing code are in scope.
- Test files are **not** in scope.
