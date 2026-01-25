# Configuration Setup

This project supports multiple ways to configure API keys and settings.

## Option 1: config.json (Recommended for local development)

1. Copy the example config file:
   ```bash
   cp config.example.json config.json
   ```

2. Edit `config.json` with your actual API keys:
   ```json
   {
     "anthropic_api_key": "sk-ant-your-actual-key-here",
     "openai_api_key": "sk-your-actual-key-here",
     "fhir_server_url": "http://localhost:5826",
     "mcp_server_url": ""
   }
   ```

3. The `config.json` file is **automatically ignored by git** (.gitignore), so your keys are safe.

## Option 2: .env file (Also good)

1. Copy the example env file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your keys:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
   OPENAI_API_KEY=sk-your-actual-key-here
   ```

3. The `.env` file is also gitignored.

## Option 3: Environment Variables (Best for production)

Set environment variables directly:

```bash
# Linux/Mac
export ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
export OPENAI_API_KEY=sk-your-actual-key-here

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="sk-ant-your-actual-key-here"
$env:OPENAI_API_KEY="sk-your-actual-key-here"

# Windows (CMD)
set ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
set OPENAI_API_KEY=sk-your-actual-key-here
```

## Configuration Priority

Settings are loaded in this order (higher priority first):

1. **Environment variables** (highest priority)
2. **.env file**
3. **config.json file** (lowest priority)

This means environment variables will override values in config.json.

## Security Notes

- ✅ **DO**: Use `config.json` or `.env` for local development
- ✅ **DO**: Use environment variables for production/CI/CD
- ✅ **DO**: Keep `config.example.json` updated as a template
- ❌ **DON'T**: Commit `config.json` or `.env` to git (they're gitignored)
- ❌ **DON'T**: Share your API keys in screenshots or documentation
- ❌ **DON'T**: Put API keys in code comments or hardcoded strings

## Available Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `anthropic_api_key` | Anthropic API key for Claude | None (required for scraping) |
| `openai_api_key` | OpenAI API key | None (optional) |
| `fhir_server_url` | FHIR server endpoint | `http://localhost:5826` |
| `fhir_version` | FHIR version (r4, r4b, r5) | `r4` |
| `mcp_server_url` | MCP server endpoint | None (optional) |
| `test_cases_dir` | Test cases directory | `test-cases` |
| `data_dir` | Data directory | `data` |

## Example: Complete Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd llm-fhir-query-eval

# 2. Set up config file
cp config.example.json config.json
# Edit config.json with your API keys

# 3. Install backend
cd backend
poetry install

# 4. Install CLI
cd ../cli
pip install -e .

# 5. Test configuration
fhir-eval scrape --list
```

Your `config.json` is safe and won't be committed to git!
