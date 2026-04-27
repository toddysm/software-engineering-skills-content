# Component Guide

## Central Components

These components are heavily used throughout the system. Changes here have wide impact:

### pytest

**File**: `pytest`

**Used by**: 211 other components

**Key dependent files**: packages/agent-os/modules/cmvk/tests/test_verification.py, packages/agent-discovery/tests/test_models.py, packages/agent-os/tests/test_mcp_server.py

### os

**File**: `os`

**Used by**: 151 other components

**Key dependent files**: packages/agent-os/examples/copilot_governed.py, packages/agent-os/examples/self-evaluating/examples/sample_full_stack_agent.py, packages/agent-os/modules/iatp/examples/run_untrusted_sidecar.py

### sys

**File**: `sys`

**Used by**: 123 other components

**Key dependent files**: packages/agent-os/examples/copilot_governed.py, packages/agent-os/modules/cmvk/tests/unit/test_core.py, packages/agent-os/modules/caas/src/caas/cli.py

### json

**File**: `json`

**Used by**: 114 other components

**Key dependent files**: packages/agentmesh-integrations/a2a-protocol/tests/test_a2a.py, packages/agent-sre/tests/unit/test_rogue_detector.py, packages/agent-os/modules/caas/src/caas/storage/store.py

### time

**File**: `time`

**Used by**: 92 other components

**Key dependent files**: packages/agent-os/tests/test_e2e_governance_pipeline.py, packages/agent-os/tests/test_semantic_policy_engine.py, packages/agent-os/examples/self-evaluating/examples/example_circuit_breaker.py

## Component Categories

### Test (949 files)

- **maf_governance_demo**: `demo/maf_governance_demo.py` - Agent Governance Toolkit — Live Governance Demo

Demonstrates real-time governance enforcement using...
- **IdentityLifecycleTests**: `agent-governance-dotnet/tests/AgentGovernance.Tests/IdentityLifecycleTests.cs`
- **ComprehensiveAdvancedTests**: `agent-governance-dotnet/tests/AgentGovernance.Tests/ComprehensiveAdvancedTests.cs`
... and 946 other files

### Unknown (737 files)

- **demo_data**: `demo/governance-dashboard/demo_data.py` - Demo data generator for the governance dashboard.
- **AgentGovernance.GlobalUsings.g**: `agent-governance-dotnet/src/AgentGovernance/obj/Debug/net8.0/AgentGovernance.GlobalUsings.g.cs`
- **AgentGovernance.Extensions.Microsoft.Agents.GlobalUsings.g**: `agent-governance-dotnet/src/AgentGovernance.Extensions.Microsoft.Agents/obj/Debug/net8.0/AgentGovernance.Extensions.Microsoft.Agents.GlobalUsings.g.cs`
... and 734 other files

### Application (10 files)

- **app**: `demo/governance-dashboard/app.py` - Agent Governance Dashboard - Real-time agent fleet visibility.
- **.NETCoreApp,Version=v8.0.AssemblyAttributes**: `agent-governance-dotnet/src/AgentGovernance/obj/Debug/net8.0/.NETCoreApp,Version=v8.0.AssemblyAttributes.cs`
- **AgentGovernance.AssemblyInfo**: `agent-governance-dotnet/src/AgentGovernance/obj/Debug/net8.0/AgentGovernance.AssemblyInfo.cs`
... and 7 other files

### Entry Point (170 files)

- **03_contoso_support**: `demo/maf-integration/03_contoso_support.py` - Demo 3: Contoso Support — Prompt injection detection with MAF

Shows how GovernancePolicyMiddleware ...
- **01_contoso_bank**: `demo/maf-integration/01_contoso_bank.py` - Demo 1: Contoso Bank — AGT governance in Microsoft Agent Framework (MAF)

Shows how to wire AGT's go...
- **02_helpdesk_it**: `demo/maf-integration/02_helpdesk_it.py` - Demo 2: HelpDesk IT — Capability-guarded tool access with MAF

Shows how CapabilityGuardMiddleware r...
... and 167 other files

### Data Model (33 files)

- **GovernedMcpServerTool**: `agent-governance-dotnet/src/AgentGovernance.Extensions.ModelContextProtocol/GovernedMcpServerTool.cs`
- **GovernanceMcpServerOptionsSetup**: `agent-governance-dotnet/src/AgentGovernance.Extensions.ModelContextProtocol/GovernanceMcpServerOptionsSetup.cs`
- **.NETCoreApp,Version=v8.0.AssemblyAttributes**: `agent-governance-dotnet/src/AgentGovernance.Extensions.ModelContextProtocol/obj/Debug/net8.0/.NETCoreApp,Version=v8.0.AssemblyAttributes.cs`
... and 30 other files

