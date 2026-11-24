# Python_2020

## Engineering skills for Claude Code

This repository bundles the [Claude Engineering Skills](https://github.com/Soljourner/claude-engineering-skills)
library (MIT, © 2025 Soljourner): 36 Agent Skills for mechanical, aerospace and pump-design work —
fluid properties, pump design and selection, CFD/FEA workflows, and the Python tooling around them.

### How it is integrated

| Path | Contents |
|---|---|
| `.claude/skills/<skill-name>/` | One directory per skill (`SKILL.md` + its scripts and references). Claude Code loads these automatically when it runs in this repo. |
| `docs/engineering-skills/` | Upstream README, category guides, skills inventory, contributing guide and license. `manifest.json` records the upstream commit and where each skill came from. |
| `scripts/sync_engineering_skills.py` | Re-syncs the skills from upstream. |
| `requirements-engineering.txt` | Python packages the skills use. |

Upstream nests skills by category (`skills/<category>/<skill>/`); Claude Code only discovers
`.claude/skills/<name>/SKILL.md`, so the sync script flattens them using each skill's frontmatter `name`.
Note that some names differ from the upstream folder name (e.g. `thinking/fluid-dynamics` → `fluid-dynamics-workflow`,
`pump-design/centrifugal-pumps` → `centrifugal-pump-design`); the upstream docs still use the old paths, so use the table below to translate.

### Setup

```bash
pip install -r requirements-engineering.txt   # or just the packages you need
```

Then open the repo in Claude Code and describe the engineering task, e.g.
*"Size a centrifugal pump for 100 m³/h at 50 m head with water at 20 °C and check NPSH margin."*
Claude picks the relevant skills (`centrifugal-pump-design`, `cavitation-analysis`, `coolprop-db`, …) on its own;
you can also call one directly with `/<skill-name>`.

Commercial tools (NIST REFPROP, ANSYS, COMSOL, SolidWorks) need their own licenses; those skills provide scripting guidance only.

### Updating from upstream

```bash
python scripts/sync_engineering_skills.py              # latest upstream default branch
python scripts/sync_engineering_skills.py --ref <tag>  # a specific branch or tag
```

The script only replaces or removes skills it created itself (tracked in `docs/engineering-skills/manifest.json`),
so your own skills in `.claude/skills/` are left alone. Review the diff before committing — skills are instructions Claude will follow.

### Skills

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
