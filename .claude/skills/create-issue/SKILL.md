---
name: create-issue
description: File a GitHub issue on this repo with a plain two-sentence summary on top, the six-section body written for its two readers and run through the hemingway and humanizer skills, and the required labels. Use whenever asked to file, create, or open an issue (a bug, a feature, a decision, or a task), or to convert findings into issues.
---

# Creating an issue

Same flow as bluebird's `create-issue` skill, with this repo's areas and gates.

## Step 1: confirm the request

Never file an issue the maintainer did not ask for. If the idea is yours,
propose it and get an explicit yes first. This includes follow-up issues
discovered mid-task.

## Step 2: keep technical names exact

- File paths, functions, API paths, env vars and label names are technical
  names. Write them exactly as they appear in the code.
- Quote UI strings, commands and code verbatim.
- Use one name for one thing. Do not alternate synonyms.
- Use no em dashes.

## Step 3: open with a plain summary

The body opens with a `## Summary` heading, the summary, and a horizontal
rule (`---`) that closes it off from the six sections below. It is the only
part of the issue most readers see on the board.

- Two sentences, three at most. No bullets, no file paths, no code spans.
- Sentence one: what is wrong, in words someone who lifts and wears the watch
  would follow. Sentence two: what changes when the issue is closed. An
  optional third: why it matters now.
- Write it last, after the six sections, so it summarizes what is in the
  issue. Then place it first.

## Step 4: use the six sections, in this order

1. **Problem**: what is wrong or missing, with verified facts. State what
   was observed and how (a run's log, a probe, a screenshot).
2. **Proposed Solutions**: lettered options, each with Good and Bad bullets,
   ending in one recommendation line. State a settled decision as settled,
   with who decided and when.
3. **Implementation Plan**: numbered imperative steps. Name the file and the
   function for each step.
4. **Acceptance Criteria**: plain bullets a reviewer can verify. Include the
   repo gates that apply: the tests pass in CI
   (`PYTHONPATH=src python3 -m unittest discover -s tests`); the README's
   table of variables and "What it does not do" match the behavior; a change
   to env vars, secrets or the schedule ships with a Kubernetes-Manifests PR
   for `misc/hevy2garmin`.
5. **Notes for an AI agent**: the guardrails and traps an implementing agent
   must know. Examples: the Hevy session on the volume is the only valid
   copy, never refresh it from a second process; everything Garmin goes
   through hevy2garmin, never a second Garmin login; `--dry-run` must stay
   write-free; the private Hevy endpoint is undocumented, so log what you
   depend on.
6. **Notes for a human**: the decisions that are the maintainer's, the
   provenance (a run's log, a probe, a conversation), the risks, and any
   open questions.

Optional extra sections (for example, Out of scope or Measured) go between
Acceptance Criteria and the Notes.

## Step 5: write for the reader, then cut, then strip the AI tells

An issue has two readers: a person on the board who may not read code, and
the agent that implements it. Each section opens with its conclusion; the
evidence follows. One idea per sentence. Explain a term the first time.

Run two passes over the whole body once the summary is placed first:

1. `hemingway` first. Take its trimmed version. Put back any cut that dropped
   a fact, a number or a qualifier that changes the meaning.
2. `humanizer` second, in embedded mode, on the trimmed text. Apply every
   fix it returns.

After both, check the technical names against the draft. An edit to an
existing issue takes the same steps before `gh issue edit`.

## Step 6: title

One short statement of the problem or the task, with no conventional-commit
prefix. Example: "A watch loses the workout every time a routine changes".

## Step 7: labels

Always add labels when you create the issue:

- Exactly one priority: `P1` (do next), `P2` (soon), or `P3` (someday).
- `PM` (Priority Manual) only when the maintainer asks for it. It is one more
  label, not a replacement for the priority.
- The current Claude Code session ID, always. The ID is the UUID directory
  above `scratchpad` in the session's scratchpad path. Create the label first
  when it does not exist (the description must stay under 100 characters):
  `gh label create <uuid> --color 5ec3f7 --description "Filed in Claude Code session <uuid> (<date> <topic>)"`.
- Every area that applies: `hevy` (the private program endpoint, the public
  API, the session), `garmin` (Garmin Connect, device messages, the watch),
  `hevy2garmin` (the dashboard and its database), `ci`, `kubernetes`, `ux`,
  `security`.
- One type: `bug`, `enhancement`, `documentation`, or `question`. A decision
  the maintainer has to make is a `question`.

## Step 8: verify before you write

- Verify file references against the current branch before you state them.
  Name the file and the function rather than a line number.
- Name related issues by number, and state a blocking relation explicitly.
