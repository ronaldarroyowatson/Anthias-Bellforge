# Anthias-Bellforge Roadmap

## Document Control

- Project: Anthias-Bellforge
- Purpose: Define phased delivery path for school-focused Anthias extension
- Status: Draft (Initial Foundation)
- Last updated: 2026-05-01

## Roadmap Principles

- Deliver in small, testable increments
- Preserve additive compatibility with Anthias baseline where feasible
- Prioritize school operational reliability and timing accuracy
- Validate each phase with pilot-ready acceptance criteria

## Phase 1: Documentation + Minimal School Mode

### Objectives

- Establish foundational project documentation
- Define initial school mode concept and minimal operational behavior
- Create a common vocabulary for schedules, triggers, and hierarchy

### Scope

- README, PRD, Architecture, and Roadmap documents
- Minimal school mode definition (non-production, baseline behavior)
- Decision log for unresolved architecture and governance choices

### Deliverables

- Completed documentation set in docs/
- Initial glossary and assumptions baseline
- Initial risk register and dependency list

### Exit Criteria

- Core stakeholders can review project intent, scope, and phased plan
- Product and architecture docs are internally consistent
- MVP scope boundary is clear for implementation kickoff

## Phase 2: Bell Schedule Engine + Countdown Overlays

### Objectives

- Implement deterministic bell schedule modeling
- Enable trigger-based warning content and countdown overlays

### Scope

- Day types: standard, early release, assembly, custom
- Period and passing-period timeline generation
- Trigger rules relative to bell events (for example T-3 minutes)
- Countdown overlay rendering with preset styles

### Deliverables

- Bell Schedule Engine (initial production-capable version)
- Countdown Overlay Renderer (initial production-capable version)
- Validation scenarios for timing accuracy and visual behavior

### Exit Criteria

- Pilot configuration can produce correct bell-event timeline
- Pre-bell warnings and countdown overlays display at expected times
- Fail-safe behavior is defined for overlay/render failures

## Phase 3: Multi-Screen Management

### Objectives

- Support school topology-aware screen targeting
- Enable hierarchy-based configuration with inheritance

### Scope

- Hierarchy model: school, building, hallway, room
- Targeted scheduling and content assignment by group
- Inheritance + override rules for localized behavior
- Basic operational views for screen-group status

### Deliverables

- Screen hierarchy and targeting model
- Group-based assignment workflows
- Inheritance policy and conflict-resolution rules

### Exit Criteria

- Pilot school can manage multiple screens by location hierarchy
- Group targeting works for routine and bell-triggered content
- Override behavior is consistent and auditable

## Phase 4: District-Level Cloud Management

### Objectives

- Introduce district-scale governance and central oversight
- Provide scoped autonomy for school-level administration

### Scope

- District > school management model
- Role boundaries and delegated administration
- Policy templates with school-level overrides
- Aggregated fleet visibility and high-level reporting

### Deliverables

- District/School Management Layer (initial release)
- Role and policy model documentation
- Cross-school configuration and monitoring baseline

### Exit Criteria

- District admins can apply template policies across schools
- School admins can perform approved local overrides
- Governance and access controls meet pilot policy expectations

## Phase 5: Raspberry Pi Image Automation

### Objectives

- Simplify and standardize endpoint provisioning
- Improve reliability and consistency of school deployments

### Scope

- Automated Pi image build process
- Baseline secure/default configuration profile
- Device bootstrap and enrollment workflow
- Update strategy for controlled rollout

### Deliverables

- Pi image automation pipeline
- Provisioning and operations runbook
- Device lifecycle guidance (install, update, recover)

### Exit Criteria

- New devices can be provisioned repeatably with minimal manual steps
- Pilot IT staff can execute documented deployment workflow
- Recovery and rollback procedures are documented and tested

## Phase 6: Teacher-Friendly UI Presets

### Objectives

- Reduce complexity for non-technical users
- Accelerate common classroom and hallway messaging tasks

### Scope

- Preset library for common school scenarios
- Simplified workflows for warning screens and transitions
- Role-aware UI constraints to protect administrative controls
- Usability-focused documentation and quick-start guides

### Deliverables

- Teacher preset experience (initial release)
- Preset templates and usage guidance
- Usability validation summary from pilot participants

### Exit Criteria

- Teachers can execute common signage tasks with minimal steps
- Presets reduce setup time versus manual configuration
- School leadership confirms operational usefulness in daily workflows

## Cross-Phase Workstreams

- Emergency override messaging model and validation
- Offline-safe behavior with local caching and continuity checks
- Calendar integration path (CSV, Google Calendar, iCal)
- Quality, observability, and auditability improvements

## Risks and Mitigations

- Risk: Timing drift or trigger inaccuracies
- Mitigation: Add deterministic schedule tests and real-time pilot validation windows

- Risk: Operational complexity for school staff
- Mitigation: Prioritize defaults, presets, and role-scoped workflows

- Risk: Deployment inconsistency across hardware
- Mitigation: Automate image creation and enforce baseline configuration profiles

- Risk: Governance friction between district and school control
- Mitigation: Define explicit override boundaries and policy precedence early

## Dependencies

- Availability of upstream Anthias baseline for integration work
- Pilot school participation for operational validation
- IT readiness for endpoint provisioning and network policy support

## Immediate Next Actions

1. Confirm phase acceptance criteria with stakeholders.
2. Prioritize Phase 2 MVP backlog items.
3. Define test scenarios for bell timing, trigger rules, and offline operation.
4. Establish pilot environment for early validation.
