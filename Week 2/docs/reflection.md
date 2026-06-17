# Week 2 Reflection

Using a `.env` file keeps credentials out of source code, which protects secrets and makes it easy to change values per environment without editing the application itself. That is the core idea behind Factor III: configuration belongs outside the codebase.

Treating PostgreSQL as a backing service also improves portability. The FastAPI application talks to the database through SQLAlchemy, so the code depends on an interface rather than a specific server instance. If the database host or even the database engine changes later, the application can be updated with configuration instead of a rewrite.

Docker strengthens dev/prod parity because the same container image, database version, and initialization script can be used in both development and production-like environments. That reduces the gap between local testing and real deployment, which lowers the chance of environment-specific bugs.

In practice, these three ideas work together: configuration stays external, the database stays replaceable, and the container setup stays consistent. That makes the project easier to run, easier to share, and easier to maintain.