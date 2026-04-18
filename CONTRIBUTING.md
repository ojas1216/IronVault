# Contributing to Enterprise MDM System

Thank you for your interest in contributing! This document covers how to set up a development environment, coding standards, and the PR process.

---

## Development Setup

### Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | [python.org](https://python.org) |
| Node.js | 20+ | [nodejs.org](https://nodejs.org) |
| Docker | 24+ | [docker.com](https://docker.com) |
| Flutter | 3.19+ | [flutter.dev](https://flutter.dev) |
| Git | 2.40+ | [git-scm.com](https://git-scm.com) |

### First-Time Setup

```bash
# 1. Fork and clone
git clone https://github.com/ojas1216/employee-device-security.git
cd employee-device-security

# 2. Create .env
make env
# Edit .env and fill in secrets

# 3. Start dependencies (Postgres + Redis)
docker-compose up postgres redis -d

# 4. Install backend
cd backend
pip install -r requirements.txt
alembic upgrade head

# 5. Install dashboard
cd ../admin_dashboard
npm install

# 6. Run both in dev mode
make dev
```

---

## Project Structure

```
.
├── backend/          FastAPI Python API
├── mobile/           Flutter Android + iOS agent
├── desktop_agent/    Python Windows/macOS agent
├── admin_dashboard/  React TypeScript admin UI
├── ironvault/        IronVault anti-theft module
└── docs/             Documentation
```

---

## Coding Standards

### Python (Backend)

- **Formatter:** `black` (line length 100)
- **Linter:** `ruff`
- **Types:** Always annotate function signatures
- **Tests:** `pytest` with `pytest-asyncio` for async endpoints
- **Naming:** `snake_case` for variables/functions, `PascalCase` for classes

```bash
cd backend
black app/          # format
ruff check app/     # lint
pytest tests/ -v    # test
```

### TypeScript (Dashboard)

- **Formatter:** Prettier (`.prettierrc` in dashboard dir)
- **Linter:** ESLint
- **Component naming:** PascalCase
- **Hook naming:** camelCase with `use` prefix
- **No `any` types** — always define proper interfaces

```bash
cd admin_dashboard
npm run lint        # eslint
npm run build       # type check + build
```

### Kotlin / Flutter

- Follow official style guides
- All native Kotlin classes must handle `SecurityException` gracefully
- No hardcoded secrets or API URLs — use `BuildConfig` / `app_config.dart`

---

## Git Workflow

### Branches

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready, protected |
| `develop` | Integration branch |
| `feature/xxx` | New feature |
| `fix/xxx` | Bug fix |
| `docs/xxx` | Documentation only |

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(backend): add SIM swap detection endpoint
fix(dashboard): OTP modal closes on ESC key
docs(api): add heartbeat endpoint examples
refactor(mobile): extract location caching to separate service
test(backend): add OTP rate limiting tests
```

### Pull Request Process

1. Create branch from `develop`: `git checkout -b feature/your-feature develop`
2. Write code + tests
3. Run `make test` — all tests must pass
4. Run `make lint` — no lint errors
5. Open PR against `develop` with:
   - Clear description of what changed and why
   - Screenshots for UI changes
   - Test evidence (pytest output or Jest output)
6. At least one reviewer must approve
7. Squash and merge

---

## Testing

### Backend

```bash
cd backend
pytest tests/ -v                          # all tests
pytest tests/test_auth.py -v              # single module
pytest tests/ -k "otp" -v                 # tests matching pattern
pytest tests/ --cov=app --cov-report=html # coverage report
```

### Dashboard

```bash
cd admin_dashboard
npm test                    # watch mode
npm test -- --watchAll=false  # CI mode
```

### Security Testing

```bash
# OWASP dependency audit
make test-security

# Manual: run with DEBUG=true and check /docs endpoint for API testing
```

---

## Security Guidelines

- **Never commit secrets** — use `.env` files (already in `.gitignore`)
- **Never log PII** — device IDs OK, emails/phone numbers NOT in logs
- **Validate all inputs** — use Pydantic schemas, no raw SQL
- **Rate limit new endpoints** — use `@limiter.limit()` decorator
- **OTP-protect destructive actions** — wipe, uninstall must require verified OTP
- **Audit log all admin actions** — use `audit_service.log_action()`

---

## Adding a New Remote Command

1. **Backend** — add command type to `CommandType` enum in `models/command.py`
2. **Backend** — add handler in `routers/commands.py`
3. **Mobile (Flutter)** — add case in `services/command_executor.dart`
4. **Dashboard** — add button in `pages/DeviceDetailPage.tsx`
5. **Docs** — add entry in `docs/API.md`
6. **Tests** — add test in `tests/test_commands.py`

---

## Reporting Security Issues

**Do NOT open a public GitHub issue for security vulnerabilities.**

Email: security@yourcompany.com

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (optional)

We will respond within 48 hours.

---

## License

By contributing, you agree your contributions will be licensed under the [MIT License](LICENSE).