### Library (2 files)

- **lib**: `agent-governance-rust/agentmesh-mcp/src/lib.rs`
- **lib**: `agent-governance-rust/agentmesh/src/lib.rs`

### Module (2 files)

- **mod**: `agent-governance-rust/agentmesh-mcp/src/mcp/mod.rs`
- **mod**: `agent-governance-rust/agentmesh/src/mcp/mod.rs`

### Configuration (15 files)

- **tailwind.config**: `packages/agent-os-vscode/tailwind.config.js`
- **tsup.config**: `packages/agentmesh-integrations/copilot-governance/tsup.config.ts`
- **tsup.config**: `packages/agentmesh-integrations/mastra-agentmesh/tsup.config.ts`
... and 12 other files

### Utility (12 files)

- **serverHelpers**: `packages/agent-os-vscode/src/server/serverHelpers.ts` - Server Helper Functions Utility functions for the governance server including port detection and cli...
- **escapeHtml**: `packages/agent-os-vscode/src/utils/escapeHtml.ts` - HTML Escape Utility Single source of truth for HTML entity escaping across the extension. Used by ex...
- **mockUtils**: `packages/agent-os-vscode/src/mockBackend/mockUtils.ts` - Shared utilities for mock backend services. Provides bounded random-walk helpers used by both MockSL...
... and 9 other files

### Ui Component (88 files)

- **detailFetchers**: `packages/agent-os-vscode/src/webviews/sidebar/detailFetchers.ts` - Detail Fetchers Rich data fetchers for promoted detail webview panels. Each function maps raw provid...
- **PanelPicker**: `packages/agent-os-vscode/src/webviews/sidebar/PanelPicker.tsx` - PanelPicker Overlay Full-screen overlay for assigning panels to the 3 sidebar slots. Uses draft stat...
- **main**: `packages/agent-os-vscode/src/webviews/sidebar/main.tsx` - Sidebar Entry Point Mounts the 3-slot sidebar React app into the webview.
... and 85 other files

### Controller (2 files)

- **scanController**: `packages/agent-os-vscode/src/webviews/sidebar/scanController.ts` - Scan Controller Pure functions for sidebar scan rotation logic. No React, no timers, no side effects...
- **handler**: `packages/agent-sre/src/agent_sre/integrations/llamaindex/handler.py` - LlamaIndex Callback Handler for Agent-SRE
==========================================

Automatically ...

### Service (44 files)

- **liveClient**: `packages/agent-os-vscode/src/services/liveClient.ts` - Live SRE Client HTTP client that polls agent-failsafe REST endpoints and caches the latest snapshot....
- **sreServer**: `packages/agent-os-vscode/src/services/sreServer.ts` - SRE Server Lifecycle Manager Manages a local agent-failsafe REST server subprocess. Spawns on activa...
- **providerFactory**: `packages/agent-os-vscode/src/services/providerFactory.ts` - Provider Factory Creates data providers for the governance dashboard. On activation, attempts to sta...
... and 41 other files

### Web Server (2 files)

- **server**: `packages/agentmesh-integrations/copilot-governance/src/server.ts` - Lightweight HTTP server for the GitHub Copilot governance extension. Exposes a single POST endpoint ...
- **server**: `packages/agent-os/extensions/mcp-server/src/server.ts` - AgentOS MCP Server - Core Server Implementation Exposes AgentOS capabilities through Model Context P...

### React Component (3 files)

- **index**: `packages/agent-os/extensions/chrome/src/options/index.tsx`
- **index**: `packages/agent-os/extensions/chrome/src/popup/index.tsx`
- **App**: `packages/agent-os/extensions/chrome/src/popup/App.tsx`

### Api (9 files)

- **api**: `packages/agent-os/extensions/chrome/src/shared/api.ts` - AgentOS API Client
- **server**: `packages/agent-os/modules/caas/src/caas/api/server.py` - REST API for Context-as-a-Service.
- **__init__**: `packages/agent-os/modules/caas/src/caas/api/__init__.py` - API module initialization.
... and 6 other files

## Common Interaction Patterns

### API-Service Pattern

API controllers delegate business logic to service components

**Example**: demo/maf_governance_demo.py → demo/maf-integration/02_helpdesk_it.py

### Service-Data Pattern

Services access data through model or repository components

**Example**: demo/maf-integration/02_helpdesk_it.py → demo/maf_governance_demo.py

## Modification Guidance

**Modifying core components**: When changing pytest, os, sys, test thoroughly as these components affect many other parts of the system.

**API changes**: When modifying API endpoints, update documentation and consider backward compatibility for existing clients.

**Database schema changes**: When changing data models, create migration scripts and update all dependent services.

