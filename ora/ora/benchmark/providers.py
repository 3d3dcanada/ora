"""
ORA Provider Benchmark - Cross-Provider Comparison Testing
==================================================

Benchmark different LLM providers to compare:
- Performance (latency, throughput)
- Cost efficiency
- Reliability
- Quality (subjective)
"""

import asyncio
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean, median
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProviderBenchmarkResult:
    """Benchmark result for a single provider"""
    provider_name: str
    model: str
    timestamp: str
    
    # Performance
    avg_latency_ms: float
    p95_latency_ms: float
    tokens_per_second: float
    
    # Cost
    cost_per_1k_input: float
    cost_per_1k_output: float
    estimated_monthly_cost: float
    
    # Reliability
    uptime_pct: float
    error_rate: float
    retries_required: int
    
    # Quality scores (1-10)
    reasoning_score: float = 0
    coding_score: float = 0
    creativity_score: float = 0
    accuracy_score: float = 0
    
    # Overall
    overall_score: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider_name,
            "model": self.model,
            "timestamp": self.timestamp,
            "performance": {
                "avg_latency_ms": self.avg_latency_ms,
                "p95_latency_ms": self.p95_latency_ms,
                "tokens_per_second": self.tokens_per_second,
            },
            "cost": {
                "per_1k_input": self.cost_per_1k_input,
                "per_1k_output": self.cost_per_1k_output,
                "monthly_estimate": self.estimated_monthly_cost,
            },
            "reliability": {
                "uptime_pct": self.uptime_pct,
                "error_rate": self.error_rate,
                "retries": self.retries_required,
            },
            "quality": {
                "reasoning": self.reasoning_score,
                "coding": self.coding_score,
                "creativity": self.creativity_score,
                "accuracy": self.accuracy_score,
            },
            "overall_score": self.overall_score,
        }


# Standard benchmark prompts for consistent testing
BENCHMARK_PROMPTS = {
    "reasoning": [
        "A train travels 60 mph. Another train travels 80 mph in the opposite direction. If they start 280 miles apart, how long until they meet?",
        "If all roses are flowers and some flowers fade quickly, can we conclude that some roses fade quickly? Explain your reasoning.",
        "Solve: If 3x + 7 = 22, what is 5x - 3?",
    ],
    "coding": [
        "Write a Python function to find the longest palindrome in a string.",
        "Create a React component that displays a sortable table with pagination.",
        "Write SQL to find the top 5 customers by total order value.",
    ],
    "creative": [
        "Write a haiku about artificial intelligence.",
        "Create a short story about a robot discovering emotions.",
        "Write a product description for a fictional time machine.",
    ],
    "analysis": [
        "Compare and contrast machine learning and deep learning.",
        "What are the main advantages and disadvantages of remote work?",
        "Explain how blockchain technology works to a five-year-old.",
    ],
}


