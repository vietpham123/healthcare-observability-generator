# Dynatrace App Deployment Review

**App**: Healthcare Health Monitoring  
**Version**: 1.19.0 (aligned)  
**Reviewed**: 2026-04-21  
**Last Updated**: 2026-04-21  
**dt-app CLI**: 1.8.1  

---

## Summary

All 10 findings from the initial review have been resolved. The app now meets Dynatrace guidelines for both tenant deployment and Hub distribution readiness. This document tracks all findings and their resolution status.

---

## Critical Issues

### 1. Unlimited DQL Scan Limits
- **Status**: ✅ Resolved
- **File**: `dynatrace-apps/healthcare-health-monitoring/ui/app/queries.ts`
- **Detail**: All ~50 queries used `scanLimitGBytes: -1`, which bypasses cost guardrails.
- **Resolution**: Replaced all 81 occurrences of `scanLimitGBytes: -1` with `scanLimitGBytes: 500`. Unit test added to prevent regression.

### 2. App Description Is a Changelog Note
- **Status**: ✅ Resolved
- **File**: `dynatrace-apps/healthcare-health-monitoring/app.config.json`
- **Resolution**: Description updated to `"Operational health monitoring for Epic EHR, network infrastructure, and clinical integrations across hospital sites."`

### 3. No App Icon
- **Status**: ✅ Resolved
- **File**: `dynatrace-apps/healthcare-health-monitoring/app-icon.png`
- **Resolution**: Generated 512×512 PNG icon with healthcare cross/shield design.

### 4. Version Mismatch
- **Status**: ✅ Resolved
- **Files**: `app.config.json` and `package.json`
- **Resolution**: Both files aligned to version `1.19.0`.

---

## Structural Issues

### 5. App ID Uses `my.` Prefix
- **Status**: ✅ Resolved
- **File**: `app.config.json`
- **Resolution**: App ID changed from `my.healthcare.health.monitoring` to `com.dynatrace.healthcare.health.monitoring`.

### 6. No Tests
- **Status**: ✅ Resolved
- **Detail**: Added vitest with 3 test suites (22 tests):
  - `ui/app/utils/chartHelpers.test.ts` — toDonutData, toBarData (8 tests)
  - `ui/app/utils/queryHelpers.test.ts` — withSiteFilter for all query kinds (6 tests)
  - `ui/app/queries.test.ts` — site config, scan limit regression guard (8 tests)
- **Config**: `vitest.config.ts`, scripts `test` and `test:watch` in package.json.

### 7. No Linting or Formatting Config
- **Status**: ✅ Resolved
- **Detail**: Added flat ESLint config (`eslint.config.mjs`) with typescript-eslint, and `.prettierrc`.
- **Scripts**: `lint` and `format` added to package.json.

### 8. Navigation SDK Not Used
- **Status**: ✅ Resolved
- **Files**: `package.json`
- **Resolution**: Removed unused `@dynatrace-sdk/navigation` dependency from package.json. In-app routing via react-router-dom is correct for single-app navigation.

### 9. No Actions Registered in app.config.json
- **Status**: ✅ Resolved
- **File**: `app.config.json`
- **Resolution**: Added 8 actions covering all routes: overview, security, integration, network, epic, mychart, sites, explore.

### 10. Node Engine Version Outdated
- **Status**: ✅ Resolved
- **File**: `package.json`
- **Resolution**: Updated `engines.node` from `>=16.13.0` to `>=18.0.0`.

---

## What Passes Guidelines

| Area | Status | Notes |
|------|--------|-------|
| Strato component usage | ✅ | `AppRoot`, `Page`, `AppHeader`, `TimeframeSelector`, design tokens, icons |
| `DqlQueryParamsProvider` pattern | ✅ | Correct timeframe management with refresh support |
| Scope declarations | ✅ | Well-declared with descriptive comments, follows least-privilege (read-only) |
| TypeScript strict mode | ✅ | Enabled in `ui/tsconfig.json` |
| `.gitignore` security | ✅ | Excludes `.dt-app/.tokens.json` |
| Component architecture | ✅ | Reusable `KpiCard`, `HealthBadge`, `SectionHealth` components |
| BrowserRouter basename | ✅ | Correctly set to `"ui"` |
| React 18 + Strato 3 | ✅ | Current SDK and framework versions |

---

## Fix Priority

| Priority | Items | Status |
|----------|-------|--------|
| P0 — Blocks tenant deploy quality | #1 (scan limits), #2 (description) | ✅ All resolved |
| P1 — Required for Hub review | #3 (icon), #4 (version), #5 (app ID), #9 (actions) | ✅ All resolved |
| P2 — Expected for Hub review | #6 (tests), #7 (linting), #10 (node version) | ✅ All resolved |
| P3 — Best practice | #8 (navigation SDK) | ✅ All resolved |

---

## Changelog

| Date | Update |
|------|--------|
| 2026-04-21 | Initial review documented |
| 2026-04-21 | All 10 issues resolved: scan limits (500GB), app.config (description, version 1.19.0, app ID, actions), app-icon.png, tests (22 vitest), ESLint+Prettier, removed unused nav SDK, Node >=18 |
