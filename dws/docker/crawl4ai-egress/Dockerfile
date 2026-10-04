# Provider-only protective overlay; no application/QMD files or new packages.
FROM unclecode/crawl4ai@sha256:9021b3cb5c6f12570bbcd5395638495e0a06969b3148e377b953d174af2ebc9b
USER root
COPY patch.py /tmp/dws-egress-patch.py
RUN python /tmp/dws-egress-patch.py && rm /tmp/dws-egress-patch.py
USER appuser
