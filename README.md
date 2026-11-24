# Python_2020

## Engineering skills for Claude Code

This repository bundles two third-party Agent Skills libraries so Claude Code can use them here:

| Library | License | What it adds |
|---|---|---|
| [Claude Engineering Skills](https://github.com/Soljourner/claude-engineering-skills) (Soljourner) | MIT | 36 skills for fluids, pump design, thermodynamics, CFD/FEA workflows and the Python tooling around them |
| [AI Mechanical 3DCAD Design Agent](https://github.com/Milkdomeda/ai-mechanical-3dcad-design-agent) (Milkdomeda) | Apache-2.0 | 4 skills for building, validating and analysing FreeCAD models, backed by its `mechanical-design` MCP server |

### Layout

| Path | Contents |
|---|---|
| `.claude/skills/<skill-name>/` | One directory per skill (`SKILL.md` + its scripts and references). Claude Code loads these automatically in this repo. |
| `docs/engineering-skills/`, `docs/mechanical-3dcad-design-agent/` | Each library's upstream docs and license. `manifest.json` records the upstream commit and which skills came from it. |
| `scripts/sync_skills.py` | Re-syncs both libraries from upstream. |
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
3. **Register the MCP servers** by saving this as `.mcp.json` in the repo root (or adding them with `claude mcp add`).
   Both are pinned to the commits upstream audited:

   ```json
   {
     "mcpServers": {
       "mechanical-design": {
         "command": "uvx",
         "args": ["--from", "git+https://github.com/Milkdomeda/ai-mechanical-3dcad-design-agent@06cc0d6cd64b2b6e03dd2d7cd34a00281816304e", "mechanical-design-mcp"],
         "env": { "MECH_DESIGN_MCP_TOOL_PROFILE": "design" }
       },
       "freecad": {
         "command": "uvx",
         "args": ["--from", "git+https://github.com/neka-nat/freecad-mcp@7667e272e1db669ff61dd5411fb4f622691f2dbc", "freecad-mcp"]
       }
     }
   }
   ```

Then ask for a part, e.g. *"Design a wall-mount bracket for a 2 kg load with two M6 bolts."* The `mechanical-design` skill
clarifies requirements, asks you to approve one design direction, models it in FreeCAD, validates it, and asks for final
confirmation. `freecad-standard-parts` also refers to a `$step-parts` skill
([earthtojake/text-to-cad](https://github.com/earthtojake/text-to-cad/tree/main/skills/step-parts)) for catalog parts; it is not bundled here.

Validation reports are geometry and provenance evidence only — not FEA sign-off, manufacturing release or certification.

### Updating from upstream

```bash
python scripts/sync_skills.py                                  # both libraries, latest default branch
python scripts/sync_skills.py engineering-skills               # one library
python scripts/sync_skills.py mechanical-3dcad-design-agent --ref <tag>
```

Each library only replaces or removes the skills its own manifest lists, so skills from the other library or written by
hand are left alone. After updating the FreeCAD agent, bump the pinned commit in your `.mcp.json` to match. Review the diff before
committing — skills are instructions Claude will follow.

### Skills: FreeCAD design agent

| Skill | Description |
|---|---|
| `mechanical-design` | Requirements → one direction approval → knowledge retrieval → FreeCAD modeling → validation → final confirmation → Design Lesson |
| `freecad-standard-parts` | Insert standard fasteners, gears and catalog parts (STEP) with BOM and provenance |
| `freecad-model-validation` | Validate FCStd parts/assemblies and STEP parts; writes JSON, Markdown and PNG evidence |
| `mechanical-fea` | Prepare, run and inspect source-bound linear static FEA, with explicit human approvals |

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
