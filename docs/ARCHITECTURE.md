# System Architecture Overview

## Document Control

- Project: Anthias-Bellforge
- Purpose: Define high-level architecture for school-focused extensions on Anthias
- Status: Draft (Initial Foundation)
- Last updated: 2026-05-01

## 1. Architectural Intent

Anthias-Bellforge extends Anthias with school-oriented, bell-aware orchestration while preserving an additive and maintainable integration strategy. This document describes conceptual components and data flows without asserting unverified Anthias internals from this repository snapshot.

## 2. High-Level Architecture Diagram

```text
+------------------------------------------------------------------+
|                 District / School Management Layer               |
|  - Policy templates  - RBAC boundaries  - Fleet grouping model   |
+-------------------------------+----------------------------------+
                                |
                                v
+------------------------------------------------------------------+
|                      School Mode Scheduler                       |
|  - Day type selection (standard/early release/assembly/custom)   |
|  - Rule resolution for time-triggered content                    |
+-------------------------------+----------------------------------+
                                |
                 +--------------+--------------+
                 |                             |
                 v                             v
+-------------------------------+   +------------------------------+
|      Bell Schedule Engine     |   |  Countdown Overlay Renderer  |
|  - Period/pass interval model |   |  - Countdown composition      |
|  - Event timeline generation  |   |  - Overlay presets/styling    |
+-------------------------------+   +------------------------------+
                 |                             |
                 +--------------+--------------+
                                |
                                v
+------------------------------------------------------------------+
|                 Anthias Content Scheduling Plane                 |
|   (Upstream scheduling/content capabilities used as baseline)    |
+-------------------------------+----------------------------------+
                                |
                                v
+------------------------------------------------------------------+
|               Player Endpoints (Raspberry Pi / Docker)           |
|  - Local cache  - Offline-safe behavior  - Screen group targeting |
+------------------------------------------------------------------+
```

## 3. Mapping Anthias Components to BellForge Needs

Because only `LICENSE` and documentation are currently present in this repository snapshot, this mapping is stated at capability level:

- Existing Anthias content scheduling baseline -> foundation for school-mode time orchestration
- Existing Anthias media/display baseline -> foundation for countdown overlays and warning screens
- Existing Anthias device deployment baseline -> foundation for Pi-first school endpoint strategy
- Existing Anthias administrative baseline -> foundation for role-oriented school/district control surfaces

Implementation-level mapping should be refined after source components are imported or linked in this repo.

## 4. Proposed New Components

### 4.1 Bell Schedule Engine

Responsibilities:

- Model day types and period structures
- Represent passing periods and bell events
- Generate normalized event timeline for downstream scheduler logic
- Support calendar-linked schedule variations

Core outputs:

- Active period state
- Upcoming bell event timestamps
- Trigger anchor points (for example, T-3m, T-1m, T+0)

### 4.2 Countdown Overlay Renderer

Responsibilities:

- Render time-remaining overlays for active/upcoming transitions
- Apply preset style themes suitable for classroom/hallway readability
- Compose overlays with underlying content
- Fail gracefully to baseline content if overlay generation is unavailable

Core outputs:

- Overlay payloads (text/time/progress style metadata)
- Render activation/deactivation events

### 4.3 School Mode Scheduler

Responsibilities:

- Resolve schedule context for the active date/time
- Evaluate trigger rules relative to bell events
- Select and dispatch content transitions across targeted screen groups
- Respect precedence rules (emergency override > school-mode trigger > normal schedule)

Core outputs:

- Effective display plan at time slice t
- Trigger execution log entries

### 4.4 District/School Management Layer

Responsibilities:

- Define hierarchical management model (district > school > building > hallway > room)
- Manage policy inheritance and local overrides
- Enforce role boundaries and delegated administration
- Provide aggregated operational visibility

Core outputs:

- Scope-aware configuration bundles
- Role-based policy decisions

## 5. Data Flow Diagrams

### 5.1 Bell-Driven Display Flow

```text
[Calendar Inputs: CSV/Google/iCal]
              |
              v
     [Bell Schedule Engine]
              |
    normalized event timeline
              |
              v
     [School Mode Scheduler] -----> [Emergency Override State]
              |                               |
              | precedence resolution         |
              +---------------+---------------+
                              |
                              v
             [Anthias Content Scheduling Plane]
                              |
                              v
                  [Player Endpoint Screen]
                              |
                              v
                [Countdown Overlay Renderer]
                              |
                              v
                    [Final Display Output]
```

### 5.2 Management and Configuration Flow

```text
[District Admin]      [School Admin]      [Teacher Preset User]
        |                    |                     |
        +---------+----------+----------+----------+
                  |                     
                  v
     [District/School Management Layer]
                  |
      policy + scope + role enforcement
                  |
                  v
          [School Mode Scheduler]
                  |
                  v
            [Screen Group Targets]
```

### 5.3 Offline-Safe Runtime Flow

```text
        [Control Plane Connectivity]
                 |         
         available? (Y/N)
            /           \
           Y             N
           |             |
           v             v
 [Fetch latest schedule] [Use cached schedule/content]
           |             |
           +-------> [Local Runtime Decision Engine]
                           |
                           v
                   [Continue bell-driven display]
```

## 6. Deployment Model

### 6.1 Raspberry Pi Model (Primary)

- Intended for classroom, hallway, and common-area screens
- Local cache required for schedule/content resilience
- Supports school-scale rollout with repeatable image strategy

### 6.2 Docker Model (Operational/Server Components)

- Suitable for management and orchestration services
- Enables consistent packaging for school or district infrastructure
- Supports CI/CD-aligned deployment workflows

### 6.3 Hybrid Model (Recommended Growth Path)

- Central services in Docker-backed environment
- Edge playback on Raspberry Pi endpoints
- Balances centralized governance with edge resilience

## 7. Cross-Cutting Concerns

- Reliability: deterministic bell-event handling and offline fallback
- Security: role-bound administrative actions, especially emergency controls
- Auditability: track critical operational state changes
- Observability: capture schedule resolution and trigger execution telemetry
- Maintainability: additive extension strategy to reduce upgrade friction

## 8. Assumptions and Unknowns

Assumptions:

- Upstream Anthias capabilities will remain available as a baseline scheduling/display platform.
- School operations need deterministic timing and explicit override precedence.

Unknowns to resolve in implementation planning:

- Exact integration points in Anthias code once source is present in this repository
- Preferred data model location for hierarchy and schedule entities
- Final rendering path for overlays across different player environments

## 9. Initial Implementation Guidance (Non-Binding)

1. Establish canonical schedule event model first.
2. Implement rule evaluation for time-triggered content next.
3. Add overlay rendering as composable layer with fallback behavior.
4. Introduce hierarchy-aware management controls in parallel with role model.
5. Validate offline behavior with controlled network-loss scenarios.
