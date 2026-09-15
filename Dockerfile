FROM python:3.14-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . \
    && groupadd --gid 10001 zut \
    && useradd --uid 10001 --gid zut --create-home zut \
    && mkdir --parents /var/lib/zut-balance /var/backups/zut-balance \
    && chown -R zut:zut /var/lib/zut-balance /var/backups/zut-balance

USER zut
CMD ["uvicorn", "zut_balance.api:app", "--host", "0.0.0.0", "--port", "8000"]
