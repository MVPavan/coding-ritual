# Registry viewer

One self-contained HTML page for reviewing the registry: every upstream unit of
every harness with rulings beside our skills, playbooks and principles, lanes by
lifecycle stage, a drawer per unit, the router, and decisions kept in the
browser with an export. Its text is pulled from the registry, the units and the
router; nothing is generated.

Rebuild it after any registry or unit change:

```sh
uv run python harness_lifecycle/registry/registry.py viewer [--out PATH]
```

The page goes to `index.html` here by default. It is untracked (about 2 MB and
regenerable); only `template.html` and the code in
`curation/registry/views/viewer.py` are kept.
