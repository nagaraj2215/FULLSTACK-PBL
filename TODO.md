# TODO

- [x] Update `physical_health_tracker` view to pass `history_json` into template.
- [x] Replace `templates/physical_tracker.html` UI with a Health Progress Graph page (Chart.js line chart) using `history_json`.
- [x] Add Django tests for physical and mental score history flows.
- [ ] Sanity check in browser: open `/physical/`, submit once, then open `/physical-tracker/` to confirm chart shows and labels render.
- [ ] Sanity check in browser: open `/mental/`, submit once, and confirm the latest, best, average, and check-in count update.

