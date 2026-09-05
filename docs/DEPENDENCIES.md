# Dependency review — 2026-09-05

The six initial Dependabot PRs were reviewed against the management implementation,
including its 36 backend and 6 frontend tests.

| Original PR | Decision | Reason |
| --- | --- | --- |
| #7 Vite 8.2.2 | Adopt together with #12 | React plugin 6 requires Vite 8. |
| #12 React plugin 6.1.1 | Adopt together with #7 | Its declared Vite peer range is `^8.0.0`; Vite 7 is incompatible. |
| #8 globals 17.12.0 | Adopt | Lint and build verified on the current source. |
| #9 pytest 9.1.1 | Adopt | All 36 backend tests pass. |
| #10 TypeScript 7.0.2 | Defer | Installed typescript-eslint 8.69.0 declares TypeScript `>=4.8.4 <6.1.0`. Keep 5.9.3 until a supported toolchain migration is reviewed. |
| #11 Node types 26.4.1 | Defer | Runtime and CI use Node 24; keep matching 24.x types. A passing type check does not establish Node 24 runtime compatibility with Node 26 APIs. |

Dependabot now groups Vite and its React plugin. Node type major upgrades and
TypeScript versions outside the current lint-tool support range are excluded
until a deliberate runtime/toolchain migration updates the policy.

Vite 8 changes bundling to Rolldown/Oxc and raises its default browser baseline.
The project explicitly retains the previous Vite 7 browser targets to avoid
silently raising client requirements during this tooling update.

Validation: dependency installation without peer-dependency overrides, all tests,
lint, production build, npm audit (zero reported vulnerabilities), and browser
smoke testing of the production dashboard and create dialog without VPN writes.
Existing Starlette/httpx deprecation warnings are unchanged.

References: [Vite migration](https://vite.dev/guide/migration),
[typescript-eslint dependency policy](https://typescript-eslint.io/users/dependency-versions/).
Exact package constraints were also checked in npm package metadata.
