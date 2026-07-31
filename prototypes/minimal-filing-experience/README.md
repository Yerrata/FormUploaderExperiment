# PROTOTYPE — minimal Form III filing experience

## Question

Which desktop layout makes the complete Yeratta Resort filing workflow easiest to understand and operate when passport and visa extraction is temporarily replaced by deterministic dummy JSON?

This is a throwaway, read-only usability prototype. It contains fictional data and simulates WhatsApp, extraction, government submission, acknowledgements, session renewal, and departure updates. It performs no real external action.

## One command

```bash
python -m http.server 8080 --directory prototypes/minimal-filing-experience
```

Then open:

- `http://localhost:8080/?variant=A` — action-first workspace
- `http://localhost:8080/?variant=B` — chronological journey
- `http://localhost:8080/?variant=C` — exception-first board

Use the floating arrow switcher or keyboard left/right arrows to compare variants. Select a fictional case and press **Simulate next step** to move it through guest correction, ready, submission, acknowledgement, departure, and reconciliation states.

