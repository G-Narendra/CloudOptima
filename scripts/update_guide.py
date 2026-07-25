"""
Update CloudOptima Master Guide HTML with 5 new sections.
Reads the HTML, updates TOC, inserts sections 24-28, writes back.
Preserves all existing content (including Conclusion body text).
"""
from pathlib import Path

GUIDE = Path("docs/CLOUDOPTIMA_MASTER_GUIDE.html")
html = GUIDE.read_text("utf-8")
orig_len = len(html)

# Markers for success/failure (ASCII only for Windows cp1252 compat)
OK = "[OK]"
ERR = "[ERR]"

# ─── 1. NEW TOC ENTRIES ───────────────────────────────────────

new_toc = (
    '<li><a href="#24-team-onboarding-guide">Team Onboarding Guide</a></li>\n'
    '<li><a href="#25-roadmap--milestones">Roadmap &amp; Milestones</a></li>\n'
    '<li><a href="#26-microsoft-integration-points">Microsoft Integration Points</a></li>\n'
    '<li><a href="#27-known-limitations--technical-debt">Known Limitations &amp; Technical Debt</a></li>\n'
    '<li><a href="#28-team-workflow--git-strategy">Team Workflow &amp; Git Strategy</a></li>'
)

old_toc_end = (
    '<li><a href="#23-appendix-complete-file-reference">'
    'Appendix: Complete File Reference</a></li>\n</ol>'
)

if old_toc_end not in html:
    print(f"{ERR} Could not find TOC end marker")
    exit(1)

new_toc_end = old_toc_end.replace('</ol>', new_toc + '\n</ol>')
html = html.replace(old_toc_end, new_toc_end)
print(f"{OK} Updated TOC: inserted 5 new entries")

# ─── 2. NEW SECTIONS 24-28 (insert before Conclusion) ────────

