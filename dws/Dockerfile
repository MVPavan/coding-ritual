# P1 named-volume probe only. NOT the future DWS application image.
# This cached foundation has Python 3.11, below DWS's >=3.13 requirement.
# Do not install the DWS package here or advertise API/worker/QMD readiness.
FROM node@sha256:905bbb67517e1e9a2a08d661635262e1289e3c786f7e2ab8bceca5314906ad98 AS image-volume-qualification
USER root
RUN mkdir /state && chown 1000:1000 /state
COPY image_volume_probe.py /opt/dws-image-volume-probe.py
USER 1000:1000
WORKDIR /state
ENTRYPOINT ["python3", "/opt/dws-image-volume-probe.py"]
CMD ["read"]

# Application foundation: linux/amd64; registry/source receipts in manifest.
FROM node:22.22.0-bookworm-slim@sha256:7cc56ef285a8568121537d17b05e72128f01b89c54607b51acf084a50ef483f3 AS application-qmd
WORKDIR /opt/qmd
COPY docker/qmd/package.json docker/qmd/package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund --userconfig=/dev/null \
    && echo '6fd4292c6c5f352436cd85c9e1cb286978efa43c20ae350973f83414ced9991d  node_modules/better-sqlite3/prebuilds/linux-x64.node' | sha256sum -c - \
    && echo '5923730861b86c707cca5602b5f91092f9e52a46706dbc6e269fd4bb9c4498e8  node_modules/sqlite-vec-linux-x64/vec0.so' | sha256sum -c - \
    && mv node_modules/@modelcontextprotocol /tmp/excluded-mcp-sdk

FROM ghcr.io/astral-sh/uv:0.9.8@sha256:f76a8aa726a81249cf123ebfbbcf0bda266118f1c30ffcc70116e268b4ecea4f AS application-uv
FROM python:3.13.12-slim-bookworm@sha256:3121f8b0804aa3698ab750d9a39ea4a42657a385c9b133722b915e55c51551a6 AS application-python
COPY --from=application-uv /uv /usr/local/bin/uv
WORKDIR /build/dws
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
COPY docker/application_build.txt /build/requirements.txt
# Build tools stay outside the runtime venv; install a non-editable distribution.
RUN uv venv /build/tools \
    && uv pip sync --python /build/tools/bin/python --require-hashes /build/requirements.txt \
    && uv build --wheel --python /build/tools/bin/python --no-build-isolation --out-dir /build/wheels \
    && UV_PROJECT_ENVIRONMENT=/opt/dws uv sync --frozen --no-dev --no-install-project \
    && uv pip install --python /opt/dws/bin/python --no-deps /build/wheels/dws-*.whl

FROM python:3.13.12-slim-bookworm@sha256:3121f8b0804aa3698ab750d9a39ea4a42657a385c9b133722b915e55c51551a6 AS application
COPY --from=application-qmd /usr/local/bin/node /usr/local/bin/node
COPY --from=application-qmd /usr/lib/x86_64-linux-gnu/libstdc++.so.6 /usr/lib/x86_64-linux-gnu/libstdc++.so.6
COPY --from=application-qmd /opt/qmd /opt/qmd
COPY --from=application-python /opt/dws /opt/dws
RUN groupadd --gid 1000 dws \
    && useradd --uid 1000 --gid 1000 --no-create-home --home-dir /state/home dws \
    && mkdir -p /state/home /state/config /state/cache /state/archive \
    && chown -R 1000:1000 /state && chmod 0700 /state /state/home /state/config /state/cache /state/archive
ENV PATH="/opt/dws/bin:/opt/qmd/node_modules/.bin:/usr/local/bin:/usr/bin:/bin" \
    HOME=/state/home XDG_CACHE_HOME=/state/cache QMD_CONFIG_DIR=/state/config \
    INDEX_PATH=/state/index.sqlite PYTHONDONTWRITEBYTECODE=1
COPY docker/application_entrypoint.sh /opt/application-entrypoint.sh
USER 1000:1000
WORKDIR /state
ENTRYPOINT ["/bin/sh", "/opt/application-entrypoint.sh"]
# No daemon/worker or healthcheck exists yet. Honest scaffold help only.
CMD ["dws", "--help"]
