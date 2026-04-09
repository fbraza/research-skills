---
title: "Implement pip-installable ultraplot publication plotting package"
status: open
tags: [plotting, ultraplot, single-cell, publication, packaging]
created: 2026-04-09
---

## Main idea
Create a pip-installable Python plotting package for publication-ready single-cell figures built on ultraplot, so agents can call stable high-level plotting functions instead of re-implementing figure code in each project.

## GitHub issue
Pending — repository not yet specified.
Issue link: TBD

## Notes
- Centralize style defaults, palettes, sizing, export helpers, and figure QC checks
- Expose a small stable API for common publication plots (UMAP, feature plots, violin, heatmap, volcano)
- Update `scientific-visualization` references so they become API-oriented usage docs + figure specs
- Keep the skill as guidance/specification, and the package as the implementation agents call
