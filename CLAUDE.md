# svcdesk - agent instructions

Python 3.13 + FastAPI service in `src/svcdesk/`, composed via `docker-compose.yml` as `svcdesk` on port 8080. Contract: `docs/` in the course package (REQUIREMENTS, API, CHECKS). Decisions in `DECISIONS.md` (C1=wallclock, C2=immutable, C3=matrix) must match the running service. Verify with `.\itsmlab.ps1 verify 1`. Tags never move: each attempt gets a new tag.
