FROM python:3.11-slim

LABEL org.opencontainers.image.source="https://github.com/tommieseals/doc-drift-detector"
LABEL org.opencontainers.image.description="Detect when code and documentation drift out of sync"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Install dependencies
COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir -e .

# Create non-root user
RUN useradd -m -u 1000 drift
USER drift

WORKDIR /workspace

ENTRYPOINT ["doc-drift"]
CMD ["--help"]
