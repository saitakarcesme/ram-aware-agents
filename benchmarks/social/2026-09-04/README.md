# Benchmark social pack — 2026-09-04

This pack turns the repository's three benchmark stages into shareable, English-language material without combining incompatible protocols or presenting preliminary evidence as a universal result.

## What the full benchmark history says

### v1: useful failure, not a headline win

The original single-run, four-prompt pilot reduced average process-tree RSS by 30.7% and P95 RSS by 18.0%, but it increased peak RSS by 3.2% and active time by 13.3%. The two generated applications also diverged. This run is evidence that agent benchmarks need independent quality gates, alternating order, and repeated fresh projects—not evidence of a peak-memory improvement.

### v2: strongest quality-valid profile signal

Two fresh-project React/Playwright pairs passed the independent typecheck, component-test, 80-case desktop/mobile E2E, production-build, required-file, and process-leak gates. Compared with control, the 8 GB `AGENTS.md` profile produced these median changes:

| Metric | Median change |
|---|---:|
| Average process-tree RSS | -40.6% |
| P95 process-tree RSS | -57.0% |
| Peak process-tree RSS | -58.9% |
| Responsiveness probe P95 | -61.5% |
| Active time | +5.0% |

Browser-process peaks fell from 22–24 to 7, while minimum free system memory improved from 32–49% to 55–60%. This is the strongest result in the repository, but it remains preliminary because the protocol requires at least three quality-valid pairs.

### v3: `AGENTS.md` versus runtime enforcement

One Rust triple and one Python triple passed across control, `AGENTS.md`, and the measured hook candidate.

| Workload | Mechanism | Peak RSS vs control | Active time vs `AGENTS.md` |
|---|---|---:|---:|
| Rust workspace | `AGENTS.md` | -79.5% | baseline |
| Rust workspace | hook | -76.1% | -13.1% |
| Python data | `AGENTS.md` | -3.7% | baseline |
| Python data | hook | -12.3% | -8.8% |

The Rust result shows that both mechanisms can prevent a high-fan-out peak. The hook retained most of the peak reduction while finishing close to control time. Python showed a smaller memory opportunity, and the hook was again faster than `AGENTS.md`.

Neither browser triple was valid across all three arms: one control artifact failed a mobile E2E case, and one hook artifact missed Playwright server readiness. Those triples are excluded from performance claims. Their diagnostic data reinforce the central rule: lower RAM use is not a win when correctness fails.

## Decision supported by the evidence

Use `AGENTS.md` as the default project-wide planning layer. Add the hook when runtime shell serialization and worker ceilings are valuable. Do not replace the instruction file universally yet: the v3 sample is below its three-triple minimum, current hooks cannot cancel a starting subagent, and the hardened hook revision requires fresh repetitions.

Only an 8 GB M1 MacBook has been physically measured. Higher-memory tiers are conservative configurations, not benchmarked claims. Claude Code was not measured because its local OAuth session required reauthentication.

## Social assets

- [`01-browser-profile.png`](01-browser-profile.png) — strongest quality-valid profile/control result
- [`02-agents-vs-hook.png`](02-agents-vs-hook.png) — quality-valid v3 Rust and Python comparison
- [`tweet-thread.md`](tweet-thread.md) — copy-ready English X/Twitter thread
- [`claims.csv`](claims.csv) — compact source values used in the graphics

The editable SVG versions are included beside the PNG files. Regenerate them with:

```sh
python3 benchmarks/social/2026-09-04/render_social.py
```

## Source evidence

- [v1 historical pilot](../../codex-8gb-2026-09-01/README.md)
- [v2 quality-gated profile/control evidence](../../v2/evidence/8gb-m1-2026-09-02/README.md)
- [v3 control/AGENTS.md/hook evidence](../../v3/evidence/8gb-m1-2026-09-04/README.md)
