FROM astral/uv:python3.12-bookworm-slim

WORKDIR /app

# Copy project metadata.
COPY pyproject.toml ./

# Copy application source before uv sync because
# uv_build needs src/app/__init__.py to build the project.
COPY src ./src

# Install project dependencies.
RUN uv sync --no-dev

# Make the src-layout imports work.
ENV PYTHONPATH=/app/src