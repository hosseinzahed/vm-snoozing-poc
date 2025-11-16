# Executive summary (one-line)

Here’s a clearer, more polished rephrasing:

---

Our organization is planning to identify and automatically snooze unused virtual machines in non-production subscriptions outside of business hours. We already have a method for locating the designated VMs in each subscription.

We want to build an agentic solution using the Microsoft Agent Framework—leveraging its workflow capabilities—to perform the following actions:

* Inspect existing code in a repository to determine whether the infrastructure is deployed using Terraform or Bicep, and understand its configuration.
* Create a new Git branch from the main branch.
* Generate the appropriate IaC code, based on the current infrastructure setup, to provision an Azure Automation Account in the target subscription.
* Add runbook tasks that shut down and start up VMs outside business hours within the Automation Account.
* Commit the generated code.
* Push the changes to the repository and open a pull request.
* Send a notification to an external system indicating that the PR has been created, along with its details.

The ideal solution should leverage the GitHub MCP and/or the GitHub Coding Agent via GitHub MCP, but it does not need to be limited to these tools.

Use a Microsoft Agent Framework workflow that calls deterministic tasks (repo inspection, branch creation, IaC generation, commit/PR) and delegates coding/PR work to a GitHub coding agent (via MCP) — with Azure operations carried out by a service principal or managed identity that the generated IaC deploys (Azure Automation account + runbooks or an equivalent Function App) — plus a human-in-the-loop approval gate for production-grade safety.

Key enabling pieces: Microsoft Agent Framework workflows (graph-based, human-in-loop, checkpointing), GitHub MCP to let agents act on repos and handoff to Copilot coding agent, GitHub PR API for PR creation/metadata, and Azure APIs/CLI for resource checks and runbook management. ([Microsoft Learn][2])

---

# High level architecture (components)

1. **Orchestrator — Microsoft Agent Framework (MAF) workflow**

   * Implements the decision logic: for each nominated VM in given non-prod subscription, inspect repository, branch, generate IaC, create PR, notify external system. Use workflow features for retries, checkpoints, human approvals, and parallelization. ([Microsoft Learn][2])

2. **Repository access via MCP / GitHub MCP Server**

   * MAF can call an MCP client that connects to GitHub MCP Server so the agent can read files, create branches, commit and open PRs programmatically using the MCP connector. Alternatively MAF triggers a separate GitHub workflow or calls the GitHub REST API directly. ([GitHub Docs][3])

3. **Coding agent (GitHub Copilot coding agent / other coding agent)**

   * Use Copilot coding agent (or a self-hosted coding-agent like `serena`) to generate IaC files (Bicep or Terraform) automatically into a feature branch, run basic linting/tests, and produce a PR. MCP allows extending Copilot to read repo context and act. ([GitHub Docs][4])

4. **Azure operator identity**

   * A short-lived service principal or federated identity (via OIDC from GitHub Actions or a managed identity in Azure) that has scoped contributor rights in the target non-prod subscriptions — used by the generated IaC when applied (or to validate resources) and for testing runbooks. Keep least privilege and log all actions.

5. **IaC generator**

   * The coding agent produces either Terraform or Bicep modules for:

     * `azurerm_automation_account` / `Microsoft.Automation/automationAccounts` (Automation Account)
     * Runbooks or Automation schedules for Stop/Start VMs (PowerShell / Az CLI)
     * Assigning a Runbook Worker (if needed) or using Hybrid Worker for on-prem
   * The agent should generate idempotent code that checks `exists` before create.

6. **CI checks**

   * A GitHub Actions workflow (or MAF step) runs: IaC lint (tflint/terraform validate or Bicep linter), unit tests (where feasible), and possibly a dry-run plan.

7. **PR + Notifications**

   * Once PR is created by the Copilot coding agent (or the orchestrator), MAF posts PR metadata to the target external system (via webhook or REST), including PR URL, branch, commits, list of generated files and a summary of the changes.

8. **Human approval (optional / recommended)**

   * A manual review step for PR approval before the IaC is merged and applied (especially for new subscriptions, or changes that modify RBAC or network settings).

9. **Deployment**

   * Either (A) after PR merge, GitHub Actions applies the IaC (Terraform apply or Azure CLI/Bicep deployment) using OIDC to authenticate to Azure, or (B) the generated IaC triggers a separate MAF task to do the apply.

---

# End-to-end flow (detailed steps)

