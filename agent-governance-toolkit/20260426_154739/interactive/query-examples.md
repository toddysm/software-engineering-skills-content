# Interactive Dependency Query Examples

The dependency database produced by this analysis can answer "what depends on what" questions. Use the `dependency_query_engine.py` script:

```sh
cd /Users/toddysm/Documents/Development/software-engineering-skills

# Interactive REPL
.venv/bin/python3 .github/skills/codebase-architecture-analyst/scripts/dependency_query_engine.py \
  /Users/toddysm/Documents/Development/software-engineering-skills-content/agent-governance-toolkit/20260426_154739 \
  --interactive

# Single query
.venv/bin/python3 .github/skills/codebase-architecture-analyst/scripts/dependency_query_engine.py \
  /Users/toddysm/Documents/Development/software-engineering-skills-content/agent-governance-toolkit/20260426_154739 \
  --query "What depends on policy_evaluator.py?"

# Built-in examples
.venv/bin/python3 .github/skills/codebase-architecture-analyst/scripts/dependency_query_engine.py \
  /Users/toddysm/Documents/Development/software-engineering-skills-content/agent-governance-toolkit/20260426_154739 \
  --examples
```

Or open the **interactive force-directed graph** in your browser:

```sh
open /Users/toddysm/Documents/Development/software-engineering-skills-content/agent-governance-toolkit/20260426_154739/dependencies/dependency-graph.html
```

---

## Recommended queries for this codebase

### Architecture exploration
- *What depends on `packages/agent-mesh/src/agentmesh/governance/policy_evaluator.py`?* — gauge blast radius before changing the Python policy evaluator.
- *What does `agent-governance-dotnet/src/AgentGovernance/GovernanceKernel.cs` depend on?* — inspect the .NET kernel surface.
- *What does `packages/agent-mesh/src/agentmesh/integrations/mcp/__init__.py` depend on?* — MCP attack surface.
- *Show me the dependency tree for `packages/agent-hypervisor/src/hypervisor/session/__init__.py`.*

### Security-driven queries
- *Show me all files importing `subprocess`* — pre-staged on bandit B603 (32 hits).
- *Show me all files importing `pickle` or `marshal`* — deserialization risk surface.
- *Show me all files importing `huggingface_hub`* — supply-chain (VULN-001) review surface.
- *What depends on `packages/agent-os/.../hf_utils.py`?* — find call sites of unpinned downloads.
- *What depends on `agent-governance-dotnet/.../FileTrustStore.cs`?* — review trust-store consumers.

### Refactoring impact
- *If I modify `packages/agent-mesh/src/agentmesh/identity/namespace_manager.py`, what is affected?*
- *Show me all circular dependencies.* (Answer: none — this codebase has 0 circular deps at module level.)
- *What are the entry points to the system?* — main scripts, CLI entrypoints, MCP server entry, demo apps.

### Cross-language consistency check
- *Files in `agent-governance-dotnet/.../Mcp/` vs files matching `packages/agentmesh*/integrations/mcp/`* — check feature parity.

---

## Tips

- The query engine is regex-aware; partial filenames work (`policy_evaluator` resolves to the full path).
- For huge result sets, pipe through `head` or use the HTML graph's search box instead.
- The graph database is rebuilt only when you re-run the deep dependency analyzer.
