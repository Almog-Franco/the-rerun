# The Rerun

Senior QA Engineer, data team. Take-home exercise. **Three hours.**

## The scenario

You have joined the data team of an exposure-management platform as the person
who leads quality for the team. Security scanners deliver findings to us as
hourly NDJSON batches. An ingestion pipeline normalises each batch, appends it
to a sighting history, updates one row per finding, and refreshes a daily
rollup that every dashboard and export reads from.

Five developers own this pipeline. They write most of their code and most of
their tests with AI assistants. The pipeline is a year old and runs hourly in
production. A customer is about to consume the rollup for compliance
reporting, and nobody has reported a bug.

Your job is not to test everything yourself. It is to understand the system,
decide what this team has to check, and give the team tools that do the
checking. `docs/CONTRACT.md` lists the six guarantees the pipeline claims.
Treat the contract as the specification, not the code.

Use AI tools for everything, as you would on the job. Send only what you can
explain.

## What you have

- Twelve batches in `raw/`, about 28,000 records, three scanner sources with
  three payload shapes
- The pipeline in `pipeline/`, readable
- A serving API on `:8080` and a dashboard at `/`
- `docs/CONTRACT.md`, the six guarantees
- An example agent in `.claude/agents/status-reporter.md`
- `tests/conftest.py` with working fixtures, in case you or your agent want
  checks in code. No tests are required.

Four commands, after the setup in `README.md`:

```bash
pipeline reset
pipeline run --batch B03
pipeline run --all
pipeline status
```

## Your task

| | | | |
| --- | --- | --- | --- |
| 1 | **Understand the system** | Draw it: the stages a record passes through, the tables, and what moves between them. Mark where each of the six guarantees could break. One page. | 40 min |
| 2 | **Find out what matters** | Run the pipeline in ways production would: repeat a batch, change the order, deliver one late, compare with the raw files. Prove the three risks you consider most serious for the customer. | 50 min |
| 3 | **Write the quality plan** | One page for the team: what has to be checked, in what order, where and when each check runs, and who or what runs it. | 30 min |
| 4 | **Build one agent** | An agent that helps this team with the quality of the pipeline. What it does is your decision. | 45 min |

The times are a suggestion and leave fifteen minutes for setup.

## The agent

Build one agent that helps this team with the quality of this pipeline.
**What it does is your decision**, and the choice is part of what we look at:
pick the job where an agent would help the team most.

Whatever it does, your agent must:

1. **Work on its own.** Given nothing but this repository, it decides what to
   run and runs it.
2. **Prove what it reports by running things.** It may read the source, but a
   conclusion needs a run that demonstrates it.
3. **Be able to report that nothing is wrong.** An agent that always finds a
   problem is as wrong as one that never does.
4. **Leave the pipeline code untouched.** It may reset and reload the database
   freely.
5. **End with a short, fixed reply format that you define:** its conclusion,
   the commands it ran and the numbers it saw.

An agent here is a single instructions file. Copy the example in
`.claude/agents/status-reporter.md`, which is in Claude Code's format, and edit
it; you need no other knowledge of building agents. Any AI coding assistant
that can run shell commands can follow the same file, so use the one you have.

We will run your agent, unchanged, with Claude Code on macOS, on **versions of
the pipeline you have not seen**. Some of them behave differently from the one
in this bundle, so the agent has to find out what is true and not repeat what
you already know. The only version you can test it against is the one in this
bundle, so decide how you will know your agent is right.

## What to send back

| File | Contents |
| --- | --- |
| `SYSTEM.pdf`, `.png` or `.md` | The flowchart. Any tool, including pen and paper photographed. One page. |
| `EVIDENCE.md` | Your top three risks, most serious first. For each: the guarantee, the exact commands, the query, the numbers you saw, and what it means for the customer. **Maximum three.** |
| `QUALITY_PLAN.md` | One page. The checks this team needs, ordered by risk, with where each runs (in a pull request, nightly, in production) and who or what runs it. What you would deliberately not test. What you would ask the team before going further. How you would know, in three months, that quality improved. |
| `.claude/agents/<name>.md` | Your agent, named for what it does. |
| `AGENT_NOTES.md` | Why this agent and not another, how you checked that it is right, one complete reply from it, what you would not trust it with, and two more agents you would build for this team. Half a page. |

Send us the repository with your files added, however you like.

## How we read this

- **Do not fix the pipeline.** We want your judgement about it, not a patch.
- **Cite real numbers.** A claim without commands we can repeat costs you a
  lot. An honest "I ran out of time here" costs you nothing.
- **Short beats long.** One page means one page. A plan that could have been
  written without opening this repository tells us nothing.
- **Your understanding is what we assess.** AI can produce every file on this
  list. Send only what you can stand behind.
