# ADR-002: Runtime and environments

- **Status:** Accepted
- **Date:** 2026-10-26

## Context

The platform must cost nothing, run on any host, and keep agents out of PROD by technical means.

## Decision

- **Two environments, DEV and PROD.** No permanent QA. A **pre-release check** replaces it: before Rafal approves a release, CI runs the release candidate end to end on the last 30 sessions of real data, in throwaway storage.
- **One Docker image and one command for both.** Only configuration differs (endpoint, bucket, credentials), passed as environment variables. No environment checks in code.
- **Where code runs.** PROD: a GitHub-hosted runner started by a scheduled GitHub Actions workflow every weekday evening. Checks and the pre-release check: GitHub runners. DEV: Rafal's machine in Docker Desktop, or an agent's sandbox.
- **Storage.** Two Cloudflare R2 buckets (`sw-dev`, `sw-prod`), each with its own key and a usage alert. Format: [ADR-003](0003-storage-and-physical-format.md).
- **Release gate.** Rafal approves a release in GitHub; the daily PROD run uses only the approved image version.
- **Secrets.** DEV keys in a git-ignored `.env`, with a committed `.env.example` holding names only. PROD keys as GitHub environment secrets, limited to main. Agents get DEV keys only. GitHub secret scanning and push protection.
- **Repositories.** The platform repository is public on GitHub Free, which gives protected branches, environments and required approval at zero cost. Stage 2 models live in a separate private repository.
- **Agents and PROD data.** Agents get no access to PROD data; they debug in DEV, or get read-only access on Rafal's explicit request.

## Consequences

- Zero cost for the platform; Cloudflare needs a card on file; agents run on Rafal's Claude subscription.
- A release is only ever an approved image tag, so rollback is approving the previous one.

## Options considered

- PROD in Docker on Rafal's machine: needs the machine on, isolates poorly from agents.
- An always-on free VM (Google, Oracle): server upkeep, reclaim risk.
- Google Cloud Run jobs: sound, kept as the fallback.
- A private repository on GitHub Free: loses protected branches, environments and approvals.

**Revisit if** the daily run outgrows free runners, scheduled runs prove unreliable, or data outgrows the 10 GB R2 free tier.
