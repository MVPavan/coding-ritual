# Add an item

From the stock list page, the user adds an item with a name and a quantity, and
sees it in the list; cancelling leaves the list as it was.

## Sub-features

- `add-save`: a new item is saved and listed.
- `add-cancel`: cancelling the form saves nothing.
- `add-normalise`: the name is shown trimmed and in lower case.

## How to reach it

- The **Add item** button on the stock list page (`http://127.0.0.1:8740/items`).
- The keyboard shortcut `a` on the same page.
- The direct route `/items/new`.

## Driving it

Each case starts in a fresh page from a reset list; the form keeps its last
values within one page (see Gotchas).

- action: open the stock list page and press **Add item**
  command: `scripts/control web open --new-page http://127.0.0.1:8740/items` then
  `scripts/control web click --role button --name "Add item"`
  result: a form titled "New item" is shown
- action: fill name `  Flour ` and quantity `2`, press **Save**
  command: `scripts/control web fill --label Name "  Flour "`, then
  `scripts/control web fill --label Quantity 2`, then
  `scripts/control web click --role button --name Save`
  result: the list shows `flour` with quantity 2 (the displayed value, not the typed one)
- action: open `flour` in a fresh page
  command: `scripts/control web open --new-page /items/flour`
  result: the item page shows quantity 2 (second read; the save banner is not proof)
- action: reset, open the form, fill a name, press **Cancel**
  command: `scripts/control seed --data "$RUN_DIR"`, then
  `scripts/control web open --new-page http://127.0.0.1:8740/items`, then
  `scripts/control web click --role button --name "Add item"`, then
  `scripts/control web fill --label Name Sugar`, then
  `scripts/control web click --role button --name Cancel`
  result: the list shows exactly the three seeded items; no `sugar`
- action: reset, then reach the form by the keyboard shortcut
  command: `scripts/control seed --data "$RUN_DIR"`, then
  `scripts/control web open --new-page http://127.0.0.1:8740/items`, then
  `scripts/control web press a`
  result: the "New item" form is shown with empty fields
- action: reset, then reach the form by its direct route
  command: `scripts/control seed --data "$RUN_DIR"`, then
  `scripts/control web open --new-page /items/new`
  result: the "New item" form is shown with empty fields

Reset: `scripts/control seed --data "$RUN_DIR"` before the next feature.

## Gotchas

- The form keeps its last values across opens in one page; use a fresh page for
  each case or the cancel journey passes for the wrong reason.
