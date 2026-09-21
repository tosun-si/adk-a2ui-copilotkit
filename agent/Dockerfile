FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

ENV APP_DIR=/usr/local/src/app
WORKDIR ${APP_DIR}

# Deps first (cache layer survives code changes). Single-package project, so
# --no-install-project installs only third-party deps into the venv.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Then the code.
COPY server.py ./server.py
COPY football_a2ui_agent/ ./football_a2ui_agent/

FROM python:3.11-slim

ENV APP_DIR=/usr/local/src/app
RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid 1001 --create-home appuser

WORKDIR ${APP_DIR}

COPY --from=builder --chown=appuser:appuser ${APP_DIR}/.venv ${APP_DIR}/.venv
COPY --from=builder --chown=appuser:appuser ${APP_DIR}/server.py ./server.py
COPY --from=builder --chown=appuser:appuser ${APP_DIR}/football_a2ui_agent/ ./football_a2ui_agent/

ENV PATH="${APP_DIR}/.venv/bin:$PATH"

USER appuser

EXPOSE 8000

# Native AG-UI endpoint (POST /chat) served by ag-ui-adk + FastAPI.
ENTRYPOINT ["uvicorn"]
CMD ["server:app", "--host", "0.0.0.0", "--port", "8000"]
