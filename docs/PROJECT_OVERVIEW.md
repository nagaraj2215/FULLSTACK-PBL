# Project Overview

This Django project is a health monitoring web app with account pages, a user dashboard, physical health scoring, mental health scoring, and suggestion pages for exercise, diet, sleep, and stress management.

## Main App Areas

- `fullstack_prj/hello/views.py` contains the page handlers and scoring logic.
- `fullstack_prj/hello/urls.py` maps app route names to views.
- `fullstack_prj/templates/` contains the HTML templates used by the app.
- `fullstack_prj/static/style.css` contains shared static styling.
- `fullstack_prj/hello/tests.py` contains focused tests for login-required pages, scoring history, resets, and suggestion flows.

## Data Notes

The app stores registered users and score history in Django models. Physical and mental history are saved per user, so graph reset actions should only clear the logged-in user's own history.
