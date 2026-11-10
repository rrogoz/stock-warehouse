# Runbook: Switch on protection

Numbered steps only. Rafal does these by hand: agents are not admins ([ADR-008](../adr/0008-ci-cd-and-release.md), [ADR-011](../adr/0011-agent-orchestration.md)). Code owners are in [`.github/CODEOWNERS`](../../.github/CODEOWNERS).

## When to use

Once, right after the SW-9 pull request merges, and again to check the settings if a gate seems not to hold.

## Steps

1. **Merge settings.** Settings, General, Pull Requests: untick "Allow merge commits" and "Allow rebase merging"; keep "Allow squash merging" with default message "Pull request title"; tick "Always suggest updating pull request branches" and "Automatically delete head branches". Leave "Allow auto-merge" off until M2.
2. **Ruleset on main.** Settings, Rules, Rulesets, New ruleset, New branch ruleset:
   1. Name `main`, Enforcement status **Active**, Bypass list **empty**.
   2. Target branches: Add target, Include default branch.
   3. Keep "Restrict deletions" and "Block force pushes" ticked.
   4. Tick "Require a pull request before merging": Required approvals **1**; tick "Dismiss stale pull request approvals when new commits are pushed", "Require review from Code Owners", "Require approval of the most recent reviewable push" and "Require conversation resolution before merging"; Allowed merge methods **Squash** only.
   5. Tick "Require status checks to pass" and "Require branches to be up to date before merging"; Add checks, source GitHub Actions: `format, lint, types, tests, SQL style`, `docs, no real data, secrets`, `docker build`, `change conventions`.
   6. Create.
3. **Environments.** Settings, Environments, for each of `agent-review`, `prod-run`, `prod-release`: Deployment branches and tags, Selected branches and tags, Add rule `main`; untick "Allow administrators to bypass configured protection rules". On `prod-release` also tick "Required reviewers" and add `rrogoz`.
4. **Actions.** Settings, Actions, General: Workflow permissions **Read repository contents and packages permissions**; untick "Allow GitHub Actions to create and approve pull requests"; fork pull request workflows: **Require approval for all external contributors**.
5. **Pause switch.** Settings, Secrets and variables, Actions, Variables, New repository variable: `SW_AGENTS_PAUSED` = `false`.
6. **Secret scanning.** Settings, Advanced Security: Secret Protection and Push protection are on.
7. **Claude GitHub App.** github.com/settings/installations, Claude, Configure: repository access includes `rrogoz/stock-warehouse`.

## How to check it worked

- A test push straight to main is refused, also for Rafal.
- An open pull request shows the four checks as Required and "Review required" from a code owner.
- Agents run as described in [run an agent](run-an-agent.md); `rrogoz-sw-review` has Write access (Settings, Collaborators), so its approval counts.
