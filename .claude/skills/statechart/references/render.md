# Rendering a chart as an image

Render an image with one named renderer at a pinned version, installed once outside the repository, only when the person wants an image or the text is too long to read, and change renderer only on request.
The renderer is the Mermaid project's command-line tool, `@mermaid-js/mermaid-cli@11.17.1`
(`mmdc`), with `puppeteer@25.16.0` for its headless browser. Rendering with this
skill's files is unproven: check the first image before relying on these rules.

**Install, once per user, with the person's approval** (Node 22.12 or newer,
the floor of `puppeteer@25`; its browser download is large):

```sh
v=11.17.1; dir="$HOME/.local/share/mermaid-cli/$v"; mkdir -p "$dir"
PUPPETEER_CACHE_DIR="$dir/browsers" npm install --prefix "$dir" --save-exact --no-fund --no-audit \
  "@mermaid-js/mermaid-cli@$v" "puppeteer@25.16.0"
"$dir/node_modules/.bin/mmdc" --version   # prints 11.17.1
```

Save the stylesheet below in `$dir` as `statechart.css`. Removal is that one
folder. **Render** each shown `chart.mmd` to `chart.svg` in the same folder,
with the `render.json` the tool wrote beside it, and give the person the image:

```sh
dir="$HOME/.local/share/mermaid-cli/11.17.1"
PUPPETEER_CACHE_DIR="$dir/browsers" "$dir/node_modules/.bin/mmdc" -i chart.mmd -o chart.svg \
  -c render.json -C "$dir/statechart.css" -I chart -b transparent
```

When `mmdc` exits non-zero, give the person its error together with the
chart's Mermaid source.

**Limits.** Mermaid refuses input over 50,000 characters and charts over 500
edges by default. No fixed limit fits every chart: 500 model states allow about
250,000 arrows, more in a regions chart. So the tool writes `render.json` for
each chart, with `maxTextSize` set to the chart's own length and `maxEdges` to
its own count of `-->` lines, each never below Mermaid's default, and
`"securityLevel": "strict"`. Whether a chart that size renders in reasonable
time is unproven.

**Colours.** The chart file defines styles for `breaks` and `mayBreak` only, so
any viewer shows the failure marks. `onPath`, `repeats` and the `phase_<colour>`
classes get their colours here. `mmdc -C` puts this sheet inside the SVG, so
the image follows the viewer's light or dark setting. Phase fills come first;
the mark rules come last and carry `!important`, since Mermaid may write a
`classDef` as the node's own style, which a plain rule cannot override.

```css
#chart .phase_blue rect{fill:#dbe9fb} #chart .phase_green rect{fill:#dcf1df} #chart .phase_yellow rect{fill:#fbf3c9}
#chart .phase_orange rect{fill:#fde3cc} #chart .phase_purple rect{fill:#e9e0f8} #chart .phase_teal rect{fill:#d3efec}
#chart .phase_pink rect{fill:#f9dceb} #chart .phase_gray rect{fill:#e6e6e6}
#chart .onPath rect{stroke:#1f5fbf !important;stroke-width:3px !important}
#chart .repeats rect{stroke:#7a3fb8 !important;stroke-width:3px !important;stroke-dasharray:4 3 !important}
@media (prefers-color-scheme: dark){
#chart .node rect{fill:#26282c;stroke:#8a8f98} #chart .nodeLabel,#chart text{fill:#ececec;color:#ececec}
#chart .transition{stroke:#9aa0a8} #chart .edgeLabel,#chart .edgeLabel rect{background:#1b1c1f;fill:#1b1c1f}
#chart .phase_blue rect{fill:#203450} #chart .phase_green rect{fill:#1f3a26} #chart .phase_yellow rect{fill:#3d3818}
#chart .phase_orange rect{fill:#45301b} #chart .phase_purple rect{fill:#33284a} #chart .phase_teal rect{fill:#173a37}
#chart .phase_pink rect{fill:#432536} #chart .phase_gray rect{fill:#333438}
#chart .breaks rect{fill:#4a1f1d !important;stroke:#f2776b !important} #chart .breaks .nodeLabel{color:#ffd9d4 !important}
#chart .mayBreak rect{fill:#433414 !important;stroke:#f2776b !important} #chart .mayBreak .nodeLabel{color:#fbe7b3 !important}
#chart .onPath rect{stroke:#6fa3f2 !important} #chart .repeats rect{stroke:#b48ae6 !important}}
```
