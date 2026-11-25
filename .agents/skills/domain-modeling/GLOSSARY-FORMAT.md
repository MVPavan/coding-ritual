# GLOSSARY.md Format

## Structure

```md
# {Context Name}

{One or two sentence description of what this context is and why it exists.}

Use these terms, never a word a term lists under _Avoid_ for that meaning. Treat a
concept this glossary lacks as either coined language to reconsider or a real gap
to note.

## Language

**Order**:
{A one or two sentence description of the term}
_Avoid_: Purchase, transaction

**Invoice**:
A request for payment sent to a customer after delivery.
_Avoid_: Bill, payment request

**Customer**:
A person or organization that places orders.
_Avoid_: Client, buyer, account
```

## Rules

- **Be opinionated.** When multiple words exist for the same concept, pick the best one and list the others under `_Avoid_`.
- **Keep definitions tight.** One or two sentences max. Define what it IS, not what it does.
- **Only include terms specific to this project's context.** General programming concepts (timeouts, error types, utility patterns) don't belong even if the project uses them extensively. Before adding a term, ask: is this a concept unique to this context, or a general programming concept? Only the former belongs.
- **Group terms under subheadings** when natural clusters emerge. If all terms belong to a single cohesive area, a flat list is fine.

## Single vs multi-context repos

**Single context:** One glossary at the location declared by `AGENTS.md`,
defaulting to `.repo-context/GLOSSARY.md`. Preserve an existing root `GLOSSARY.md`
when adopting another repo unless relocation is authorized.

**Multiple contexts:** A `GLOSSARY-MAP.md` at the repo root lists the contexts, where they live, and how they relate to each other:

```md
# Glossary Map

## Contexts

- [Ordering](./src/ordering/GLOSSARY.md) — receives and tracks customer orders
- [Billing](./src/billing/GLOSSARY.md) — generates invoices and processes payments
- [Fulfillment](./src/fulfillment/GLOSSARY.md) — manages warehouse picking and shipping

## Relationships

- **Ordering → Fulfillment**: Ordering emits `OrderPlaced` events; Fulfillment consumes them to start picking
- **Fulfillment → Billing**: Fulfillment emits `ShipmentDispatched` events; Billing consumes them to generate invoices
- **Ordering ↔ Billing**: Shared types for `CustomerId` and `Money`
```

Select the glossary in this order; the first that applies wins, for reading and
for creating the file:

1. The location the project's instructions declare (such as `AGENTS.md`).
2. A root `GLOSSARY-MAP.md`: the glossary it lists for the current context, at
   that path even if the file does not exist yet.
3. An existing root `GLOSSARY.md` or `.repo-context/GLOSSARY.md`. If both exist,
   resolve which one owns the terms before editing; do not maintain duplicates.
4. Otherwise `.repo-context/GLOSSARY.md`, created lazily when the first term is
   resolved and documentation work is authorized.

When multiple contexts exist, infer which one the current topic relates to. If unclear, ask. Context-specific ADRs live in `<context>/docs/adr/`; system-wide ones stay in the root `docs/adr/`.