class ProviderBenchmark:
    """
    Comprehensive provider benchmarking class.
    
    Usage:
        benchmark = ProviderBenchmark()
        results = await benchmark.run_all_providers()
        comparison = benchmark.compare_results(results)
    """
    
    def __init__(self, api_client=None):
        self.api_client = api_client
        self.results: List[ProviderBenchmarkResult] = []
    
    async def initialize(self):
        """Initialize API client"""
        if not self.api_client:
            from ..clients.api_client import get_api_client
            self.api_client = get_api_client()
    
    async def benchmark_provider(
        self,
        provider: str,
        model: str,
        num_iterations: int = 5
    ) -> ProviderBenchmarkResult:
        """
        Run comprehensive benchmark for a single provider.
        """
        logger.info(f"Benchmarking {provider}/{model}")
        
        latencies = []
        errors = 0
        retries = 0
        
        # Benchmark reasoning
        reasoning_scores = []
        for prompt in BENCHMARK_PROMPTS["reasoning"][:3]:
            try:
                start = time.time()
                response = await self._call_provider(provider, model, prompt)
                latency = (time.time() - start) * 1000
                latencies.append(latency)
                reasoning_scores.append(self._evaluate_reasoning(response.content))
            except Exception as e:
                errors += 1
                logger.warning(f"Reasoning test failed: {e}")
        
        # Benchmark coding
        coding_scores = []
        for prompt in BENCHMARK_PROMPTS["coding"][:3]:
            try:
                start = time.time()
                response = await self._call_provider(provider, model, prompt)
                latency = (time.time() - start) * 1000
                latencies.append(latency)
                coding_scores.append(self._evaluate_coding(response.content))
            except Exception as e:
                errors += 1
        
        # Benchmark creative
        creativity_scores = []
        for prompt in BENCHMARK_PROMPTS["creative"][:3]:
            try:
                start = time.time()
                response = await self._call_provider(provider, model, prompt)
                latency = (time.time() - start) * 1000
                latencies.append(latency)
                creativity_scores.append(self._evaluate_creativity(response.content))
            except Exception as e:
                errors += 1
        
        # Calculate statistics
        latencies.sort()
        n = len(latencies)
        
        avg_latency = mean(latencies) if latencies else 0
        p95_latency = latencies[int(n * 0.95)] if n > 0 else 0
        
        # Estimate throughput (rough)
        avg_response_tokens = 200  # Approximate
        tokens_per_second = (avg_response_tokens / avg_latency * 1000) if avg_latency > 0 else 0
        
        # Calculate quality scores
        reasoning_score = mean(reasoning_scores) if reasoning_scores else 0
        coding_score = mean(coding_scores) if coding_scores else 0
        creativity_score = mean(creativity_scores) if creativity_scores else 0
        
        # Estimate cost
        input_cost = 0.50  # $/1M tokens (rough estimate)
        output_cost = 1.50
        monthly_cost = self._estimate_monthly_cost(
            avg_latency, 
            input_cost, 
            output_cost,
            requests_per_hour=100
        )
        
        # Calculate overall score
        overall_score = (
            (10 - min(avg_latency / 100, 10)) * 0.3 +  # Latency (30%)
            (10 - errors * 2) * 0.2 +                    # Reliability (20%)
            reasoning_score * 0.2 +                       # Reasoning (20%)
            coding_score * 0.15 +                         # Coding (15%)
            creativity_score * 0.15                        # Creativity (15%)
        )
        
        result = ProviderBenchmarkResult(
            provider_name=provider,
            model=model,
            timestamp=datetime.now().isoformat(),
            avg_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            tokens_per_second=tokens_per_second,
            cost_per_1k_input=input_cost,
            cost_per_1k_output=output_cost,
            estimated_monthly_cost=monthly_cost,
            uptime_pct=(n / (n + errors)) * 100 if (n + errors) > 0 else 0,
            error_rate=errors / (n + errors) if (n + errors) > 0 else 0,
            retries_required=retries,
            reasoning_score=reasoning_score,
            coding_score=coding_score,
            creativity_score=creativity_score,
            accuracy_score=reasoning_score * 0.8 + coding_score * 0.2,
            overall_score=overall_score,
        )
        
        self.results.append(result)
        return result
    
    async def run_all_providers(
        self,
        providers: Optional[List[tuple]] = None
    ) -> List[ProviderBenchmarkResult]:
        """
        Run benchmarks for all configured providers.
        
        Args:
            providers: List of (provider_name, model) tuples
        """
        if not self.api_client:
            await self.initialize()
        
        # Get providers from API client if not specified
        if not providers:
            providers = self._get_default_providers()
        
        results = []
        for provider, model in providers:
            try:
                result = await self.benchmark_provider(provider, model)
                results.append(result)
            except Exception as e:
                logger.error(f"Benchmark failed for {provider}/{model}: {e}")
        
        return results
    
    def _get_default_providers(self) -> List[tuple]:
        """Get default providers to test"""
        # This would come from the API client configuration
        return [
            ("nvidia", "deepseek-ai/deepseek-v3.2"),
            ("kimi", "kimi-k2.5"),
            ("anthropic", "claude-3-5-sonnet-20241022"),
        ]
    
    async def _call_provider(
        self,
        provider: str,
        model: str,
        prompt: str
    ) -> Any:
        """Make a single API call to provider"""
        from ..clients.api_client import TaskType
        
        response = await self.api_client.complete(
            prompt=prompt,
            task_type=TaskType.REASONING,
            provider=provider,
            model=model,
            max_tokens=1024,
            temperature=0.7,
        )
        
        return response
    
    def _evaluate_reasoning(self, response: str) -> float:
        """Evaluate reasoning quality (simplified)"""
        # In production, this would use more sophisticated evaluation
        score = 5.0
        
        # Check for structured reasoning
        if "because" in response.lower():
            score += 1
        if "therefore" in response.lower() or "thus" in response.lower():
            score += 1
        if "first" in response.lower() and "second" in response.lower():
            score += 1
        
        return min(score, 10)
    
    def _evaluate_coding(self, response: str) -> float:
        """Evaluate coding quality (simplified)"""
        score = 5.0
        
        # Check for code blocks
        if "```" in response:
            score += 2
        if "def " in response or "function" in response.lower():
            score += 1
        if "import " in response:
            score += 1
        
        return min(score, 10)
    
    def _evaluate_creativity(self, response: str) -> float:
        """Evaluate creativity (simplified)"""
        score = 5.0
        
        # Check for descriptive language
        adjectives = len([w for w in response.split() if len(w) > 6])
        if adjectives > 10:
            score += 2
        if len(response) > 100:
            score += 1
        
        return min(score, 10)
    
    def _estimate_monthly_cost(
        self,
        avg_latency_ms: float,
        input_cost: float,
        output_cost: float,
        requests_per_hour: int = 100
    ) -> float:
        """Estimate monthly operational cost"""
        hours_per_day = 8
        days_per_month = 22
        avg_tokens_per_request = 500  # Approximate
        
        daily_requests = requests_per_hour * hours_per_day
        monthly_requests = daily_requests * days_per_month
        
        # Rough cost estimate
        monthly_cost = monthly_requests * avg_tokens_per_request * (input_cost + output_cost) / 1_000_000
        
        return monthly_cost
    
    def compare_results(
        self,
        results: Optional[List[ProviderBenchmarkResult]] = None
    ) -> Dict[str, Any]:
        """Compare benchmark results across providers"""
        results = results or self.results
        
        if not results:
            return {}
        
        # Find best in each category
        best_latency = min(results, key=lambda r: r.avg_latency_ms)
        best_cost = min(results, key=lambda r: r.estimated_monthly_cost)
        best_reliability = max(results, key=lambda r: r.uptime_pct)
        best_overall = max(results, key=lambda r: r.overall_score)
        
        # Rank all providers
        ranked = sorted(results, key=lambda r: r.overall_score, reverse=True)
        
        return {
            "best_latency": {
                "provider": best_latency.provider_name,
                "model": best_latency.model,
                "value": f"{best_latency.avg_latency_ms:.1f}ms"
            },
            "best_cost": {
                "provider": best_cost.provider_name,
                "model": best_cost.model,
                "value": f"${best_cost.estimated_monthly_cost:.2f}/month"
            },
            "best_reliability": {
                "provider": best_reliability.provider_name,
                "model": best_reliability.model,
                "value": f"{best_reliability.uptime_pct:.1f}%"
            },
            "best_overall": {
                "provider": best_overall.provider_name,
                "model": best_overall.model,
                "score": best_overall.overall_score
            },
            "rankings": [
                {
                    "rank": i + 1,
                    "provider": r.provider_name,
                    "model": r.model,
                    "score": r.overall_score
                }
                for i, r in enumerate(ranked)
            ],
        }
    
    def generate_report(
        self,
        results: Optional[List[ProviderBenchmarkResult]] = None
    ) -> str:
        """Generate a comprehensive comparison report"""
        results = results or self.results
        
        if not results:
            return "No benchmark results available."
        
        comparison = self.compare_results(results)
        
        lines = [
            "=" * 80,
            "ORA PROVIDER BENCHMARK REPORT",
            "=" * 80,
            f"Generated: {datetime.now().isoformat()}",
            f"Providers Tested: {len(results)}",
            "",
            "BEST IN CATEGORY",
            "-" * 40,
            f"Latency:     {comparison['best_latency']['provider']} ({comparison['best_latency']['value']})",
            f"Cost:        {comparison['best_cost']['provider']} ({comparison['best_cost']['value']})",
            f"Reliability: {comparison['best_reliability']['provider']} ({comparison['best_reliability']['value']})",
            f"Overall:     {comparison['best_overall']['provider']} ({comparison['best_overall']['score']:.2f})",
            "",
            "COMPLETE RANKINGS",
            "-" * 40,
        ]
        
        for r in comparison["rankings"]:
            lines.append(
                f"{r['rank']}. {r['provider']}/{r['model']} - Score: {r['score']:.2f}"
            )
        
        lines.extend(["", "=" * 80])
        
        return "\n".join(lines)


# Convenience function
async def quick_provider_compare() -> Dict[str, Any]:
    """Quick provider comparison"""
    benchmark = ProviderBenchmark()
    await benchmark.initialize()
    results = await benchmark.run_all_providers()
    return benchmark.compare_results(results)
