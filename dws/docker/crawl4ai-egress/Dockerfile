# Provider-only protective overlay; no application/QMD files or new packages.
FROM unclecode/crawl4ai@sha256:bd36741e7bdd35ddc1a05d9183e1d6d8cefb61dd640d944a25d026b76e917690
USER root
COPY patch.py /tmp/dws-egress-patch.py
RUN python /tmp/dws-egress-patch.py && rm /tmp/dws-egress-patch.py
USER appuser
