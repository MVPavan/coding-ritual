# Generic Debian/Python runtime. Application packages are prepared by uv at start.
FROM ghcr.io/astral-sh/uv:0.9.8@sha256:f76a8aa726a81249cf123ebfbbcf0bda266118f1c30ffcc70116e268b4ecea4f AS uv
FROM python:3.13.12-slim-bookworm@sha256:3121f8b0804aa3698ab750d9a39ea4a42657a385c9b133722b915e55c51551a6 AS application
COPY --from=uv /uv /usr/local/bin/uv
RUN groupadd --gid 1000 dws \
    && useradd --uid 1000 --gid 1000 --no-create-home --home-dir /app/.runtime/home dws
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_PYTHON_DOWNLOADS=never
USER 1000:1000
WORKDIR /app
CMD ["python", "--version"]
