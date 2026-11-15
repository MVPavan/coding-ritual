# Source reader brief

Load at step 3 when a sizeable feature gets its own helper. Hand the helper
the brief below, filled in; it reads from source only and returns one result.

## Fill in

- **Feature:** the feature file's path and its name.
- **Product:** the repository root, and the revision the target skill last
  recorded.
- **Where to start:** the entry points the feature file lists (route, command,
  menu item) and any source path it cites.

## The brief

> Explain from source how this user-facing feature works now, and where its
> feature file disagrees. Read only: do not launch, start or drive the product,
> do not run its commands, and edit no file. Return exactly the four parts
> below; write "none" for a part with nothing in it.

## Return shape

1. **Summary:** what a user does and what the product does in reply, in a few
   lines.
2. **Source entry points:** each file and symbol where the feature starts
   (parser, handler, route, screen), as `path:line`.
3. **Likely drift:** each statement of the feature file that the source
   contradicts or omits (a renamed flag, a new required input, a changed exit
   code, a missing prerequisite), with the file's wording and the `path:line`
   that shows the product's behaviour; or "none".
4. **Live recipe:** one short way to drive the feature through the target
   skill's helper, with the values to assert.

A citation names a line that holds the claim itself, not the file that imports
it. A guess is marked as a guess, never cited as drift.
