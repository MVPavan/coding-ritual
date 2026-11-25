# Optional alternative interface designs

Use when comparing real alternatives could change a consequential interface
choice, or when a caller has several valid implementation shapes, even inside one
function. State caller needs, constraints, dependencies and invariants first. This
stops at a recommended design; the caller writes the code.

Sketch a small number of materially different designs, locally or through bounded
independent workers when shared delegation policy supports it. Do not force a
three-agent exercise or invent variants for an already clear interface or shape.

For each design, show the caller-facing contract, a usage example, hidden
complexity, dependency strategy and migration cost. Compare depth, locality,
seam placement, error behavior and testability. Recommend one with reasons,
preserving strengths of alternatives only when the combination remains coherent.
