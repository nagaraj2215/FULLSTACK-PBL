# Testing Checklist

Use this checklist after changing views, URLs, templates, or models.

## Quick Checks

- Run `python fullstack_prj/manage.py check`.
- Run `python fullstack_prj/manage.py test hello`.
- Open the login, register, dashboard, physical, mental, exercise, and diet pages.
- Confirm named URL links still navigate to the expected pages.

## Behavior Checks

- Login-required pages should redirect anonymous users to `/login/`.
- Physical score submissions should appear in the progress tracker.
- Mental score submissions should appear in the mental score graph.
- Reset buttons should clear only the logged-in user's score history.
- Suggestion pages should adapt to the user's goal and latest score history.
