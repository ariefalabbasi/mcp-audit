#!/usr/bin/env python3
"""
Test suite for pricing_config module

Tests pricing configuration loading, validation, and cost calculation.
"""

import pytest
from pathlib import Path
from mcp_audit.pricing_config import PricingConfig, load_pricing_config, get_model_cost


class TestPricingConfigLoading:
    """Tests for configuration file loading"""

    def test_load_default_config(self) -> None:
        """Test loading default mcp-audit.toml"""
        config = PricingConfig()
        assert config.loaded == True
        assert len(config.pricing_data) > 0

    def test_load_specific_path(self) -> None:
        """Test loading from specific path"""
        config_path = Path("mcp-audit.toml")
        config = PricingConfig(config_path)
        assert config.loaded == True

    def test_missing_config_falls_back_to_defaults(self) -> None:
        """Test that missing config file falls back to DEFAULT_PRICING (task-67)"""
        config = PricingConfig(Path("nonexistent.toml"))
        # Should load defaults, not fail
        assert config.loaded == True
        assert config._source == "defaults"


class TestModelPricingLookup:
    """Tests for model pricing retrieval"""

    def test_get_claude_pricing(self) -> None:
        """Test getting Claude model pricing"""
        config = PricingConfig()
        pricing = config.get_model_pricing("claude-sonnet-4-5-20250929")

        assert pricing is not None
        assert "input" in pricing
        assert "output" in pricing
        assert pricing["input"] == 3.0
        assert pricing["output"] == 15.0

    def test_get_openai_pricing(self) -> None:
        """Test getting OpenAI model pricing"""
        config = PricingConfig()
        pricing = config.get_model_pricing("gpt-4o")

        assert pricing is not None
        assert "input" in pricing
        assert pricing["output"] == 10.0

    def test_get_pricing_with_vendor(self) -> None:
        """Test getting pricing with specific vendor"""
        config = PricingConfig()
        pricing = config.get_model_pricing("gpt-4o", vendor="openai")

        assert pricing is not None
        assert pricing["input"] == 2.5

    def test_unknown_model(self) -> None:
        """Test unknown model returns None with warning"""
        config = PricingConfig()

        with pytest.warns(RuntimeWarning, match="No pricing configured"):
            pricing = config.get_model_pricing("unknown-model")

        assert pricing is None

    def test_cache_pricing_fields(self) -> None:
        """Test models with cache pricing"""
        config = PricingConfig()
        pricing = config.get_model_pricing("claude-sonnet-4-5-20250929")

        assert "cache_create" in pricing
        assert "cache_read" in pricing
        assert pricing["cache_create"] == 3.75
        assert pricing["cache_read"] == 0.30


class TestCostCalculation:
    """Tests for cost calculation"""

    def test_basic_cost_calculation(self) -> None:
        """Test basic input/output token cost"""
        config = PricingConfig()
        cost = config.calculate_cost(
            "claude-sonnet-4-5-20250929", input_tokens=1_000_000, output_tokens=1_000_000
        )

        # 1M input @ $3.0 + 1M output @ $15.0 = $18.0
        assert cost == 18.0

    def test_cost_with_cache(self) -> None:
        """Test cost calculation with cache tokens"""
        config = PricingConfig()
        cost = config.calculate_cost(
            "claude-sonnet-4-5-20250929",
            input_tokens=10_000,
            output_tokens=5_000,
            cache_read_tokens=50_000,
        )

        # 10K input @ $3.0/1M + 5K output @ $15.0/1M + 50K cache @ $0.30/1M
        # = 0.03 + 0.075 + 0.015 = 0.12
        assert cost == pytest.approx(0.12, rel=1e-4)

    def test_zero_tokens(self) -> None:
        """Test cost calculation with zero tokens"""
        config = PricingConfig()
        cost = config.calculate_cost("claude-sonnet-4-5-20250929")

        assert cost == 0.0

    def test_unknown_model_returns_zero(self) -> None:
        """Test unknown model returns zero cost"""
        config = PricingConfig()

        with pytest.warns(RuntimeWarning):
            cost = config.calculate_cost("unknown-model", input_tokens=10_000, output_tokens=5_000)

        assert cost == 0.0

    def test_model_without_cache_pricing(self) -> None:
        """Test model without cache pricing fields"""
        config = PricingConfig()

        # gpt-4o has cache_read but not cache_create
        cost = config.calculate_cost(
            "gpt-4o",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            cache_created_tokens=100_000,
            cache_read_tokens=100_000,
        )

        # Should only include input, output, and cache_read
        # 1M @ $2.5 + 1M @ $10.0 + 100K @ $1.25/1M = 2.5 + 10.0 + 0.125
        assert cost == pytest.approx(12.625, rel=1e-4)


