# Product Requirements Document (PRD)

## Document Control

- Project: Anthias-Bellforge
- Purpose: Define school-focused product requirements for extending Anthias into a bell-aware digital signage platform
- Status: Draft (Initial Foundation)
- Last updated: 2026-05-01

## 1. Problem Statement

Schools rely on precise, time-sensitive communication tied to bell schedules, class transitions, and safety events. Traditional digital signage workflows are often too generic for bell-driven operations and do not provide first-class support for period-based timing, countdown cues, or school hierarchy (district > school > building > screen).

Anthias-Bellforge aims to establish a maintainable, school-oriented extension path that supports operational clarity, student movement coordination, and emergency communication reliability while preserving the deployability strengths of Anthias.

## 2. Target Users

### 2.1 Teachers

- Need simple, preset-driven controls for classroom and hallway messaging
- Need predictable countdown and transition cues before tardy or class bells
- Need low-friction content workflows that do not require technical expertise

### 2.2 Principals and School Leadership

- Need consistent school-wide messaging aligned to daily schedules
- Need rapid override capabilities for announcements and emergency messaging
- Need visibility into whether critical messages are displayed as intended

### 2.3 IT Administrators (School or District)

- Need centralized management across multiple screens and locations
- Need resilient deployments that continue functioning during network outages
- Need repeatable provisioning, updates, and operational monitoring for Pi-based endpoints

## 3. User Stories

1. As a teacher, I want a preset to show a class-end warning 3 minutes before the bell so students can prepare to transition.
2. As a principal, I want school-wide emergency override messaging so urgent instructions can replace normal content immediately.
3. As an IT admin, I want screens organized by school, building, hallway, and room so targeted content can be delivered precisely.
4. As a front-office staff member, I want early-release schedules to activate automatically on specific dates so manual schedule switching is minimized.
5. As a district admin, I want policy-level templates with school-level overrides so messaging remains consistent but locally adaptable.
6. As a teacher, I want a countdown overlay option that can be applied without designing custom media so setup time is minimal.
7. As an IT admin, I want local content caching and fallback schedules so displays remain useful during internet disruptions.
8. As scheduling staff, I want to import schedule events from CSV, Google Calendar, or iCal so schedule maintenance integrates with existing workflows.

## 4. Functional Requirements

### 4.1 Bell Schedule Management

- FR-1: System shall support schedule types including standard day, early release, assembly, and custom event day.
- FR-2: System shall model periods and passing periods with explicit start and end times.
- FR-3: System shall support date-bound schedule variants (for example, specific assemblies).
- FR-4: System shall allow manual day-type override by authorized roles.

### 4.2 Time-Triggered Content

- FR-5: System shall support rule-based triggers relative to bell events (for example, T-3 minutes).
- FR-6: System shall allow pre-bell warning screens and post-bell transition screens.
- FR-7: System shall support screen-group targeting for triggered content.

### 4.3 Countdown Overlays

- FR-8: System shall render countdown overlays tied to active or upcoming bell events.
- FR-9: System shall allow configurable overlay style presets suitable for classroom readability.
- FR-10: System shall support enabling/disabling overlays per screen group.

### 4.4 Multi-Screen School Deployment

- FR-11: System shall support hierarchical grouping: district, school, building, hallway, room.
- FR-12: System shall allow content and schedule assignment at any hierarchy level with inherited defaults.
- FR-13: System shall allow local overrides at lower hierarchy levels where permitted.

### 4.5 Centralized Management

- FR-14: System shall support school-level centralized management as a baseline.
- FR-15: System shall support district-level governance patterns in the architecture roadmap.
- FR-16: System shall expose role-based administration boundaries for teachers, school admins, and district admins.

### 4.6 Emergency Override Messaging

- FR-17: System shall allow authorized users to trigger immediate emergency override content.
- FR-18: Emergency override shall preempt routine schedules until cleared.
- FR-19: System shall record audit metadata for override activation and deactivation.

### 4.7 Teacher-Friendly Presets

- FR-20: System shall provide simple preset templates for common school scenarios.
- FR-21: System shall minimize required steps for non-technical users to activate a preset.

### 4.8 Deployment and Reliability

- FR-22: System shall support Raspberry Pi deployment as a first-class model.
- FR-23: System shall support local caching of required assets and schedule data.
- FR-24: System shall continue schedule-driven display behavior during temporary connectivity loss.

### 4.9 Calendar Integration

- FR-25: System shall support importing schedule data via CSV.
- FR-26: System shall define integration path for Google Calendar feeds.
- FR-27: System shall define integration path for iCal-compatible feeds.

## 5. Non-Functional Requirements

- NFR-1: Reliability: Core schedule display behavior should remain available during intermittent network failure.
- NFR-2: Performance: Triggered transitions and overlays should appear in time for operational bell events.
- NFR-3: Usability: Teacher-facing actions should prioritize low cognitive load and clear defaults.
- NFR-4: Maintainability: Architecture and docs should support incremental extension without large rewrites.
- NFR-5: Security: Administrative actions, especially emergency override, should require authorized roles.
- NFR-6: Auditability: Critical operational actions should be traceable.
- NFR-7: Scalability: Design should support growth from single-school to district-wide deployments.

## 6. Constraints Inherited from Anthias

The following constraints are intentionally framed at a platform level to avoid asserting internals not yet verified in this repository snapshot:

- C-1: Anthias is the upstream platform baseline; Bellforge scope should be additive and compatible where feasible.
- C-2: Existing Anthias content scheduling paradigms influence integration shape for bell-aware logic.
- C-3: Existing Anthias deployment approaches influence operational rollout strategy.
- C-4: Existing Anthias administrative and user workflow patterns should guide UI/UX extension decisions.
- C-5: Upstream compatibility and maintainability concerns should be considered in implementation planning.

## 7. Success Criteria

### 7.1 Adoption and Usability

- SC-1: Pilot school users can configure and run bell-aware signage for at least one complete school day without developer intervention.
- SC-2: Teachers can activate at least one preset flow in minimal steps.

### 7.2 Operational Accuracy

- SC-3: Time-triggered warnings and countdown overlays align with configured bell event times in pilot validation.
- SC-4: Early-release and assembly day schedule variants can be switched by date or override control.

### 7.3 Reliability and Resilience

- SC-5: Pilot screens continue operating with cached schedule/content during temporary connectivity loss.
- SC-6: Emergency override can be activated and cleared with auditable records.

### 7.4 Deployment and Scale Readiness

- SC-7: Baseline deployment guidance supports Raspberry Pi targets.
- SC-8: Architecture and roadmap clearly define path from school-level management to district-level management.

## 8. Out of Scope for Initial Foundation

- Direct implementation details of Anthias internals not present in this repository snapshot
- Finalized UI design system and production-ready visual components
- Full district cloud control-plane implementation
- Complete automated provisioning pipeline for all hardware variants

## 9. Open Decisions

1. Governance model priority: school-first autonomy vs district-first policy control.
2. Preferred source of truth for calendar ingestion in early phases: CSV-first vs calendar-feed-first.
3. Emergency override authority model granularity across roles.
4. Minimum offline duration target for cached operations in pilot environments.