1. **Trigger**

   * MAF workflow triggered by schedule or event (list of nominated VMs passed as input per subscription). MAF instantiates a run per subscription (parallelizable). ([Microsoft Learn][2])

2. **Repo inspection** (deterministic function)

   * MAF calls a tool step that clones / reads the infra repo (via MCP/GitHub API). Detect whether infra for that subscription is Bicep or Terraform:

     * Look for files like `main.bicep`, `*.bicep`, `*.tf`, `terraform.tfstate`, or pipeline conventions.
     * Also detect repository patterns: monorepo per subscription or per environment. (If ambiguous, default to repo’s majority pattern.)

   *(Important: do NOT change repo yet — this is read only.)* ([GitHub][5])

3. **Create branch**

   * Use the GitHub API (or MCP server call) to create a branch name like `agent/snooze-automation/<subscription>-<date>` from `main` (or repo’s default branch).

4. **Delegate code generation to coding agent** (MCP)

   * MAF uses MCP to send the coding task to Copilot coding agent (or internal coding agent). Payload:

     * repo context (paths/files found), sample existing IaC patterns, subscription id, runbook name and schedule (office hours).
     * instruction: “Generate <Bicep|Terraform> module that creates an Automation Account `snooze-automation-{subscription}` with Runbooks `Start-VMs` and `Stop-VMs`. Add schedules using cron or Azure schedule resources for off-hours start/stop. Ensure idempotency, use tags, and include parameterized lists of targeted VMs. Add unit test / validate files and pipeline change.”
   * Copilot coding agent writes code into the branch, runs lint/test where possible, and prepares a PR draft. This is what MCP + Copilot enables — agentic edits and PR creation. ([GitHub Docs][4])

5. **Orchestrator validates**

   * MAF runs automated checks: lint, terraform/bicep validation, policy checks (Azure Policy compliance), scanning for secrets (git-secrets), and a dry deployment plan. If any check fails, mark PR as "Changes requested" or reopen agent task.

6. **Commit & PR**

   * Agent commits generated files, pushes branch, opens PR against `main`. PR body should include:
   * Summary of changes, list of generated files, affected subscriptions, proposed schedule (with time zone), security considerations, test results, and an automated checklist.

7. **Notify external system**

   * MAF posts PR metadata (title, URL, branch, checks status, CI artefacts) to the external system via REST webhook or message bus so that downstream system shows the PR was generated with details.

8. **Human review & merge**

   * Reviewer inspects PR. Optionally the MAF workflow pauses and resumes on approval (human-in-the-loop). After merge, deployment can be auto-applied by a protected GitHub Actions workflow that uses OIDC to authenticate to Azure.

9. **Post-deploy verification**

   * After apply, run a verification step: check Automation Account exists, the runbooks are published and schedules exist, and the runbooks can target VMs by name/tag. Optionally do a dry run like `Stop` on a test VM or simulate.

10. **Operational run**

* Automation Account runbooks execute on schedule to stop/start nominated VMs. Use logging to storage account/Log Analytics. Workflow ends and MAF logs the whole execution trace.

---

# Example artifacts (short examples & PR template)

### Example PR body (template)

```
Title: [agent] add Automation Account + Runbooks to manage off-hours VM snooze for subscription <SUB_ID>

Summary:
- Adds Automation Account: snooze-automation-<SUB_ID>
- Adds Runbooks: Stop-TargetedVMs, Start-TargetedVMs (PowerShell Az)
- Adds schedule: Stop at 18:30 Europe/Copenhagen Mon-Fri, Start at 07:30 Europe/Copenhagen Mon-Fri
- Params: list of VM resource IDs or tag selector (env=nonprod, snooze=true)

Files generated:
- infra/automation/snooze-<sub>.tf
- infra/automation/runbooks/Stop-TargetedVMs.ps1
- infra/automation/runbooks/Start-TargetedVMs.ps1
- .github/workflows/ci-iac.yml (IaC lint/validate)

Validation:
- terraform fmt & validate passed
- bicep build passed
- static secret-scan passed

Action required:
- Reviewer: confirm schedules, VM selection logic, and least-privilege for managed identity.
```

### Minimal Bicep snippet idea (conceptual)