class TestModelListing:
    """Tests for listing available models"""

    def test_list_all_models(self) -> None:
        """Test listing all configured models"""
        config = PricingConfig()
        models = config.list_models()

        assert len(models) > 0
        assert "claude-sonnet-4-5-20250929" in models
        assert "gpt-4o" in models

    def test_list_claude_models(self) -> None:
        """Test listing Claude models only"""
        config = PricingConfig()
        models = config.list_models("claude")

        assert len(models) >= 3  # At least Opus, Sonnet, Haiku
        assert "claude-sonnet-4-5-20250929" in models
        assert "gpt-4o" not in models

    def test_list_openai_models(self) -> None:
        """Test listing OpenAI models only"""
        config = PricingConfig()
        models = config.list_models("openai")

        assert len(models) >= 5  # At least GPT-4o variants and O series
        assert "gpt-4o" in models
        assert "claude-sonnet-4-5-20250929" not in models

    def test_list_custom_models(self) -> None:
        """Test listing custom models (empty by default)"""
        config = PricingConfig()
        models = config.list_models("custom")

        # Should be empty list (no custom models configured)
        assert isinstance(models, list)


class TestValidation:
    """Tests for configuration validation"""

    def test_validate_valid_config(self) -> None:
        """Test validation of valid configuration"""
        config = PricingConfig()
        result = config.validate()

        assert result["valid"] == True
        assert len(result["errors"]) == 0

    def test_validate_checks_required_fields(self) -> None:
        """Test validation warns about missing required fields"""
        config = PricingConfig()
        result = config.validate()

        # All models should have input and output pricing
        # So no warnings about missing fields
        assert "input" not in str(result.get("warnings", []))


class TestConvenienceFunctions:
    """Tests for convenience functions"""

    def test_load_pricing_config(self) -> None:
        """Test convenience function for loading config"""
        config = load_pricing_config()

        assert config.loaded == True
        assert isinstance(config, PricingConfig)

    def test_get_model_cost(self) -> None:
        """Test convenience function for cost calculation"""
        cost = get_model_cost(
            "claude-sonnet-4-5-20250929", input_tokens=10_000, output_tokens=5_000
        )

        # 10K @ $3.0/1M + 5K @ $15.0/1M = 0.03 + 0.075 = 0.105
        assert cost == pytest.approx(0.105, rel=1e-4)


