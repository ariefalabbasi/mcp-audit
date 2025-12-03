# Pricing Configuration Guide

**Last Updated**: 2025-11-24

This guide explains how to configure model pricing for cost calculation in MCP Audit.

---

## Overview

MCP Audit uses `mcp-audit.toml` to define pricing for AI models. This allows accurate cost estimation for your sessions.

**Key Features**:
- User-configurable pricing for any model
- Support for custom models and local models (zero cost)
- Automatic validation with warnings for missing pricing
- Easy-to-edit TOML format

---

## Configuration File Location

**Default**: `mcp-audit.toml` in project root

The configuration file is automatically loaded when you run MCP Audit tools.

---

## Configuration Format

```toml
[pricing.vendor]
"model-name" = { input = X.X, output = Y.Y, cache_create = Z.Z, cache_read = W.W }
```

**Fields**:
- `input`: Cost per million input tokens (USD)
- `output`: Cost per million output tokens (USD)
- `cache_create`: Cost per million cache creation tokens (USD) - *optional*
- `cache_read`: Cost per million cache read tokens (USD) - *optional*

**Vendors**: Group models by vendor namespace (e.g., `claude`, `openai`, `custom`)

---

## Adding a New Model

### Example 1: OpenAI Model

```toml
[pricing.openai]
"gpt-4-turbo" = { input = 10.0, output = 30.0, cache_read = 5.0 }
```

### Example 2: Local Model (Zero Cost)

```toml
[pricing.custom]
"llama-3-70b" = { input = 0.0, output = 0.0 }
```

### Example 3: Custom Fine-Tuned Model

```toml
[pricing.custom]
"my-fine-tuned-gpt4" = { input = 5.0, output = 20.0, cache_read = 2.5 }
```

---

## Finding Model Pricing

### Anthropic (Claude)
- **Pricing page**: https://www.anthropic.com/pricing
- Models: Claude Opus, Sonnet, Haiku

### OpenAI
- **Pricing page**: https://openai.com/api/pricing/
- Models: GPT-4o, GPT-4o Mini, O1, O3

### Other Providers
- Check provider's pricing documentation
- Convert to USD per million tokens
- Add to `[pricing.custom]` section

---

## Validation

### Automatic Warnings

MCP Audit warns when a model has no pricing configured:

```
⚠️ WARNING: No pricing configured for model: my-new-model
   Add pricing to mcp-audit.toml under [pricing.custom]
```

### Manual Validation

Test your configuration:

```bash
python3 pricing_config.py
```

Expected output:
```
✓ Loaded config from mcp-audit.toml
Validation: ✓ PASS
```

---

## Usage in Code

### Python API

```python
from pricing_config import PricingConfig

# Load configuration
config = PricingConfig()

# Get pricing for a model
pricing = config.get_model_pricing("claude-sonnet-4-5-20250929")
print(pricing)  # {'input': 3.0, 'output': 15.0, ...}

# Calculate cost
cost = config.calculate_cost(
    "claude-sonnet-4-5-20250929",
    input_tokens=10000,
    output_tokens=5000,
    cache_read_tokens=50000
)
print(f"Cost: ${cost:.4f}")  # Cost: $0.1200
```

### List Available Models

```python
# All models
all_models = config.list_models()

# Models by vendor
claude_models = config.list_models('claude')
openai_models = config.list_models('openai')
custom_models = config.list_models('custom')
```

---

## Advanced Configuration

### Exchange Rates

Add exchange rates for display purposes:

```toml
[metadata.exchange_rates]
USD_to_AUD = 1.54
USD_to_EUR = 0.92
USD_to_GBP = 0.79
```

**Note**: Exchange rates are for display only. All costs are calculated in USD.

### Metadata

```toml
[metadata]
currency = "USD"
pricing_unit = "per_million_tokens"
last_updated = "2025-11-24"
```

---

## Common Issues

### Issue 1: "TOML support not available"

**Solution**: Install toml package (Python 3.8-3.10 only):

```bash
pip install toml
```

**Note**: Python 3.11+ has built-in `tomllib` (no installation needed)

### Issue 2: "Config file not found"

**Solution**: Ensure `mcp-audit.toml` exists in project root:

```bash
ls mcp-audit.toml
```

### Issue 3: Invalid TOML syntax

**Solution**: Validate TOML format online:
- https://www.toml-lint.com/

Common mistakes:
- Missing quotes around model names
- Invalid numeric values (use dots: `3.0` not `3,0`)
- Unclosed brackets

---

## Migration from model-pricing.json

If you previously used `model-pricing.json`, the TOML format is equivalent:

**Old (JSON)**:
```json
{
  "models": {
    "claude": {
      "claude-sonnet-4-5-20250929": {
        "input": 3.0,
        "output": 15.0
      }
    }
  }
}
```

**New (TOML)**:
```toml
[pricing.claude]
"claude-sonnet-4-5-20250929" = { input = 3.0, output = 15.0 }
```

**Benefits of TOML**:
- ✅ More human-readable
- ✅ Easier to edit manually
- ✅ Built-in Python 3.11+ support
- ✅ Supports comments (JSON doesn't)

---

## Best Practices

1. **Keep pricing up-to-date**: Check provider pricing pages quarterly
2. **Document custom models**: Add comments explaining your custom model pricing
3. **Use vendor namespaces**: Group models by provider for organization
4. **Validate after editing**: Run `python3 pricing_config.py` to test changes
5. **Version control**: Commit `mcp-audit.toml` to git for team consistency

---

## Example Configuration

See the default `mcp-audit.toml` for a complete example with:
- Claude models (Opus, Sonnet, Haiku)
- OpenAI models (GPT-4o, O1, O3)
- Custom model template
- Exchange rates
- Metadata

---

## API Reference

### PricingConfig Class

**Methods**:
- `load()` - Load configuration from TOML file
- `get_model_pricing(model_name, vendor)` - Get pricing for a model
- `calculate_cost(...)` - Calculate cost for token usage
- `list_models(vendor)` - List all configured models
- `validate()` - Validate configuration structure

**Properties**:
- `pricing_data` - Dictionary of all pricing data
- `metadata` - Configuration metadata
- `loaded` - Boolean indicating if config loaded successfully

---

## Support

**Issues**: Report configuration problems to:
- GitHub: https://github.com/littlebearapps/mcp-audit/issues
- Label: `pricing-config`

**Documentation**: See README.md for general usage
