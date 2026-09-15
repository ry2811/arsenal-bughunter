# Web3 Bug Hunter (Arsenal Agent)

An AI-powered smart contract security auditor and bug hunter using LangGraph, DeepSeek, and leading static analysis tools.

Landing pages :  https://arsenal-bughunter-landing.vercel.app/

## 🚀 Features

- **Multi-Tool Analysis**: Integrates Slither, Aderyn, Surya, and Mythril.
- **Deep Reasoning**: Uses `deepseek-reasoner` for high-level logic vulnerability analysis.
- **PoC Engineering**: Automatically generates Foundry-based Proof of Concepts (PoC).
- **Automated Verification**: Runs `forge test` to verify discovered vulnerabilities.

## 🛠️ Prerequisites

- **Python**: 3.10+
- **Foundry**: [Install Forge](https://book.getfoundry.sh/getting-started/installation)
- **Node.js**: Required for Aderyn and Surya (`npm install -g @pwned-no/aderyn surya`)
- **Slither**: `pip install slither-analyzer`
- **Mythril**: Recommended to install in a separate venv (`mythril-env`)

## 📦 Setup

1. Clone the repository.
2. Initialize and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your API keys:
   ```env
   DEEPSEEK_API_KEY=your_key_here
   MYTHRIL_PATH=mythril-env/bin/myth
   ```

## 🔍 Usage

Run the auditor on any GitHub repository:
```bash
python audit_agent.py https://github.com/Username/RepoName
```

## 🛡️ License
MIT
# arsenal-bughunter