new_sections = r"""
<hr class="section-divider">

<h2 id='24-team-onboarding-guide'>24. Team Onboarding Guide</h2>

<blockquote><strong>For new team members joining the CloudOptima collaboration. Read this first.</strong></blockquote>

<h3 id='24-1-team-structure'>24.1 Team Structure</h3>

<table><thead><tr><th>Role</th><th>Who</th><th>Primary Responsibilities</th></tr></thead><tbody>
<tr><td><strong>Lead Architect</strong></td><td>You (Project Lead)</td><td>Architecture decisions, code review gatekeeper, stakeholder communication, roadmap prioritization, final arbitration on design choices</td></tr>
<tr><td><strong>Microsoft Engineer 1</strong></td><td>Azure Infra Specialist</td><td>Azure OpenAI Service integration, CI/CD pipelines, Azure Monitor/App Insights, Microsoft Defender for Cloud</td></tr>
<tr><td><strong>Microsoft Engineer 2</strong></td><td>Cloud Security/Compliance</td><td>Azure AD / Entra ID auth, Azure Policy, Compliance automation, Cost Management API, Azure API Management</td></tr>
<tr><td><strong>Student 1</strong></td><td>Backend/Frontend Developer</td><td>Core Python (agent_base, orchestrator, models), Streamlit dashboard improvements, unit tests</td></tr>
<tr><td><strong>Student 2</strong></td><td>Data/ML Engineer</td><td>RAG compliance engine, LLM cache, prompt engineering, test coverage expansion, documentation</td></tr>
</tbody></table>

<h3 id='24-2-first-week-checklist'>24.2 First-Week Checklist</h3>

<table><thead><tr><th>Day</th><th>Task</th><th>Details</th></tr></thead><tbody>
<tr><td><strong>Day 1</strong></td><td>Environment Setup</td><td>Clone repo, install Python 3.12+, create venv, <code>pip install -r requirements.txt</code>, copy <code>.env.example</code> to <code>.env</code></td></tr>
<tr><td><strong>Day 1</strong></td><td>Run Locally</td><td><code>streamlit run dashboard.py</code> - verify UI loads. Run <code>python run.py</code> - verify CLI works</td></tr>
<tr><td><strong>Day 2</strong></td><td>Read Key Modules</td><td>Read through <code>models.py</code>, <code>agent_base.py</code>, <code>agent_schemas.py</code>, <code>orchestrator.py</code> in order</td></tr>
<tr><td><strong>Day 2</strong></td><td>Run Tests</td><td><code>pytest tests/ -v</code> - all ~200 tests should pass. Fix any failures</td></tr>
<tr><td><strong>Day 3</strong></td><td>Run a Demo Session</td><td>Open dashboard, enter a sample request, observe agent execution flow end-to-end</td></tr>
<tr><td><strong>Day 3</strong></td><td>First Small PR</td><td>Fix a TODO, improve a test, or add a docstring. Get familiar with the PR workflow (Section 28)</td></tr>
<tr><td><strong>Day 4</strong></td><td>Read Architecture Guide</td><td>Read the Master Guide (this document) sections 1-23 to understand full system design</td></tr>
<tr><td><strong>Day 5</strong></td><td>Pick a Task from Roadmap</td><td>Select a Phase 1 task from Section 25 and start implementation with a design brief</td></tr>
</tbody></table>

<h3 id='24-3-development-environment'>24.3 Development Environment</h3>

<h4 id='required-tools'>Required Tools</h4>
<ul>
<li><strong>Python 3.12+</strong> - Core runtime</li>
<li><strong>Git + GitHub Desktop (optional)</strong> - Version control</li>
<li><strong>VS Code</strong> - Recommended IDE (with Python, Pylance, and GitLens extensions)</li>
<li><strong>Docker Desktop</strong> - For local container testing (deploy/ directory)</li>
<li><strong>Streamlit</strong> - UI framework (runs locally via <code>streamlit run dashboard.py</code>)</li>
</ul>

<h4 id='environment-variables'>Environment Variables (.env)</h4>
<table><thead><tr><th>Variable</th><th>Required</th><th>Purpose</th></tr></thead><tbody>
<tr><td><code>NVIDIA_API_KEY</code></td><td>For live LLM calls</td><td>NVIDIA NIMs API key (get from build.nvidia.com)</td></tr>
<tr><td><code>SENTRY_DSN</code></td><td>Optional</td><td>Error tracking (set up a free Sentry project)</td></tr>
<tr><td><code>DEMO_MODE</code></td><td>Defaults to <code>true</code></td><td>Set to <code>true</code> to use mock data (no API key needed)</td></tr>
<tr><td><code>LOG_LEVEL</code></td><td>Defaults to <code>INFO</code></td><td>Set to <code>DEBUG</code> for verbose logging</td></tr>
</tbody></table>

<h4 id='useful-commands'>Useful Commands</h4>
<pre class="code-block"><code class="language-bash"># Run the dashboard
streamlit run dashboard.py

# Run the CLI API server
python run.py api

# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_orchestrator.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Check code style (if configured)
ruff check src/
</code></pre>


<hr class="section-divider">

<h2 id='25-roadmap-milestones'>25. Roadmap &amp; Milestones</h2>

<blockquote><strong>Four-phase plan for the CloudOptima team. Each phase has clear deliverables, owners, and success criteria.</strong></blockquote>

<h3 id='25-1-phase-1-stabilize-weeks-1-3'>25.1 Phase 1 - Stabilize (Weeks 1-3)</h3>

<table><thead><tr><th>Task</th><th>Owner</th><th>Effort</th><th>Success Criterion</th></tr></thead><tbody>
<tr><td><strong>Fix LLM JSON Parsing</strong></td><td>Student 1</td><td>~3 days</td><td>JSON decode failures drop from ~20% to &lt;5%. All 5 agent types produce valid output 95%+ of the time</td></tr>
<tr><td><strong>Reduce Session Latency</strong></td><td>Student 1 + MS Eng 1</td><td>~4 days</td><td>Total session time under 60 seconds for typical requests (currently ~98s)</td></tr>
<tr><td><strong>Improve Dashboard UX</strong></td><td>Student 1</td><td>~3 days</td><td>Agent outputs display in human-readable format (not raw JSON). Judge verdict is prominent and clear</td></tr>
<tr><td><strong>Add Database Persistence</strong></td><td>Student 2</td><td>~5 days</td><td>Sessions survive server restarts. Use SQLite first, then migrate to Cosmos DB (Phase 2)</td></tr>
<tr><td><strong>Expand Test Coverage</strong></td><td>Student 2</td><td>~3 days</td><td>Test count grows from 205+ to 350+. Coverage exceeds 80% on core modules</td></tr>
<tr><td><strong>Input Validation Edge Cases</strong></td><td>Student 1</td><td>~2 days</td><td>Boundary testing: empty inputs, malicious payloads, Unicode, extremely long text - all handled gracefully</td></tr>
</tbody></table>

<p><strong>Phase 1 Milestone:</strong> CloudOptima runs reliably under 60 seconds with &lt;5% error rate. Demo-ready for Microsoft stakeholders.</p>

<h3 id='25-2-phase-2-microsoft-integration-weeks-4-6'>25.2 Phase 2 - Microsoft Integration (Weeks 4-6)</h3>

<table><thead><tr><th>Task</th><th>Owner</th><th>Effort</th><th>Success Criterion</th></tr></thead><tbody>
<tr><td><strong>Switch to Azure OpenAI Service</strong></td><td>MS Eng 1</td><td>~5 days</td><td>GPT-4o replaces NVIDIA NIMs as default provider. Config-switchable via env var</td></tr>
<tr><td><strong>Set up Azure DevOps CI/CD</strong></td><td>MS Eng 1</td><td>~3 days</td><td>Every push triggers automated build + test + deploy to Azure Container Apps</td></tr>
<tr><td><strong>Add Azure AD / Entra ID Auth</strong></td><td>MS Eng 2</td><td>~4 days</td><td>Users sign in with Microsoft accounts. Role-based access (admin, viewer, editor)</td></tr>
<tr><td><strong>Azure Monitor + App Insights</strong></td><td>MS Eng 1</td><td>~3 days</td><td>Real-time dashboards for latency, error rates, session volume. Alert thresholds configured</td></tr>
<tr><td><strong>Microsoft Defender for Cloud Scan</strong></td><td>MS Eng 2</td><td>~2 days</td><td>Generated architectures are automatically scanned for security misconfigurations</td></tr>
<tr><td><strong>Live Cost Management API</strong></td><td>MS Eng 2</td><td>~3 days</td><td>Replace static pricing with live Azure Retail Rates API. Updates cached daily</td></tr>
</tbody></table>

<p><strong>Phase 2 Milestone:</strong> CloudOptima runs entirely on Azure infrastructure with real Microsoft services. Demo shows Azure-native integration.</p>

<h3 id='25-3-phase-3-production-ready-weeks-7-9'>25.3 Phase 3 - Production-Ready (Weeks 7-9)</h3>

<table><thead><tr><th>Task</th><th>Owner</th><th>Effort</th><th>Success Criterion</th></tr></thead><tbody>
<tr><td><strong>Cosmos DB Migration</strong></td><td>Student 2 + MS Eng 2</td><td>~5 days</td><td>Session data persists in Cosmos DB. Global replication enabled for multi-region demos</td></tr>
<tr><td><strong>Azure API Management</strong></td><td>MS Eng 2</td><td>~4 days</td><td>API Gateway with rate limiting, RBAC, usage plans, and developer portal</td></tr>
<tr><td><strong>Parallel Agent Execution</strong></td><td>Student 1 + MS Eng 1</td><td>~4 days</td><td>Agents run in parallel (asyncio) instead of sequentially. Cut session time by ~60%</td></tr>
<tr><td><strong>RAG Compliance Engine</strong></td><td>Student 2</td><td>~5 days</td><td>Vector DB (Azure AI Search) with 10+ regulatory documents. Agent queries RAG for less common frameworks</td></tr>
<tr><td><strong>Multi-Tenancy Support</strong></td><td>All</td><td>~5 days</td><td>Multiple teams can use CloudOptima simultaneously with isolated sessions</td></tr>
</tbody></table>

<p><strong>Phase 3 Milestone:</strong> CloudOptima is production-grade: scalable, secure, multi-tenant, with real Azure services end-to-end.</p>

<h3 id='25-4-phase-4-advanced-weeks-10-12'>25.4 Phase 4 - Advanced (Weeks 10-12)</h3>

<table><thead><tr><th>Task</th><th>Owner</th><th>Effort</th><th>Success Criterion</th></tr></thead><tbody>
<tr><td><strong>Real-Time Streaming</strong></td><td>Student 1</td><td>~5 days</td><td>SSE or WebSocket-based real-time agent output streaming to dashboard</td></tr>
<tr><td><strong>Working Terraform Output</strong></td><td>MS Eng 1</td><td>~4 days</td><td>Generated Terraform configs are syntactically valid and deployable</td></tr>
<tr><td><strong>Cost Optimization Recommendations</strong></td><td>MS Eng 2</td><td>~3 days</td><td>Reserved Instance / Savings Plan recommendations based on usage patterns</td></tr>
<tr><td><strong>Sustainability Agent (6th Agent)</strong></td><td>Student 2</td><td>~4 days</td><td>Carbon footprint estimation for each architecture. Recommends green SKUs</td></tr>
<tr><td><strong>Export to PowerPoint / PDF</strong></td><td>Student 1</td><td>~3 days</td><td>One-click export of architecture report for stakeholder presentations</td></tr>
</tbody></table>

<p><strong>Phase 4 Milestone:</strong> CloudOptima is a comprehensive, enterprise-grade architecture tool with advanced features.</p>

<h3 id='25-5-risk-mitigation'>25.5 Risk Mitigation</h3>

<table><thead><tr><th>Risk</th><th>Likelihood</th><th>Impact</th><th>Mitigation</th></tr></thead><tbody>
<tr><td>LLM API cost overruns</td><td>Medium</td><td>High</td><td>Use cache aggressively (Section 11). Limit to smaller models for Cost/Security agents. Set daily spend caps</td></tr>
<tr><td>$100 Azure credits insufficient</td><td>Medium</td><td>Medium</td><td>Azure Container Apps consumption plan (~$0/mo for demo). Apply for Azure for Research credits ($5K-$50K)</td></tr>
<tr><td>Streamlit scaling limitations</td><td>Low</td><td>Medium</td><td>Replace with React frontend in Phase 4. For now, Streamlit handles 50+ concurrent users</td></tr>
<tr><td>LLM output quality regression</td><td>Medium</td><td>High</td><td>Maintain golden test set of 20+ prompt/response pairs. Run regression tests before every release</td></tr>
<tr><td>Team member availability gaps</td><td>Medium</td><td>Medium</td><td>Cross-train: each module has at least 2 people familiar with it. Document key decisions</td></tr>
</tbody></table>


<hr class="section-divider">

<h2 id='26-microsoft-integration-points'>26. Microsoft Integration Points</h2>

<blockquote><strong>Specific Azure services and Microsoft tools that the MS engineers on the team can leverage. Each integration has a clear owner, effort estimate, and impact.</strong></blockquote>

<h3 id='26-1-azure-openai-service'>26.1 Azure OpenAI Service</h3>

<p><strong>Owner:</strong> Microsoft Engineer 1 | <strong>Effort:</strong> ~5 days | <strong>Impact:</strong> High</p>

<p><strong>Current:</strong> CloudOptima uses NVIDIA NIMs (OpenAI-compatible API) as the default LLM provider.</p>

<p><strong>Target:</strong> Switch to <strong>Azure OpenAI Service</strong> (GPT-4o, GPT-4-turbo, o1-mini) deployed within the student Azure subscription.</p>

<table><thead><tr><th>Capability</th><th>Current (NVIDIA NIMs)</th><th>Target (Azure OpenAI)</th></tr></thead><tbody>
<tr><td><strong>Model</strong></td><td>Mistral Small, LLaMA 3</td><td>GPT-4o, GPT-4-turbo, o1-mini</td></tr>
<tr><td><strong>Latency</strong></td><td>~3-5s per call</td><td>~2-4s per call (Azure regions)</td></tr>
<tr><td><strong>SLA</strong></td><td>None (free tier)</td><td>99.9% (paid tier)</td></tr>
<tr><td><strong>Data Residency</strong></td><td>US-based</td><td>UAE North (same as target region)</td></tr>
<tr><td><strong>Cost</strong></td><td>Free credits</td><td>Pay-as-you-go (~$0.01-0.03 per session)</td></tr>
<tr><td><strong>Integration</strong></td><td>External API key</td><td>Azure AD auth, no exposed keys</td></tr>
</tbody></table>

<h3 id='26-2-azure-devops-github-actions'>26.2 Azure DevOps / GitHub Actions</h3>

<p><strong>Owner:</strong> Microsoft Engineer 1 | <strong>Effort:</strong> ~3 days | <strong>Impact:</strong> High</p>

<p><strong>Current:</strong> Manual deployment via shell scripts in <code>deploy/</code>. No automated CI/CD pipeline.</p>

<p><strong>Target:</strong> GitHub Actions workflow that:</p>
<ol>
<li>Runs <code>pytest tests/ -v</code> on every push</li>
<li>Runs Ruff linter + type checker</li>
<li>Builds Docker image with <code>--platform linux/amd64</code></li>
<li>Pushes to Azure Container Registry (ACR)</li>
<li>Deploys to Azure Container Apps with zero-downtime</li>
</ol>

<h3 id='26-3-azure-ad-entra-id-authentication'>26.3 Azure AD / Entra ID Authentication</h3>

<p><strong>Owner:</strong> Microsoft Engineer 2 | <strong>Effort:</strong> ~4 days | <strong>Impact:</strong> Medium</p>

<p><strong>Current:</strong> No authentication. Anyone with the URL can run sessions.</p>

<p><strong>Target:</strong> Microsoft Entra ID (formerly Azure AD) authentication so only authorized team members can access CloudOptima.</p>

<h3 id='26-4-azure-monitor-application-insights'>26.4 Azure Monitor + Application Insights</h3>

<p><strong>Owner:</strong> Microsoft Engineer 1 | <strong>Effort:</strong> ~3 days | <strong>Impact:</strong> Medium</p>

<p><strong>Current:</strong> Basic observability via <code>observability.py</code> - traces, audit logs, and metrics are written to local files.</p>

<p><strong>Target:</strong> Replace local logging with Azure Monitor + Application Insights for live metrics, distributed traces, and alerts.</p>

<h3 id='26-5-microsoft-defender-for-cloud'>26.5 Microsoft Defender for Cloud</h3>

<p><strong>Owner:</strong> Microsoft Engineer 2 | <strong>Effort:</strong> ~2 days | <strong>Impact:</strong> High</p>

<p><strong>Current:</strong> Security recommendations are LLM-generated and not validated against real Azure security benchmarks.</p>

<p><strong>Target:</strong> After CloudOptima generates an architecture, automatically scan it using Microsoft Defender for Cloud's API to verify security compliance.</p>

<h3 id='26-6-azure-api-management'>26.6 Azure API Management</h3>

<p><strong>Owner:</strong> Microsoft Engineer 2 | <strong>Effort:</strong> ~4 days | <strong>Impact:</strong> Medium</p>

<p><strong>Current:</strong> No API gateway. The Streamlit dashboard communicates directly with the orchestrator.</p>

<p><strong>Target:</strong> Expose CloudOptima as a REST API through Azure API Management with rate limiting, RBAC, and developer portal.</p>

<h3 id='26-7-integration-dependency-graph'>26.7 Integration Dependency Graph</h3>

<pre class="code-block"><code class="language-text">Phase 2
Azure OpenAI        Replaces NVIDIA NIMs (Day 1)
Azure DevOps        CI/CD pipeline (Day 2-3)
  +-- Azure Container Registry     Store Docker images
  +-- Azure Container Apps         Deployment target
Entra ID Auth       Auth layer (Day 4-7)
  +-- Affects dashboard.py + run.py (session.user_id)

Phase 3
Cosmos DB           Replaces in-memory sessions
  +-- Depends on Entra ID (user context)
Azure Monitor       Replaces local observability
  +-- Instrument orchestrator.py + agent_base.py
Defender for Cloud  Validates generated IaC
  +-- New agent output type

Phase 4
API Management      Exposes REST API
  +-- Depends on Entra ID + Cosmos DB
Terraform Output    Requires Bicep - Terraform converter
Real-Time Streaming Requires SSE/WebSocket support
</code></pre>


<hr class="section-divider">

<h2 id='27-known-limitations-technical-debt'>27. Known Limitations &amp; Technical Debt</h2>

<blockquote><strong>Transparency about what doesn't work well yet. Each item has a severity, workaround, and planned fix.</strong></blockquote>

<h3 id='27-1-llm-output-quality'>27.1 LLM Output Quality</h3>

<table><thead><tr><th>Issue</th><th>Severity</th><th>Frequency</th><th>Workaround</th><th>Planned Fix</th></tr></thead><tbody>
<tr><td><strong>Malformed JSON from LLM</strong></td><td>HIGH</td><td>~15-20%</td><td>Pydantic defaults fill missing fields</td><td>Switch to Azure OpenAI response_format param</td></tr>
<tr><td><strong>Agent hallucinates pricing</strong></td><td>MEDIUM</td><td>~10%</td><td>Manual price verification recommended</td><td>Live Azure Retail Prices API integration</td></tr>
<tr><td><strong>Compliance citations are generic</strong></td><td>MEDIUM</td><td>~30%</td><td>Human review of regulation sections required</td><td>RAG engine with regulatory documents (Phase 2)</td></tr>
<tr><td><strong>Judge averages instead of picking</strong></td><td>MEDIUM</td><td>~15%</td><td>Prompt includes explicit "do not average" instruction</td><td>Improve prompt with negative examples</td></tr>
</tbody></table>

<h3 id='27-2-performance'>27.2 Performance</h3>

<table><thead><tr><th>Issue</th><th>Severity</th><th>Impact</th><th>Root Cause</th><th>Planned Fix</th></tr></thead><tbody>
<tr><td><strong>Total session time &gt;90s</strong></td><td>HIGH</td><td>Poor UX</td><td>Sequential agent execution (5 LLM calls)</td><td>Parallel execution via asyncio (Phase 3)</td></tr>
<tr><td><strong>No streaming output</strong></td><td>MEDIUM</td><td>Blank screen during processing</td><td>Streamlit sync limitation</td><td>SSE via st.write streaming (Phase 4)</td></tr>
<tr><td><strong>Dashboard re-render overhead</strong></td><td>MEDIUM</td><td>~2-3s delay</td><td>Streamlit re-runs entire script</td><td>Use st.fragment for targeted re-renders</td></tr>
<tr><td><strong>Cache not shared across instances</strong></td><td>LOW</td><td>Cache miss on new server</td><td>Disk-persisted cache</td><td>Migrate to Azure Cache for Redis</td></tr>
</tbody></table>

<h3 id='27-3-architecture-design'>27.3 Architecture &amp; Design</h3>

<table><thead><tr><th>Issue</th><th>Severity</th><th>Impact</th><th>Planned Fix</th></tr></thead><tbody>
<tr><td><strong>In-memory session storage</strong></td><td>MEDIUM</td><td>Sessions lost on restart</td><td>Cosmos DB migration (Phase 3)</td></tr>
<tr><td><strong>No authentication</strong></td><td>MEDIUM</td><td>No audit trail per user</td><td>Entra ID auth (Phase 2)</td></tr>
<tr><td><strong>No rate limiting</strong></td><td>LOW</td><td>Unlimited concurrent sessions</td><td>Azure API Management (Phase 2)</td></tr>
<tr><td><strong>Mock vs Live mode confusing</strong></td><td>LOW</td><td>Wrong mode used accidentally</td><td>Clear visual indicator in dashboard header</td></tr>
</tbody></table>

<h3 id='27-4-testing-gaps'>27.4 Testing Gaps</h3>

<table><thead><tr><th>Gap</th><th>Severity</th><th>Impact</th><th>Planned Fix</th></tr></thead><tbody>
<tr><td><strong>No LLM integration tests</strong></td><td>MEDIUM</td><td>Prompt changes may break output</td><td>Recorded LLM responses (VCR.py pattern)</td></tr>
<tr><td><strong>No end-to-end browser tests</strong></td><td>MEDIUM</td><td>Dashboard changes break silently</td><td>Playwright tests for critical paths</td></tr>
<tr><td><strong>No performance benchmarks in CI</strong></td><td>LOW</td><td>Latency regressions</td><td>Add locust/vegeta benchmarks</td></tr>
<tr><td><strong>Limited negative test coverage</strong></td><td>LOW</td><td>Error paths not tested</td><td>Tests for empty responses, timeouts, invalid input</td></tr>
</tbody></table>

<h3 id='27-5-ux-shortcomings'>27.5 UX Shortcomings</h3>

<table><thead><tr><th>Issue</th><th>Severity</th><th>Impact</th><th>Planned Fix</th></tr></thead><tbody>
<tr><td><strong>Agent results as raw JSON</strong></td><td>HIGH</td><td>Users cannot understand outputs</td><td>Human-readable cards (Student 1, Phase 1)</td></tr>
<tr><td><strong>No progress estimation</strong></td><td>MEDIUM</td><td>Unknown wait time</td><td>Show estimated time per agent</td></tr>
<tr><td><strong>No session history browser</strong></td><td>MEDIUM</td><td>Results lost on refresh</td><td>Session list sidebar</td></tr>
<tr><td><strong>Mobile layout broken</strong></td><td>LOW</td><td>Unusable on phones</td><td>Responsive CSS breakpoints</td></tr>
</tbody></table>


<hr class="section-divider">

<h2 id='28-team-workflow-git-strategy'>28. Team Workflow &amp; Git Strategy</h2>

<blockquote><strong>How the 5-person team collaborates on code. Branching strategy, PR workflow, code review standards, and sprint cadence.</strong></blockquote>

<h3 id='28-1-branching-strategy'>28.1 Branching Strategy</h3>

<p>We use a simplified <strong>GitHub Flow</strong> (not Git Flow) because:</p>
<ul>
<li>5 people is small enough for trunk-based development</li>
<li>No need for long-running release branches</li>
<li>Simplifies CI/CD (every branch gets tested)</li>
<li>Less merge overhead</li>
</ul>

<table><thead><tr><th>Branch</th><th>Purpose</th><th>Protection</th></tr></thead><tbody>
<tr><td><code>main</code></td><td>Production-ready code. Deployed to Azure</td><td>Requires PR review + passing CI</td></tr>
<tr><td><code>feature/&lt;name&gt;</code></td><td>New feature or bug fix</td><td>None - created from main, merged via PR</td></tr>
<tr><td><code>docs/&lt;name&gt;</code></td><td>Documentation-only changes</td><td>Same as feature branches</td></tr>
</tbody></table>

<h3 id='28-2-pull-request-workflow'>28.2 Pull Request Workflow</h3>

<pre class="code-block"><code class="language-text">1. Create a feature branch from main
   git checkout main && git pull
   git checkout -b feature/my-task

2. Make changes, commit frequently
   git add -A && git commit -m "[Area] Description"
   git push -u origin feature/my-task

3. Open a Pull Request against main
   - Title: [Area] Brief description
   - Description: What changed, why, how to test
   - Reviewers: At least 1 other team member

4. CI runs automatically (pytest + lint)
5. Code review: At least 1 approval required
6. Merge: Use "Squash and merge" (clean history)
7. Delete feature branch after merge
</code></pre>

<h3 id='28-3-code-review-standards'>28.3 Code Review Standards</h3>

<table><thead><tr><th>Category</th><th>Must Check</th><th>Must NOT Block On</th></tr></thead><tbody>
<tr><td><strong>Correctness</strong></td><td>Does the code do what it claims? Are edge cases handled?</td><td>-</td></tr>
<tr><td><strong>Tests</strong></td><td>Are new features tested? Do existing tests pass?</td><td>Line-by-line coverage requirements</td></tr>
<tr><td><strong>Style</strong></td><td>Does it follow existing conventions? No dead code</td><td>Personal preferences (tabs vs spaces)</td></tr>
<tr><td><strong>Design</strong></td><td>Is the change consistent with the architecture?</td><td>Perfect abstraction. Good enough is fine</td></tr>
<tr><td><strong>Security</strong></td><td>Are user inputs sanitized? No hardcoded secrets?</td><td>-</td></tr>
</tbody></table>

<h3 id='28-4-commit-message-conventions'>28.4 Commit Message Conventions</h3>

<pre class="code-block"><code class="language-text">[Area] Short description under 50 chars

Longer explanation if needed. Wrap at 72 characters.
Explain WHY, not what (the code shows what).

Areas: [Core], [Agent], [UI], [Docs], [Tests], [Deploy], [Config]

Example:
[Core] Fix JSON extraction regex for nested objects
The previous regex stopped at the first closing brace,
missing nested objects. Used re.DOTALL flag to match
across newlines.
</code></pre>

<h3 id='28-5-sprint-cadence'>28.5 Sprint Cadence</h3>

<table><thead><tr><th>Frequency</th><th>Meeting</th><th>Duration</th><th>Agenda</th></tr></thead><tbody>
<tr><td><strong>Weekly</strong></td><td>Sprint Planning</td><td>30 min</td><td>Pick tasks from Roadmap (Section 25). Assign owners. Set weekly goals</td></tr>
<tr><td><strong>Weekly</strong></td><td>Standup (async)</td><td>5 min each</td><td>What I did yesterday, what I'll do today, blockers</td></tr>
<tr><td><strong>Bi-weekly</strong></td><td>Demo &amp; Review</td><td>45 min</td><td>Show working progress. Stakeholder feedback. Adjust roadmap</td></tr>
<tr><td><strong>Monthly</strong></td><td>Retrospective</td><td>30 min</td><td>What went well, what could improve, action items</td></tr>
</tbody></table>

<h3 id='28-6-responsibility-matrix'>28.6 Responsibility Matrix</h3>

<table><thead><tr><th>Module</th><th>Primary</th><th>Secondary (Backup)</th></tr></thead><tbody>
<tr><td><code>orchestrator.py</code> / <code>models.py</code></td><td>You (Lead)</td><td>Student 1</td></tr>
<tr><td><code>agent_base.py</code> / <code>agent_schemas.py</code></td><td>Student 1</td><td>You (Lead)</td></tr>
<tr><td><code>llm_client.py</code></td><td>MS Eng 1</td><td>Student 1</td></tr>
<tr><td><code>compliance_rules.py</code> / RAG</td><td>Student 2</td><td>MS Eng 2</td></tr>
<tr><td><code>azure_prices_api.py</code> / pricing</td><td>MS Eng 2</td><td>Student 2</td></tr>
<tr><td><code>dashboard.py</code> (UI)</td><td>Student 1</td><td>You (Lead)</td></tr>
<tr><td><code>observability.py</code> / monitoring</td><td>MS Eng 1</td><td>Student 2</td></tr>
<tr><td><code>health.py</code> / deployment</td><td>MS Eng 1</td><td>MS Eng 2</td></tr>
<tr><td>Tests</td><td>Whoever writes the code</td><td>Student 2 (coverage guardian)</td></tr>
<tr><td>Documentation</td><td>Student 2</td><td>Everyone (for their modules)</td></tr>
</tbody></table>

<h3 id='28-7-communication-channels'>28.7 Communication Channels</h3>

<table><thead><tr><th>Channel</th><th>Purpose</th></tr></thead><tbody>
<tr><td><strong>GitHub Issues</strong></td><td>Bug reports, feature requests, technical discussions (public record)</td></tr>
<tr><td><strong>GitHub Discussions</strong></td><td>Architecture decisions, RFCs, longer-form technical conversations</td></tr>
<tr><td><strong>Pull Request Reviews</strong></td><td>Code-specific feedback, inline suggestions</td></tr>
<tr><td><strong>Teams / Slack</strong></td><td>Quick questions, daily standups, meeting coordination</td></tr>
<tr><td><strong>Shared Notebook (OneNote/Notion)</strong></td><td>Meeting notes, design docs, decision logs</td></tr>
</tbody></table>
"""