```bicep
param automationAccountName string = 'snoozeAutomation${uniqueString(subscription().subscriptionId)}'
resource aa 'Microsoft.Automation/automationAccounts@2022-08-08' = {
  name: automationAccountName
  location: resourceGroup().location
  properties: {}
  tags: {
    managedBy: 'agent-snoozer'
    environment: 'nonprod'
  }
}
```

*(Runbooks would be uploaded using `Microsoft.Automation/automationAccounts/runbooks` resource, or post-deployment via Az PowerShell.)*

---

# Important design choices & options (tradeoffs)

1. **Automation engine: Azure Automation vs Functions**

   * *Azure Automation* gives built-in Runbooks, schedules, and integration with Hybrid Runbook Worker. Good fit if you want PowerShell Runbooks.
   * *Azure Functions* + Timer Trigger + MSI can be simpler/cheaper for small tasks, easier to deploy as code (az cli / zip deploy).
   * Recommendation: start with Azure Automation for parity with “automation account” ask; design runbooks as idempotent PowerShell with retry/backoff.

2. **Where to run IaC apply**

   * Option A: Apply only after PR merge using GitHub Actions with OIDC to Azure (strongly recommended). That centralizes CI/CD and uses Git provider trust.
   * Option B: Agent (MAF) applies the IaC directly — useful if you want the agent to own deploys. Either is viable; Option A better aligns with GitOps practices.

3. **Coding agent approach**

   * Preferred: Copilot coding agent via MCP (can autonomously create PRs). Alternatively use an internal coding agent (open source) if you must keep everything on-prem or avoid Copilot licensing. ([GitHub Docs][4])

4. **VM targeting**

   * Implement multiple targeting modes:

     * explicit VM resource IDs
     * tag selector (recommend `snooze=true` + `environment=nonprod`)
     * name patterns
   * Tagging approach is scalable and less error-prone.

---

# Security, permissions, and governance

