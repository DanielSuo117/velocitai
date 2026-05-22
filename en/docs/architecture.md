# Project Architecture

## POM Layering

```
┌─────────────────────────────────────────────┐
│                  tests/ Test Layer            │
│  Split by role: test_<role>_flow.py          │
│  Each test class inherits Base (or Role-Base) │
├─────────────────────────────────────────────┤
│                  pages/ Page Object Layer     │
│  BasePage ← LoginPage ← LandingPage ← ...    │
├─────────────────────────────────────────────┤
│                  config/ Config Layer         │
│  URLs, tokens, browser params switch by env  │
├─────────────────────────────────────────────┤
│                  conftest.py Fixture Layer    │
│  browser → context → page → Role-specific base │
└─────────────────────────────────────────────┘
```

## Roles and Context Sharing

| Role | Base Class | Context Scope | Start Page |
|------|------|--------------|---------|
| (append new roles here) | | | |

## Decision Tree

See [architecture skill](../skills/architecture/SKILL.md)