# ─── 3. INSERT BEFORE CONCLUSION (preserving all existing content) ─

find_conc = "<h2 id='conclusion'>Conclusion</h2>"
if find_conc not in html:
    print(f"{ERR} Could not find Conclusion heading")
    exit(1)

insert_pos = html.index(find_conc)
html = html[:insert_pos] + new_sections + "\n\n" + html[insert_pos:]

# ─── 4. UPDATE VERSION & METADATA ───────────────────────────

html = html.replace(
    '<p><strong>Version:</strong> 1.0.0</p>',
    '<p><strong>Version:</strong> 1.1.0</p>'
)
html = html.replace(
    'CloudOptima Engineering Team</p>',
    'CloudOptima Collaboration Team (5 members)</p>'
)

# ─── 5. VERIFY & WRITE ───────────────────────────────────────

# Quick sanity checks
for tag in ["id='24-", "id='25-", "id='26-", "id='27-", "id='28-"]:
    if tag not in html:
        print(f"WARNING: Section anchor '{tag}' not found!")

for section_id in ["24-team-onboarding-guide", "25-roadmap-milestones",
                   "26-microsoft-integration-points", "27-known-limitations-technical-debt",
                   "28-team-workflow-git-strategy"]:
    if section_id not in html:
        print(f"WARNING: Section ID '{section_id}' not found in anchors!")

if find_conc not in html:
    print(f"{ERR} Conclusion section was lost!")
    exit(1)

if "Page number script" not in html:
    print(f"{ERR} Script tag was lost!")
    exit(1)

changed = len(html) - orig_len
GUIDE.write_text(html, "utf-8")
print(f"{OK} Written {len(html):,} bytes to {GUIDE}  (changed: {changed:+,} bytes)")
print(f"{OK} Added sections 24-28 (Team Onboarding, Roadmap, MS Integration, Limitations, Git Workflow)")
print(f"{OK} Preserved all original content including Conclusion body text")
print(f"{OK} Updated version to 1.1.0 and author line")
