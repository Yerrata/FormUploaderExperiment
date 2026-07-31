# Issue tracker: GitHub

Issues and planning artifacts for this repository live as GitHub Issues.

## Conventions

- Use the connected GitHub application for issue and pull-request operations where available.
- Use the `gh` CLI for native relationships or GitHub Actions details not exposed by the application.
- Pull requests are not treated as feature-request or triage tickets.

## Wayfinding operations

The Wayfinder map is one issue labelled `wayfinder:map`. Decision tickets are child issues labelled with one of:

- `wayfinder:research`
- `wayfinder:prototype`
- `wayfinder:grilling`
- `wayfinder:task`

Use native GitHub sub-issue and dependency relationships when available. Otherwise, link tickets from the map and record `Part of <map>` and `Blocked by: <ticket>` in issue bodies.

An open, unassigned, unblocked child is on the frontier. Claim a ticket by assigning it before working. Resolve it with an answer comment, close it, and add a one-line linked gist to the map's Decisions so far section.
