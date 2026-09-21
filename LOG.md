# Project Work Log

### Day 1: Project Setup, Architecture & The Hard Problem
- **What we did**: Built the complete GiveNaija backend architecture following strict 3-tier layering (routers -> services -> models/db). Implemented all models, JWT authentication, RBAC dependencies, atomic transaction boundaries, Redis caching with write invalidation, Server-Sent Events (SSE) live ticker, HMAC-SHA256 signed payment webhook, and 26 automated pytest tests including all 5 hard-problem tests.
- **What broke**: In initial test execution, lifespan attempted to connect to localhost:5432 with default Docker passwords while an existing PostgreSQL 18 Windows service was running natively on the host, causing an operational error.
- **What we learnt**: Tests must strictly isolate test environments using `APP_ENV=testing` and in-memory/test engines so that test suites run completely independent of host machine infrastructure.
- **What is next**: Final rehearsals for viva examination, demo walkthrough, and deployment.
- **Who did what**: Anthony & Victor (Team Mighty Spark) designed the schema, implemented the hard problem constraints, and wrote the acceptance test suite.
