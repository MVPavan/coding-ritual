---
name: sharpen
description: "Make a task deeper, not bigger: answer four questions about it, then rewrite the prompt. Use for /sharpen to deepen a task prompt within its scope; settling open scope or behaviour choices is discovery."
disable-model-invocation: true
argument-hint: "The task or prompt to sharpen"
---

# Sharpen

Take the person's task or prompt and rewrite it; do not do the task itself.

Make it deeper, not bigger: the rewrite asks for better work on the same scope,
never for more of it. Refuse additions that only enlarge the task.

First answer four questions, each briefly:

1. What would a top practitioner in this field do here that the request leaves out?
2. What least processed material would they start from instead of a summary or digest?
3. Which specific methods and tools would they use?
4. What, outside both you and the person, would show the result is right?

Then rewrite the prompt to ask for exactly what those answers revealed.

Leave the person's own choices open: where a decision is theirs, name it as a
question in the rewrite instead of deciding it.

Output the four answers, then the rewritten prompt.
