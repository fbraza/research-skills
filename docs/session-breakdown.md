# session-breakdown

## Summary

`session-breakdown` analyzes Pi session logs and presents an interactive view of recent activity, tokens, cost, and model usage.

## What it adds

- Command: `/session-breakdown`

## How it works

- Recursively scans session files under `~/.pi/agent/sessions`
- Aggregates the last 7, 30, and 90 days of usage
- Computes metrics such as:
  - sessions per day
  - messages per day
  - tokens per day
  - cost per day
  - model, cwd, day-of-week, and time-of-day breakdowns
- Renders a calendar-style heatmap and supporting tables in the TUI
- Falls back to a non-interactive text summary when no TUI is available

## Usage

Use this when you want to understand how you are using Pi over time and which models or projects dominate your usage.

## Examples

- `/session-breakdown`

## Files and state

- Reads session log files from `~/.pi/agent/sessions`
- No project-local persistent state

## Notes / caveats

- Metrics depend on what the underlying session logs contain
- Cost and token information may be incomplete for some sessions/providers
- Large session histories may take noticeable time to scan
