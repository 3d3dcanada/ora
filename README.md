# ORA - Operational Reasoning Architecture

<p align="center">
  <strong>Enterprise-Grade Multi-Agent AI Operating System</strong>
</p>

<p align="center">
  <a href="https://github.com/3d3dcanada/ora">
    <img src="https://img.shields.io/badge/GitHub-3d3dcanada-blue.svg" alt="GitHub">
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT">
  </a>
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/TypeScript-5.0+-blue.svg" alt="TypeScript">
</p>

---

## What is ORA?

**ORA (Operational Reasoning Architecture)** is a comprehensive multi-agent AI operating system designed for enterprise deployments. It combines advanced agent orchestration with graph-based routing, robust security mechanisms, and constitutional governance to enable safe, auditable, and scalable AI operations.

### Key Features

- 🧠 **7 Specialized AI Agents** - Planner, Researcher, Builder, Tester, Integrator, Security, and Self-Dev
- 🔒 **6 Authority Levels (A0-A5)** - Hierarchical permission system from read-only to system execution
- 🌐 **Provider Agnostic** - Works with ANY LLM (DeepSeek, Kimi, GLM, Nemotron, Mistral, OpenAI, Anthropic +100 more)
- 💾 **Vector Memory** - Pulz Memory with Qdrant for semantic context retention
- 🛡️ **Enterprise Security** - Prompt injection scanning, sandbox enforcement, immutable audit logs
- ⚖️ **Constitutional Governance** - Rules-based AI operation with separation of powers

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/3d3dcanada/ora.git
cd ora

# Install Python dependencies
pip install -e .

# Set up environment
cp config/.env.example config/.env
# Edit config/.env with your API keys

# Run the TUI
python -m ora.tui
```

### Running the Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Documentation

### 📺 Presentation

For a comprehensive visual overview of ORA's architecture, features, and capabilities, see our interactive presentation:

**[View Presentation](./ora/docs/detailed_presentation.html)**

The presentation covers:
- System architecture diagrams
- Authority levels (A0-A5)
- Security layers
- Performance benchmarks
- Provider comparisons
- Agent fleet details

### Architecture Overview

```
┌─────────────────────────────────────────┐
│              CORE LAYER                 │
│  OraKernel │ Constitution │ Authority   │
├─────────────────────────────────────────┤
│           ORCHESTRATOR                  │
│  Graph-Based Routing │ Task Pipeline    │
├─────────────────────────────────────────┤
│            AGENT FLEET                  │
│  Planner │ Researcher │ Builder │ ...   │
├─────────────────────────────────────────┤
│            SECURITY LAYER                │
│  Vault │ Gates │ Scanner │ Audit Log    │
├─────────────────────────────────────────┤
│             GATEWAY                     │
│  MoneyModZ │ Smart Router │ Rate Limit │
├─────────────────────────────────────────┤
│              MEMORY                     │
│  Pulz Memory │ Qdrant Vector Store      │
└─────────────────────────────────────────┘
```

---

## Supported LLM Providers

ORA is provider-agnostic through LiteLLM abstraction:

| Provider | Best For | Context |
|----------|----------|---------|
| DeepSeek | Value | 64K |
| Kimi | Long Context | 128K |
| GLM | Reasoning | 128K |
| Nemotron | Speed | 32K |
| Mistral | Code | 128K |
| OpenAI | Quality | 128K |
| Anthropic | Reasoning | 200K |

---

## Configuration

Key configuration files:

- `config/litellm.yaml` - LLM provider settings
- `config/.env` - API keys and secrets

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Contact

- GitHub: [https://github.com/3d3dcanada](https://github.com/3d3dcanada)
- Email: info@3d3d.ca

---

<p align="center">
  Built with enterprise-grade security and constitutional governance.
</p>
