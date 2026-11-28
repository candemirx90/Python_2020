# Python_2020

## Engineering skills for Claude Code

This repository bundles five third-party Agent Skills libraries so Claude Code can use them here:

| Library | License | What it adds |
|---|---|---|
| [Claude Engineering Skills](https://github.com/Soljourner/claude-engineering-skills) (Soljourner) | MIT | 36 skills for fluids, pump design, thermodynamics, CFD/FEA workflows and the Python tooling around them |
| [AI Mechanical 3DCAD Design Agent](https://github.com/Milkdomeda/ai-mechanical-3dcad-design-agent) (Milkdomeda) | Apache-2.0 | 4 skills for building, validating and analysing FreeCAD models, backed by its `mechanical-design` MCP server |
| [text-to-cad](https://github.com/earthtojake/text-to-cad) (earthtojake), v0.11.17 | MIT | 8 skills for build123d CAD as Python, manufacturing checks, FEA, drawings, renders, PCBs, 3D printing, SendCutSend and robot descriptions, driven by the `cad` CLI |
| [last30days](https://github.com/mvanhorn/last30days-skill) (Matt Van Horn), v4.6.0 | MIT | 1 skill that researches what people said about a topic in the last 30 days across Reddit, X, YouTube, TikTok, Hacker News, Polymarket, GitHub and the web |
| [Graphify](https://github.com/safishamsi/graphify) (Safi Shamsi), v0.9.122 | Apache-2.0 (earlier parts MIT) | 1 skill that turns a folder of code, docs, papers or images into a queryable knowledge graph (interactive HTML, JSON and a plain-language report), driven by the `graphify` CLI |

### Layout

| Path | Contents |
|---|---|
| `.claude/skills/<skill-name>/` | One directory per skill (`SKILL.md` + its scripts and references). Claude Code loads these automatically in this repo. |
| `docs/engineering-skills/`, `docs/mechanical-3dcad-design-agent/`, `docs/text-to-cad/`, `docs/last30days/`, `docs/graphify/` | Each library's upstream docs and license. `manifest.json` records the upstream commit and which skills came from it. |
| `scripts/sync_skills.py` | Re-syncs the libraries from upstream. |
| `requirements-engineering.txt` | Python packages the engineering skills use. |

Claude Code only discovers `.claude/skills/<name>/SKILL.md`, so the sync script copies each upstream skill there
under its frontmatter `name`. Some names differ from the upstream folder (e.g. `thinking/fluid-dynamics` →
`fluid-dynamics-workflow`); the upstream docs still use the old paths, so use the tables below to translate.

### Setup: engineering skills

```bash
pip install -r requirements-engineering.txt   # or just the packages you need
```

Then describe the task, e.g. *"Size a centrifugal pump for 100 m³/h at 50 m head with water at 20 °C and check NPSH margin."*
Claude picks the relevant skills on its own; you can also call one with `/<skill-name>`.
Commercial tools (NIST REFPROP, ANSYS, COMSOL, SolidWorks) need their own licenses; those skills give scripting guidance only.

### Setup: FreeCAD design agent

These skills drive two MCP servers and only work on a machine with FreeCAD and [uv](https://docs.astral.sh/uv/):

1. **FreeCAD 1.1.3** (the version upstream tests against) with the FreeCAD MCP add-on: copy `addon/FreeCADMCP` from
   [`neka-nat/freecad-mcp`](https://github.com/neka-nat/freecad-mcp) at commit `7667e272e1db669ff61dd5411fb4f622691f2dbc`
   into FreeCAD's `Mod/` folder, restart FreeCAD, pick **MCP Addon → Start RPC Server**.
   Optional workbenches used by `freecad-standard-parts`: Fasteners and `freecad.gears`.
2. **Design workspace** (outside this repo), then export it before starting Claude Code:

   ```bash
   uvx --from git+https://github.com/Milkdomeda/ai-mechanical-3dcad-design-agent@06cc0d6cd64b2b6e03dd2d7cd34a00281816304e \
     mechanical-design init --workspace ~/mechanical-design-workspace \
     --actor engineer --organization example-org --design-group example-group
   export MECH_DESIGN_WORKSPACE=~/mechanical-design-workspace
   ```

   Run `mechanical-design status --workspace "$MECH_DESIGN_WORKSPACE"` to see what is still missing
   (e.g. the `FreeCADCmd` path, which FEA needs). PostgreSQL is optional and only stores reusable Design Lessons.
3. **MCP servers** are registered in `.mcp.json` (pinned to the commits upstream audited): `mechanical-design` for design
   state, validation and FEA, and `freecad` for live CAD edits through the add-on from step 1. Claude Code asks you to
   approve them the first time you open the repo; both run through `uvx`, and `mechanical-design` reads
   `MECH_DESIGN_WORKSPACE` from the environment you start Claude Code in.

Then ask for a part, e.g. *"Design a wall-mount bracket for a 2 kg load with two M6 bolts."* The `mechanical-design` skill
clarifies requirements, asks you to approve one design direction, models it in FreeCAD, validates it, and asks for final
confirmation. `freecad-standard-parts` also refers to a `$step-parts` skill from text-to-cad for catalog parts; text-to-cad
retired that skill in 0.11, so catalog STEP files come from the step.parts service directly
(`freecad-standard-parts/scripts/cache_step_part.py` caches and checksums them).

Validation reports are geometry and provenance evidence only — not FEA sign-off, manufacturing release or certification.

### Setup: text-to-cad

The skills call the `cad` CLI (needs [uv](https://docs.astral.sh/uv/)); they were written for 0.11.17:

```bash
uv tool install cad==0.11.17
cad --version
```

Then ask, e.g. *"Model a 40 × 20 × 6 mm bracket with an 8 mm bore and export a STEP."* `cad` builds the model, prints a
local viewer link and exports files. Blender (`render`), KiCad (`pcb`) and OrcaSlicer (`print3d`) are only needed for
those skills. Upstream's one-line installer also turns on automatic plugin updates; installing `cad` with uv as above
does not, and the vendored skills only change when you run the sync script.

**Which skill when:** text-to-cad (`cad`, `fea`) works on build123d Python models with no FreeCAD; the FreeCAD agent
(`mechanical-design`, `mechanical-fea`) works on FCStd files with approval gates and validation evidence. Name the one
you want if a request could fit both.

### Web scraping: Playwright MCP

`.mcp.json` also registers Microsoft's [Playwright MCP](https://github.com/microsoft/playwright-mcp)
(`@playwright/mcp@0.0.85`, run with `npx`, so it needs Node.js). It drives a real browser, so it handles
JavaScript-heavy pages, clicking through pagination, filling search forms and screenshots. Ask, e.g.
*"Open example.com/products, go through every page and save name, price and URL to `data/products.csv`."*

- **Browser:** it uses Google Chrome by default. Without Chrome, run `npx playwright install chrome`, or add
  `"--browser", "chromium"` to its args and run `npx playwright install chromium`.
- **Flags:** `--headless` runs without a window (remove it to watch the browser), `--isolated` starts each session
  with a fresh in-memory profile so your own cookies and logins are never used, and `--output-dir .playwright-mcp`
  keeps screenshots and traces in a git-ignored folder.
- **Cloud sessions** only reach the hosts their environment allows (package registries by default), so scrape from
  your own machine, or add the target hosts to the environment's network settings.
- Respect each site's terms of use and `robots.txt`, and keep request rates polite.

### Setup: last30days

Run `/last30days <topic>`, e.g. `/last30days Segway F2 Pro reviews`. It needs Python 3.12+ (it installs one through uv
if missing) and Node.js for its X search client; `yt-dlp` adds YouTube. The first run starts a setup wizard that writes
`~/.config/last30days/.env`.

- **Free sources, no keys:** Hacker News, Polymarket, public Reddit threads, YouTube (with `yt-dlp`) and the web.
- **Optional keys** add sources: `SCRAPECREATORS_API_KEY` for TikTok and Instagram (10,000 free calls), `X_BEARER_TOKEN`
  or `XAI_API_KEY` for X, and Brave, Perplexity, Parallel or OpenRouter for web search. Paid calls spend credits.
- **Browser cookies:** it can read X or Reddit logins from Chrome, Safari or Firefox, but only after you consent
  (`BROWSER_CONSENT` / `FROM_BROWSER`). Answer *no* in the wizard to keep it off.
- **Saved briefs** go to `~/Documents/Last30Days` (`LAST30DAYS_MEMORY_DIR`; set it empty to save nothing). Publishing to
  `ht-ml.app` happens only when you ask, and those pages are public unless password-protected.
- **Not included:** upstream's plugin Stop hook, which auto-archives finished briefs, and its demo media (`assets/`).
- **Cloud sessions** only reach allowed hosts; add e.g. `www.reddit.com`, `hn.algolia.com` and
  `gamma-api.polymarket.com` to the environment's network settings to research from there.

### Setup: Graphify

The skill drives the `graphify` CLI from the `graphifyy` package (Python 3.11.5+). Install the version the skill was
vendored from, so its instructions and the CLI match:

```bash
uv tool install graphifyy==0.9.122   # or: pipx install graphifyy==0.9.122
graphify --version
```

If `graphify` is missing, the skill installs the latest `graphifyy` itself, which may not match the vendored text.
Then run `/graphify` (this repo), `/graphify <path>`, or ask a question once a graph exists, e.g.
`/graphify query "which skills use the cad CLI?"`.

- **Output** goes to `graphify-out/` (`graph.html`, `graph.json`, `GRAPH_REPORT.md`, plus a cache); it is git-ignored.
- **No API key needed.** Code is parsed locally (tree-sitter). Docs, papers and images are read by the Claude Code
  session itself, which costs tokens on large folders; `GEMINI_API_KEY`/`GOOGLE_API_KEY` switches that to Gemini.
- **Not included:** what `graphify claude install` adds beyond the skill — a `## graphify` block in `CLAUDE.md` and
  PreToolUse/SessionStart hooks in `.claude/settings.json` that nudge (or, with `--strict`, block) Read/Grep until the
  graph is queried. Run `graphify claude install --project` yourself if you want them. The skill sets up a post-commit
  rebuild hook only when you ask for one (`graphify hook install`).
- **Cloud sessions** reach PyPI by default, so the install works; `/graphify https://github.com/...` needs `github.com`
  allowed for cloning.

### Updating from upstream

```bash
python scripts/sync_skills.py                                  # every library, latest default branch
python scripts/sync_skills.py engineering-skills               # one library
python scripts/sync_skills.py mechanical-3dcad-design-agent --ref <tag>
python scripts/sync_skills.py graphify --ref v<version>            # tags match the graphifyy release
```

Each library only replaces or removes the skills its own manifest lists, so skills from other libraries or written by
hand are left alone. After updating the FreeCAD agent, bump the pinned commit in `.mcp.json` to match; after updating text-to-cad, install the `cad` version its `cad` skill names; after updating Graphify, install the matching `graphifyy` version. Review the diff before
committing — skills are instructions Claude will follow.

### Skills: FreeCAD design agent

| Skill | Description |
|---|---|
| `mechanical-design` | Requirements → one direction approval → knowledge retrieval → FreeCAD modeling → validation → final confirmation → Design Lesson |
| `freecad-standard-parts` | Insert standard fasteners, gears and catalog parts (STEP) with BOM and provenance |
| `freecad-model-validation` | Validate FCStd parts/assemblies and STEP parts; writes JSON, Markdown and PNG evidence |
| `mechanical-fea` | Prepare, run and inspect source-bound linear static FEA, with explicit human approvals |

### Skills: text-to-cad

| Skill | Description |
|---|---|
| `cad` | Parts, assemblies, mechanisms and DXF profiles as build123d Python; export STEP/STL/3MF/GLB; manufacturability checks |
| `fea` | Linear static stress check with CalculiX: peak stress, safety factor, deflection |
| `engineering-drawing` | Dimensioned PDF drawings projected from the 3D model |
| `render` | Photoreal stills and videos with Blender |
| `pcb` | KiCad schematics and boards, ERC/DRC, pre-order review, fab files |
| `print3d` | Slice with OrcaSlicer; hand off to Bambu Connect or Bambu Studio |
| `sendcutsend` | Preflight DXF/STEP files against SendCutSend's rules before you order (it does not order) |
| `robot-simulation` | URDF, SRDF and MJCF for ROS, MoveIt and MuJoCo |

### Skills: research

| Skill | Description |
|---|---|
| `last30days` | What people actually said about a topic in the last 30 days, ranked by engagement, with citations; also trending discovery, competitor comparisons and a source health check (`doctor`) |

### Skills: knowledge graph

| Skill | Description |
|---|---|
| `graphify` | Build a knowledge graph of a folder or GitHub repo (communities, "god nodes", EXTRACTED/INFERRED edges), then `query`, `path` and `explain` against it; exports to HTML, JSON, Obsidian, GraphML, Neo4j and an MCP server |

### Skills: engineering library

| Category | Skill | Upstream path | Description |
|---|---|---|---|
| databases | `cavitation-risk-db` | `skills/databases/cavitation-risk-db` | Query vapor pressures and NPSH requirements for cavitation assessment |
| databases | `coolprop-db` | `skills/databases/coolprop-db` | Query thermodynamic properties for 100+ fluids from CoolProp database |
| databases | `hydraulic-components-db` | `skills/databases/hydraulic-components-db` | Query loss coefficients for pipes, valves, fittings in pump systems |
| databases | `material-properties-db` | `skills/databases/material-properties-db` | Query fluid viscosities, densities, and material properties vs temperature |
| databases | `nasa-earthdata` | `skills/databases/nasa-earthdata` | Access atmospheric properties and aerospace fluid data from NASA Earthdata |
| databases | `nist-refprop` | `skills/databases/nist-refprop` | Query high-accuracy thermodynamic properties from NIST REFPROP database (commercial) |
| databases | `pump-performance-db` | `skills/databases/pump-performance-db` | Access manufacturer pump curves and specifications from Grundfos, KSB, and other databases |
| databases | `turbulence-models-db` | `skills/databases/turbulence-models-db` | Select and configure turbulence models (k-epsilon, k-omega SST, LES) for CFD |
| helpers | `engineering-context-init` | `skills/helpers/engineering-context-init` | Initialize engineering session with standard constants, units, and imports |
| helpers | `error-handler-fluids` | `skills/helpers/error-handler-fluids` | Handle common numerical errors in fluid calculations with validation checks |
| helpers | `fluid-property-calculator` | `skills/helpers/fluid-property-calculator` | Quick fluid property calculations using empirical formulas without database queries |
| helpers | `get-available-resources` | `skills/helpers/get-available-resources` | Enumerate installed packages, databases, and tools for engineering workflows |
| helpers | `pump-selection-helper` | `skills/helpers/pump-selection-helper` | Decision tree for selecting pump type based on flow, head, and fluid properties |
| helpers | `unit-converter` | `skills/helpers/unit-converter` | Convert flow rates, pressures, viscosities, and other engineering units |
| integrations | `ansys-simulation` | `skills/integrations/ansys-simulation` | Automate ANSYS Fluent CFD simulations via Python scripting and journal files |
| integrations | `comsol-multiphysics` | `skills/integrations/comsol-multiphysics` | Set up coupled fluid-structure interaction for pump vibration analysis |
| integrations | `openfoam-cfd` | `skills/integrations/openfoam-cfd` | Set up turbulent flow simulations in OpenFOAM with automated case generation |
| integrations | `solidworks-cad` | `skills/integrations/solidworks-cad` | Automate parametric pump impeller design in SolidWorks via API |
| packages | `fluids-package` | `skills/packages/fluids-package` | Pipe flow, pump sizing, friction factor, and compressible flow calculations |
| packages | `matplotlib-visualization` | `skills/packages/matplotlib-visualization` | Create pump performance curves, velocity contours, and engineering plots |
| packages | `networkx-flow-networks` | `skills/packages/networkx-flow-networks` | Model hydraulic networks and multi-pump systems using graph theory |
| packages | `numpy-numerics` | `skills/packages/numpy-numerics` | Numerical array operations for velocity fields, pump curves, and matrix calculations |
| packages | `pint-units` | `skills/packages/pint-units` | Handle engineering units with automatic conversion and dimensional analysis |
| packages | `pyvista-visualization` | `skills/packages/pyvista-visualization` | Create 3D visualizations of velocity fields and pump CFD results |
| packages | `scipy-optimization` | `skills/packages/scipy-optimization` | Optimize pump designs and system parameters using scipy.optimize |
| packages | `sympy-symbolic` | `skills/packages/sympy-symbolic` | Derive and solve fluid dynamics and pump equations symbolically |
| packages | `thermo-package` | `skills/packages/thermo-package` | Calculate thermodynamic properties and mixture behavior for pump applications |
| thinking | `fluid-dynamics-workflow` | `skills/thinking/fluid-dynamics` | Systematic workflow for fluid dynamics analysis from problem setup to validation |
| thinking | `cavitation-analysis` | `skills/thinking/pump-design/cavitation-analysis` | Calculate NPSH and assess cavitation risk in centrifugal pumps |
| thinking | `centrifugal-pump-design` | `skills/thinking/pump-design/centrifugal-pumps` | Design centrifugal pumps using Euler equations, velocity triangles, and specific speed |
| thinking | `pump-efficiency-optimization` | `skills/thinking/pump-design/efficiency-optimization` | Maximize pump efficiency through design optimization and operational strategies |
| thinking | `pump-performance-curves` | `skills/thinking/pump-design/performance-curves` | Generate and interpret H-Q curves, apply affinity laws, and predict off-design performance |
| thinking | `positive-displacement-pumps` | `skills/thinking/pump-design/positive-displacement-pumps` | Design and analyze gear, piston, and screw pumps with volumetric efficiency |
| thinking | `pump-system-integration` | `skills/thinking/pump-design/system-integration` | Design complete pump systems including piping, controls, and parallel/series configurations |
| thinking | `structural-analysis-workflow` | `skills/thinking/structural-analysis` | FEA workflow for pump casings and impellers under fluid loads |
| thinking | `thermodynamics-workflow` | `skills/thinking/thermodynamics` | Analyze thermodynamic cycles and heat transfer in pump systems |
