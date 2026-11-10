# Runbook: Run an agent

Numbered steps only. Workflows and limits: [ADR-011](../adr/0011-agent-orchestration.md); what each role does: its skill in `.claude/skills/`.

## When to use

A story or pull request is ready for its next step: refine, spec, implement, review or fix.

## Steps

1. Actions, pick the workflow, Run workflow, branch **main** (other branches are refused):

   | Step | Workflow | Input | Default model | Turns, minutes |
   | --- | --- | --- | --- | --- |
   | Refine | `agent-refine` | story key | sonnet | 30, 15 |
   | Spec | `agent-spec` | story key | opus | 40, 20 |
   | Implement | `agent-implement` | story key, spec on main | sonnet | 80, 45 |
   | Review | `agent-review` | pull request number | opus | 40, 20 |
   | Fix | `agent-fix` | pull request number | haiku | 40, 30 |

2. Keep the default model; after two failed runs of a story, pick the next model up.
3. Run workflow. One run per story at a time; a second one waits for the first.
4. To stop every agent: Settings, Secrets and variables, Actions, Variables, set `SW_AGENTS_PAUSED` to `true`. Set it back to `false` to resume.
5. If a run stops on the usage limit, wait for the reset and run it again; nothing half-done can merge.

## How to check it worked

- The run is green and its log shows the agent's steps.
- Refine: verdict field and a `[refinement]` comment in Jira. Spec: a pull request on a `SW-NNN-…` branch and the story in Spec review. Implement: a pull request on a `SW-NNN-…` branch; the `story-status` workflow, not the agent, moves the story to In review (and to Awaiting release on merge). Review: a review by `rrogoz-sw-review`. Fix: new commits on the same pull request.
- The run's job summary lists the tool calls the agent was refused ("Refused tool calls"); start there when an agent did less than asked.
- Agents cannot push changes to `.github/workflows/`: the Claude GitHub App has no workflows permission. Such a story is built in a planning session from its approved spec, reviewed by `agent-review`, and merged by Rafal with the ruleset bypass.
- A refused run fails at the `limits` job with the reason: paused, not main, bad key, no spec on main, a fork, or three rejections already (the story then waits in Needs input).