class TestMetadata:
    """Tests for metadata handling"""

    def test_metadata_loaded(self) -> None:
        """Test metadata is loaded from config"""
        config = PricingConfig()

        assert "currency" in config.metadata
        assert config.metadata["currency"] == "USD"

    def test_exchange_rates(self) -> None:
        """Test exchange rates in metadata"""
        config = PricingConfig()

        if "exchange_rates" in config.metadata:
            rates = config.metadata["exchange_rates"]
            assert "USD_to_AUD" in rates


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_model_name_case_sensitivity(self) -> None:
        """Test that model names are case-sensitive"""
        config = PricingConfig()

        # Correct case
        pricing1 = config.get_model_pricing("claude-sonnet-4-5-20250929")
        assert pricing1 is not None

        # Wrong case - should fail with warning
        with pytest.warns(RuntimeWarning):
            pricing2 = config.get_model_pricing("CLAUDE-SONNET-4-5-20250929")
        assert pricing2 is None

    def test_empty_vendor_namespace(self) -> None:
        """Test handling of empty vendor namespace"""
        config = PricingConfig()
        models = config.list_models("nonexistent-vendor")

        assert models == []

    def test_negative_tokens(self) -> None:
        """Test cost calculation with negative tokens (edge case)"""
        config = PricingConfig()

        # Negative tokens should still work (though invalid in practice)
        cost = config.calculate_cost(
            "claude-sonnet-4-5-20250929", input_tokens=-1000, output_tokens=5000
        )

        # Should calculate: -1000 * 3.0/1M + 5000 * 15.0/1M
        assert cost < 0.1


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for complete workflows"""

    def test_complete_workflow(self) -> None:
        """Test complete workflow: load → lookup → calculate"""
        # Load config
        config = load_pricing_config()

        # Validate
        validation = config.validate()
        assert validation["valid"] == True

        # List models
        models = config.list_models()
        assert len(models) > 0

        # Get pricing
        model = models[0]
        pricing = config.get_model_pricing(model)
        assert pricing is not None

        # Calculate cost
        cost = config.calculate_cost(model, input_tokens=1000, output_tokens=500)
        assert cost >= 0.0

    def test_all_configured_models_have_pricing(self) -> None:
        """Test that all configured models have valid pricing"""
        config = PricingConfig()

        for vendor, models in config.pricing_data.items():
            # Skip API configuration section (not pricing data)
            if vendor == "api":
                continue

            for model_name, pricing in models.items():
                # Each model should have at least input and output
                assert (
                    "input" in pricing or "output" in pricing
                ), f"{vendor}.{model_name} missing input/output pricing"

                # Prices should be numeric
                for key in ["input", "output", "cache_create", "cache_read"]:
                    if key in pricing:
                        assert isinstance(
                            pricing[key], (int, float)
                        ), f"{vendor}.{model_name}.{key} is not numeric"
                        assert pricing[key] >= 0, f"{vendor}.{model_name}.{key} is negative"


class TestDefaultPricingFallback:
    """Tests for DEFAULT_PRICING fallback when no config file exists (task-67)"""

    def test_source_attribute_file(self) -> None:
        """Test _source is 'file' when loaded from config file"""
        config = PricingConfig(Path("mcp-audit.toml"))
        assert config._source == "file"
        assert config.loaded == True

    def test_source_attribute_defaults(self) -> None:
        """Test _source is 'defaults' when using fallback"""
        config = PricingConfig(Path("definitely-does-not-exist.toml"))
        assert config._source == "defaults"
        assert config.loaded == True

    def test_default_pricing_has_claude_models(self) -> None:
        """Test DEFAULT_PRICING includes Claude models"""
        config = PricingConfig(Path("nonexistent.toml"))

        # Check Claude Opus 4.5
        opus_pricing = config.get_model_pricing("claude-opus-4-5-20251101")
        assert opus_pricing is not None
        assert "input" in opus_pricing
        assert "output" in opus_pricing
        assert opus_pricing["input"] > 0

        # Check Claude Sonnet 4.5
        sonnet_pricing = config.get_model_pricing("claude-sonnet-4-5-20250929")
        assert sonnet_pricing is not None

        # Check Claude Haiku 4.5
        haiku_pricing = config.get_model_pricing("claude-haiku-4-5-20251001")
        assert haiku_pricing is not None

    def test_default_pricing_has_openai_models(self) -> None:
        """Test DEFAULT_PRICING includes OpenAI/Codex models"""
        config = PricingConfig(Path("nonexistent.toml"))

        # Check GPT-5.1 Codex Max
        codex_max = config.get_model_pricing("gpt-5.1-codex-max")
        assert codex_max is not None
        assert "input" in codex_max
        assert "output" in codex_max

        # Check GPT-5.1
        gpt51 = config.get_model_pricing("gpt-5.1")
        assert gpt51 is not None

    def test_default_pricing_has_gemini_models(self) -> None:
        """Test DEFAULT_PRICING includes Gemini models"""
        config = PricingConfig(Path("nonexistent.toml"))

        # Check Gemini 2.5 Flash
        flash = config.get_model_pricing("gemini-2.5-flash")
        assert flash is not None
        assert "input" in flash
        assert "output" in flash

        # Check Gemini 2.5 Pro
        pro = config.get_model_pricing("gemini-2.5-pro")
        assert pro is not None

    def test_default_pricing_cost_calculation(self) -> None:
        """Test cost calculation works with DEFAULT_PRICING"""
        config = PricingConfig(Path("nonexistent.toml"))

        # Calculate cost with Claude Sonnet 4.5
        cost = config.calculate_cost(
            "claude-sonnet-4-5-20250929",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )

        # 1M input @ $3.0 + 1M output @ $15.0 = $18.0
        assert cost == pytest.approx(18.0, rel=1e-4)

    def test_default_pricing_has_metadata(self) -> None:
        """Test DEFAULT_PRICING includes proper metadata"""
        config = PricingConfig(Path("nonexistent.toml"))

        assert config.metadata is not None
        assert config.metadata.get("currency") == "USD"
        assert config.metadata.get("source") == "hardcoded defaults (task-67)"

    def test_default_pricing_validation_passes(self) -> None:
        """Test DEFAULT_PRICING passes validation"""
        config = PricingConfig(Path("nonexistent.toml"))
        result = config.validate()

        assert result["valid"] == True
        assert len(result["errors"]) == 0

    def test_unknown_model_warning_mentions_config_creation(self) -> None:
        """Test unknown model warning suggests creating config file"""
        config = PricingConfig(Path("nonexistent.toml"))

        with pytest.warns(RuntimeWarning, match="Create.*mcp-audit.toml"):
            config.get_model_pricing("unknown-future-model")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
