# Provisional `gh` fixtures

Hand-written, modelled on GitHub's documented REST and GraphQL responses (fields the
mirror reads, plus enough neighbours to look like the real thing). They are
**provisional**: M4's live trial records real responses and replaces these files.

String values of the form `$name` are filled by `tests/mirror/_fake_gh.py` from its
state (for example `$login`, `$repo_node_id`). Keys starting with one `_` are notes (GraphQL `__typename` stays) and
are stripped before a response is served. `errors.json` holds what `gh` prints and
exits with for each injected fault.

The fake checks each query's and mutation's operation, argument and field names, not
the structure of its selections (which field sits in which fragment); M4's recorded
responses settle the shapes.
