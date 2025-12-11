"""
Smell Engine - Detects efficiency anti-patterns in MCP usage.

This module identifies common inefficiencies in AI coding assistant sessions
by analyzing tool usage patterns, token distribution, and cache behavior.

Smell Patterns (v1.5.0 - task-103.1):
- HIGH_VARIANCE: Tool with unusually variable token counts across calls
- TOP_CONSUMER: Single tool consuming >50% of session tokens
- HIGH_MCP_SHARE: MCP tools consuming >80% of total tokens
- CHATTY: Tool called >20 times in a session
- LOW_CACHE_HIT: Cache hit rate <30% for cacheable operations
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .base_tracker import Session, Smell


@dataclass
class SmellThresholds:
    """Configurable thresholds for smell detection."""

    # HIGH_VARIANCE: coefficient of variation threshold (std_dev / mean)
    high_variance_cv: float = 0.5  # 50% coefficient of variation

    # TOP_CONSUMER: percentage of session tokens for single tool
    top_consumer_percent: float = 50.0

    # HIGH_MCP_SHARE: percentage of session tokens from MCP tools
    high_mcp_share_percent: float = 80.0

    # CHATTY: minimum calls to trigger chatty detection
    chatty_call_threshold: int = 20

    # LOW_CACHE_HIT: minimum cache hit rate (cache_read / (cache_read + input))
    low_cache_hit_percent: float = 30.0

    # Minimum calls/tokens to consider for certain patterns
    min_calls_for_variance: int = 3  # Need at least 3 calls to detect variance
    min_tokens_for_consumer: int = 1000  # Ignore tiny token consumers


@dataclass
class SmellDetector:
    """Detects efficiency anti-patterns in session data.

    Usage:
        detector = SmellDetector()
        smells = detector.analyze(session)
        session.smells = smells
    """

    thresholds: SmellThresholds = field(default_factory=SmellThresholds)

    def analyze(self, session: Session) -> List[Smell]:
        """Analyze a session and return all detected smells.

        Args:
            session: Finalized session with tool statistics

        Returns:
            List of Smell objects for detected anti-patterns
        """
        smells: List[Smell] = []

        # Run all detectors
        smells.extend(self._detect_high_variance(session))
        smells.extend(self._detect_top_consumer(session))
        smells.extend(self._detect_high_mcp_share(session))
        smells.extend(self._detect_chatty(session))
        smells.extend(self._detect_low_cache_hit(session))

        return smells

    def _detect_high_variance(self, session: Session) -> List[Smell]:
        """Detect tools with highly variable token counts.

        A high variance indicates inconsistent tool usage that may benefit
        from batching or restructuring.
        """
        smells: List[Smell] = []

        for _server_name, server_session in session.server_sessions.items():
            for tool_name, tool_stats in server_session.tools.items():
                # Need minimum calls and token history
                if tool_stats.calls < self.thresholds.min_calls_for_variance:
                    continue

                # Check if we have token history for variance calculation
                if not hasattr(tool_stats, "token_history") or not tool_stats.token_history:
                    # Fall back to checking if avg vs total suggests high variance
                    # This is a heuristic when we don't have per-call history
                    continue

                # Calculate coefficient of variation
                tokens = tool_stats.token_history
                if len(tokens) < self.thresholds.min_calls_for_variance:
                    continue

                mean = sum(tokens) / len(tokens)
                if mean == 0:
                    continue

                variance = sum((t - mean) ** 2 for t in tokens) / len(tokens)
                std_dev = variance**0.5
                cv = std_dev / mean  # Coefficient of variation

                if cv >= self.thresholds.high_variance_cv:
                    smells.append(
                        Smell(
                            pattern="HIGH_VARIANCE",
                            severity="warning",
                            tool=tool_name,
                            description=f"Token counts vary significantly (CV={cv:.2f})",
                            evidence={
                                "coefficient_of_variation": round(cv, 3),
                                "std_dev": round(std_dev, 1),
                                "mean": round(mean, 1),
                                "min_tokens": min(tokens),
                                "max_tokens": max(tokens),
                                "call_count": len(tokens),
                            },
                        )
                    )

        return smells

    def _detect_top_consumer(self, session: Session) -> List[Smell]:
        """Detect tools consuming >50% of session tokens.

        A single tool dominating token usage may indicate over-reliance
        or opportunities for optimization.
        """
        smells: List[Smell] = []

        # Calculate total MCP tokens
        total_mcp_tokens = sum(ss.total_tokens for ss in session.server_sessions.values())

        if total_mcp_tokens < self.thresholds.min_tokens_for_consumer:
            return smells

        # Find tools consuming high percentage
        for _server_name, server_session in session.server_sessions.items():
            for tool_name, tool_stats in server_session.tools.items():
                if tool_stats.total_tokens < self.thresholds.min_tokens_for_consumer:
                    continue

                percentage = (tool_stats.total_tokens / total_mcp_tokens) * 100

                if percentage >= self.thresholds.top_consumer_percent:
                    smells.append(
                        Smell(
                            pattern="TOP_CONSUMER",
                            severity="info",
                            tool=tool_name,
                            description=f"Consuming {percentage:.1f}% of MCP tokens",
                            evidence={
                                "percentage": round(percentage, 1),
                                "tool_tokens": tool_stats.total_tokens,
                                "total_mcp_tokens": total_mcp_tokens,
                                "calls": tool_stats.calls,
                            },
                        )
                    )

        return smells

    def _detect_high_mcp_share(self, session: Session) -> List[Smell]:
        """Detect when MCP tools consume >80% of session tokens.

        High MCP share may indicate heavy reliance on external tools
        or opportunities to reduce MCP overhead.
        """
        smells: List[Smell] = []

        # Get session total tokens
        total_session_tokens = session.token_usage.total_tokens
        if total_session_tokens == 0:
            return smells

        # Calculate MCP tokens
        total_mcp_tokens = sum(ss.total_tokens for ss in session.server_sessions.values())

        mcp_percentage = (total_mcp_tokens / total_session_tokens) * 100

        if mcp_percentage >= self.thresholds.high_mcp_share_percent:
            smells.append(
                Smell(
                    pattern="HIGH_MCP_SHARE",
                    severity="info",
                    tool=None,  # Session-level smell
                    description=f"MCP tools consuming {mcp_percentage:.1f}% of session tokens",
                    evidence={
                        "mcp_percentage": round(mcp_percentage, 1),
                        "mcp_tokens": total_mcp_tokens,
                        "session_tokens": total_session_tokens,
                        "server_count": len(session.server_sessions),
                    },
                )
            )

        return smells

    def _detect_chatty(self, session: Session) -> List[Smell]:
        """Detect tools called >20 times in a session.

        Chatty tools may benefit from batching or indicate
        inefficient usage patterns.
        """
        smells: List[Smell] = []

        for _server_name, server_session in session.server_sessions.items():
            for tool_name, tool_stats in server_session.tools.items():
                if tool_stats.calls >= self.thresholds.chatty_call_threshold:
                    avg_tokens = (
                        tool_stats.total_tokens / tool_stats.calls if tool_stats.calls > 0 else 0
                    )
                    smells.append(
                        Smell(
                            pattern="CHATTY",
                            severity="warning",
                            tool=tool_name,
                            description=f"Called {tool_stats.calls} times",
                            evidence={
                                "call_count": tool_stats.calls,
                                "threshold": self.thresholds.chatty_call_threshold,
                                "total_tokens": tool_stats.total_tokens,
                                "avg_tokens_per_call": round(avg_tokens, 1),
                            },
                        )
                    )

        return smells

    def _detect_low_cache_hit(self, session: Session) -> List[Smell]:
        """Detect low cache hit rates (<30%).

        Low cache efficiency indicates missed optimization opportunities
        or context that isn't being reused effectively.
        """
        smells: List[Smell] = []

        # Session-level cache analysis
        cache_read = session.token_usage.cache_read_tokens
        cache_created = session.token_usage.cache_created_tokens
        input_tokens = session.token_usage.input_tokens

        # Calculate cache hit rate
        # Hit rate = cache_read / (cache_read + non-cached input)
        # Non-cached input = input - cache_read
        total_input_opportunity = input_tokens + cache_read
        if total_input_opportunity == 0:
            return smells

        # Only check if there's cache activity
        if cache_created == 0 and cache_read == 0:
            return smells

        # Calculate effective hit rate
        hit_rate = (
            (cache_read / total_input_opportunity) * 100 if total_input_opportunity > 0 else 0
        )

        if hit_rate < self.thresholds.low_cache_hit_percent:
            # Determine severity based on how low the hit rate is
            severity = "warning" if hit_rate < 10 else "info"

            smells.append(
                Smell(
                    pattern="LOW_CACHE_HIT",
                    severity=severity,
                    tool=None,  # Session-level smell
                    description=f"Cache hit rate is {hit_rate:.1f}%",
                    evidence={
                        "hit_rate_percent": round(hit_rate, 1),
                        "threshold_percent": self.thresholds.low_cache_hit_percent,
                        "cache_read_tokens": cache_read,
                        "cache_created_tokens": cache_created,
                        "input_tokens": input_tokens,
                    },
                )
            )

        return smells


def detect_smells(
    session: Session,
    thresholds: Optional[SmellThresholds] = None,
) -> List[Smell]:
    """Convenience function to detect smells in a session.

    Args:
        session: Finalized session with tool statistics
        thresholds: Optional custom thresholds (uses defaults if not provided)

    Returns:
        List of Smell objects for detected anti-patterns
    """
    detector = SmellDetector(thresholds=thresholds or SmellThresholds())
    return detector.analyze(session)