* **Least privilege:** Service principal / managed identity used to create Automation Accounts should be scoped to the subscription/resource group and only to required resource actions (Microsoft.Automation/* create/update, Microsoft.Compute/virtualMachines/* for Runbook operations).
* **Short-lived creds:** Use GitHub OIDC for CI (no long lived PAT where possible), or use federated identity with Azure AD.
* **Signing & accountability:** All agent commits should include a bot identity, and require human review for merges. Log all agent actions into a secure log (Log Analytics or SIEM).
* **Secret management:** Store credentials/secrets in Azure Key Vault and reference via Managed Identity. Do not let agents embed secrets into PRs. Use pre-commit scanning.
* **Policy guardrails:** Use Azure Policy to prevent creation of certain resource types or to require tags; validate generated IaC with policy checks.
* **PR review controls:** Protect `main` branch; require required reviewers or at least one human approval for any IaC that changes RBAC or network settings.

---

# Edge cases & failure modes (with mitigations)

* **Repo detection ambiguous** — fallback to a conservative template and surface the ambiguity in the PR; pause for human decision if multiple infra styles present.
* **Automation account already exists** — generated IaC must check for existence and only add runbooks or update schedules; tests should detect collisions and fail fast.
* **Multiple agents editing same repo** — use branch naming conventions and coordinate via locks (a simple file lock in repo or orchestrator mutex).
* **Agent hallucination in code generation** — enforce strict CI checks, static analyzers, and run sandboxed unit tests BEFORE committing.
* **Time zone / business hours differences** — use explicit timezone parameters (user indicated Europe/Copenhagen) and convert to cron/time schedule. Always include explicit timestamps in PR.
* **VMs with special state (deallocated vs stopped)** — Ensure runbooks use the correct VM state API (`Stop-AzVM -Force` vs `Start-AzVM`) and handle VM Scale Sets differently.

---

# Observability & auditing

* MAF workflow tracing (built-in) + GitHub PR + Git history for code audit. ([GitHub][6])
* Log runbook executions to Log Analytics (include runbook output and structured telemetry).
* Emit events (webhooks) to the external system at major milestones: branch created, PR opened, PR merged, apply succeeded, runbook first run.

---

# Implementation plan (recommended phases)

1. **Prototype (1–2 sprints)**

   * Build a MAF workflow that reads a repo and detects Bicep/Terraform.
   * Wire MCP to allow the MAF workflow to request a coding agent to create a branch and add a trivial IaC file.
   * Create a simple PR and notify an external system.

2. **MVP (next 2–4 sprints)**

   * Coding agent generates full Automation Account + runbooks for one sample subscription.
   * Implement CI checks (IaC lint/validate), PR template, and notification hooks.
   * Deploy Automation Account via GitHub Actions with OIDC.

3. **Harden & scale**

   * Add RBAC checks, policy scans, human approvals, concurrency controls.
   * Add monitoring, secrets management via Key Vault and thorough testing.
   * Expand to multiple subscriptions and selector logic (tags, names).

4. **Operations & docs**

   * Document runbook behavior, rollback process, on-call runbook, and runbook emergency stop.
   * Train reviewers and run a pilot.

---

# Minimal tech stack + libraries

* Microsoft Agent Framework (workflows + agents). ([Microsoft Learn][1])
* GitHub MCP Server (for agent ↔ repo integration) and Copilot coding agent (or an internal coding agent if needed). ([GitHub][5])
* GitHub Actions (for CI and apply via OIDC), or MAF apply step.
* Terraform or Bicep (based on repo detection).
* Azure Automation (or Azure Functions) runbooks with Az PowerShell modules.
* Azure Key Vault, Azure AD service principals / federated credentials.
* Monitoring: Log Analytics + alerts.

---

# Short sample MAF workflow pseudocode (conceptual)

```python
# Pseudocode to illustrate steps inside MAF workflow
workflow snooze_infra(subscription, vm_list):
  repo_ctx = call(tool=github.read_repo, repo='infra-repo')
  infra_type = call(tool=detect_infra_type, repo_ctx)
  branch = call(tool=github.create_branch, base='main', name=f'agent/snooze/{subscription}')
  coding_task = {
    "repo": 'infra-repo',
    "branch": branch,
    "infra_type": infra_type,
    "target_subscription": subscription,
    "vm_selector": vm_list or "tag:snooze=true"
  }
  pr = delegate_to_coding_agent_via_mcp(task=coding_task)   # Copilot coding agent
  checks = run(ci.validate_iac, pr.branch)
  if not checks.passed:
    post_notification(external_system, pr, status='failed_checks')
    return failure
  post_notification(external_system, pr, status='pr_created')
  await human_approval(pr)  # optional pause
  on_merge = subscribe_to_github_event('pull_request', action='merged', branch=pr.branch)
  if on_merge:
    run(deploy_iac, pr.branch)
    post_notification(external_system, pr, status='deployed')
```

(Implement with MAF nodes / graph primitives, using MAF’s human-in-loop, checkpoints and retries.) ([Microsoft Learn][2])

---

# Recommendations / final notes

* **Use MCP + Copilot coding agent** for the fastest path to an agentic repo edit + PR flow. MCP provides the standard plumbing to safely let an agent read and write repo content; Copilot coding agent can autonomously create PRs and run tests. Ensure you meet Copilot licensing for your org. ([GitHub Docs][3])
* **Force strong CI and human approval** before any IaC is merged/applied — agents can speed work but must not bypass governance.
* **Start small and iterate**: prove for a single non-prod subscription and a single tag-based VM selector, then expand.
* **Logging & auditability** are essential; use MAF’s trace + Git history + Azure logs for complete traceability. ([GitHub][6])

---

If you want, I can now:

* produce an exact Agent Framework workflow file (Python or .NET pseudo-implementation) implementing the steps above, or
* sketch the GitHub MCP payload to delegate to Copilot coding agent, or
* generate a concrete Bicep and PowerShell runbook pair for a single subscription (with schedules in Europe/Copenhagen) that the coding agent could produce.

Tell me which artifact you want first and I’ll generate it right away (workflow file, MCP payload, IaC sample + runbook, or a PR template + GitHub Actions workflow).

[1]: https://learn.microsoft.com/en-us/agent-framework/overview/agent-framework-overview?utm_source=chatgpt.com "Introduction to Microsoft Agent Framework"
[2]: https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/overview?utm_source=chatgpt.com "Microsoft Agent Framework Workflows"
[3]: https://docs.github.com/en/copilot/concepts/agents/coding-agent/mcp-and-coding-agent?utm_source=chatgpt.com "Model Context Protocol (MCP) and GitHub Copilot coding ..."
[4]: https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent?utm_source=chatgpt.com "About GitHub Copilot coding agent"
[5]: https://github.com/github/github-mcp-server?utm_source=chatgpt.com "GitHub's official MCP Server"
[6]: https://github.com/microsoft/agent-framework?utm_source=chatgpt.com "Microsoft Agent Framework"
