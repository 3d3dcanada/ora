"""
ORA Benchmark Runner - Enterprise Performance Testing
===================================================

Comprehensive benchmarking for LLM gateways with:
- Throughput testing (tokens/sec)
- Latency analysis (ms)
- Cost estimation
- Provider comparison
- Concurrent load testing
"""

import asyncio
import time
import json
import os
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from statistics import mean, median, stdev
import logging

logger = logging.getLogger(__name__)


class BenchmarkType(Enum):
    """Types of benchmarks available"""
    LATENCY = "latency"              # Response time testing
    THROUGHPUT = "throughput"        # Tokens per second
    CONCURRENT = "concurrent"        # Parallel request handling
    COST = "cost"                    # Cost per million tokens
    CONTEXT = "context"              # Context window utilization
    RELIABILITY = "reliability"      # Error rate testing
    STREAMING = "streaming"          # Streaming performance


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run"""
    benchmark_type: str
    provider: str
    model: str
    timestamp: str
    
    # Core metrics
    total_requests: int
    successful_requests: int
    failed_requests: int
    error_rate: float
    
    # Timing metrics
    avg_latency_ms: float
    median_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    stddev_latency_ms: float
    
    # Throughput metrics
    tokens_per_second: float
    total_tokens: int
    avg_tokens_per_request: float
    
    # Cost metrics
    cost_per_1k_input: float
    cost_per_1k_output: float
    estimated_hourly_cost: float
    estimated_monthly_cost: float
    
    # Context metrics
    context_window_used: int
    max_context_available: int
    context_utilization_pct: float
    
    # Raw data
    raw_latencies: List[float] = field(default_factory=list)
    raw_tokens: List[int] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def summary(self) -> str:
        """Get a summary string"""
        return (
            f"{self.benchmark_type.upper()} | {self.provider}/{self.model} | "
            f"Avg: {self.avg_latency_ms:.1f}ms | "
            f"Throughput: {self.tokens_per_second:.1f} tok/s | "
            f"Error Rate: {self.error_rate:.2%}"
        )


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark runs"""
    # Test parameters
    num_requests: int = 100
    concurrent_requests: int = 1
    warmup_requests: int = 10
    
    # Prompt settings
    prompt_lengths: List[int] = field(default_factory=lambda: [100, 500, 1000, 5000])
    max_tokens: int = 1024
    temperature: float = 0.7
    
    # Provider settings
    providers_to_test: List[str] = field(default_factory=list)
    models_to_test: List[str] = field(default_factory=list)
    
    # Cost settings (default prices per 1M tokens)
    default_input_cost: float = 0.50   # $0.50 per 1M input
    default_output_cost: float = 1.50   # $1.50 per 1M output
    
    # Thresholds
    max_latency_ms: float = 10000
    min_success_rate: float = 0.95
    
    # Output
    save_raw_data: bool = True
    output_dir: str = "./benchmark_results"


class BenchmarkRunner:
    """
    Main benchmark runner for ORA LLM Gateway.
    
    Usage:
        runner = BenchmarkRunner()
        results = await runner.run_all_benchmarks()
        runner.generate_report(results)
    """
    
    def __init__(self, config: Optional[BenchmarkConfig] = None):
        self.config = config or BenchmarkConfig()
        self.results: List[BenchmarkResult] = []
        self.api_client = None
        
        # Ensure output directory exists
        os.makedirs(self.config.output_dir, exist_ok=True)
    
    async def initialize(self):
        """Initialize the API client"""
        from ..clients.api_client import get_api_client
        self.api_client = get_api_client()
        logger.info("Benchmark runner initialized")
    
    async def run_latency_benchmark(
        self,
        provider: str,
        model: str,
        num_requests: Optional[int] = None
    ) -> BenchmarkResult:
        """
        Run latency benchmark - measures response time distribution.
        
        Tests:
        - Average, median, min, max latency
        - P95, P99 percentiles
        - Standard deviation
        """
        num_requests = num_requests or self.config.num_requests
        
        logger.info(f"Running latency benchmark: {provider}/{model}")
        
        latencies = []
        tokens = []
        errors = 0
        
        # Warmup
        for _ in range(self.config.warmup_requests):
            try:
                await self._test_single_request(provider, model)
            except:
                pass
        
        # Actual benchmark
        for i in range(num_requests):
            try:
                start = time.time()
                response = await self._test_single_request(provider, model)
                latency = (time.time() - start) * 1000  # Convert to ms
                
                latencies.append(latency)
                
                # Estimate tokens (rough approximation)
                token_count = len(response.content.split()) * 1.3
                tokens.append(int(token_count))
                
            except Exception as e:
                logger.warning(f"Request {i} failed: {e}")
                errors += 1
            
            # Small delay between requests
            if self.config.concurrent_requests == 1:
                await asyncio.sleep(0.1)
        
        # Calculate statistics
        latencies.sort()
        n = len(latencies)
        
        result = BenchmarkResult(
            benchmark_type="latency",
            provider=provider,
            model=model,
            timestamp=datetime.now().isoformat(),
            total_requests=num_requests,
            successful_requests=n,
            failed_requests=errors,
            error_rate=errors / num_requests if num_requests > 0 else 0,
            avg_latency_ms=mean(latencies) if latencies else 0,
            median_latency_ms=median(latencies) if latencies else 0,
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            p95_latency_ms=latencies[int(n * 0.95)] if n > 0 else 0,
            p99_latency_ms=latencies[int(n * 0.99)] if n > 0 else 0,
            stddev_latency_ms=stdev(latencies) if n > 1 else 0,
            tokens_per_second=0,  # Will be calculated in throughput benchmark
            total_tokens=sum(tokens),
            avg_tokens_per_request=mean(tokens) if tokens else 0,
            cost_per_1k_input=self.config.default_input_cost,
            cost_per_1k_output=self.config.default_output_cost,
            estimated_hourly_cost=0,
            estimated_monthly_cost=0,
            context_window_used=self.config.max_tokens,
            max_context_available=128000,
            context_utilization_pct=0,
            raw_latencies=latencies,
            raw_tokens=tokens,
        )
        
        self.results.append(result)
        return result
    
    async def run_throughput_benchmark(
        self,
        provider: str,
        model: str,
        duration_seconds: int = 60
    ) -> BenchmarkResult:
        """
        Run throughput benchmark - measures tokens processed per second.
        
        Tests:
        - Tokens per second
        - Total tokens processed
        - Requests per second
        """
        logger.info(f"Running throughput benchmark: {provider}/{model}")
        
        latencies = []
        tokens = []
        errors = 0
        start_time = time.time()
        request_count = 0
        
        while time.time() - start_time < duration_seconds:
            try:
                req_start = time.time()
                response = await self._test_single_request(provider, model)
                req_time = time.time() - req_start
                
                latencies.append(req_time * 1000)
                
                token_count = len(response.content.split()) * 1.3
                tokens.append(int(token_count))
                request_count += 1
                
            except Exception as e:
                errors += 1
        
        elapsed = time.time() - start_time
        total_tokens = sum(tokens)
        
        result = BenchmarkResult(
            benchmark_type="throughput",
            provider=provider,
            model=model,
            timestamp=datetime.now().isoformat(),
            total_requests=request_count,
            successful_requests=request_count - errors,
            failed_requests=errors,
            error_rate=errors / request_count if request_count > 0 else 0,
            avg_latency_ms=mean(latencies) if latencies else 0,
            median_latency_ms=median(latencies) if latencies else 0,
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            p95_latency_ms=0,
            p99_latency_ms=0,
            stddev_latency_ms=0,
            tokens_per_second=total_tokens / elapsed if elapsed > 0 else 0,
            total_tokens=total_tokens,
            avg_tokens_per_request=mean(tokens) if tokens else 0,
            cost_per_1k_input=self.config.default_input_cost,
            cost_per_1k_output=self.config.default_output_cost,
            estimated_hourly_cost=0,
            estimated_monthly_cost=0,
            context_window_used=self.config.max_tokens,
            max_context_available=128000,
            context_utilization_pct=0,
            raw_latencies=latencies,
            raw_tokens=tokens,
        )
        
        self.results.append(result)
        return result
    
    async def run_concurrent_benchmark(
        self,
        provider: str,
        model: str,
        concurrent_level: int = 10
    ) -> BenchmarkResult:
        """
        Run concurrent benchmark - tests parallel request handling.
        
        Tests:
        - Requests handled simultaneously
        - Latency under load
        - Error rate under stress
        """
        logger.info(f"Running concurrent benchmark: {provider}/{model} ({concurrent_level} concurrent)")
        
        async def make_request():
            start = time.time()
            try:
                response = await self._test_single_request(provider, model)
                latency = (time.time() - start) * 1000
                tokens = int(len(response.content.split()) * 1.3)
                return latency, tokens, None
            except Exception as e:
                return (time.time() - start) * 1000, 0, str(e)
        
        # Run concurrent requests
        tasks = [make_request() for _ in range(concurrent_level)]
        results = await asyncio.gather(*tasks)
        
        latencies = [r[0] for r in results]
        tokens = [r[1] for r in results]
        errors = sum(1 for r in results if r[2] is not None)
        
        n = len(latencies)
        
        result = BenchmarkResult(
            benchmark_type="concurrent",
            provider=provider,
            model=model,
            timestamp=datetime.now().isoformat(),
            total_requests=concurrent_level,
            successful_requests=n - errors,
            failed_requests=errors,
            error_rate=errors / concurrent_level if concurrent_level > 0 else 0,
            avg_latency_ms=mean(latencies) if latencies else 0,
            median_latency_ms=median(latencies) if latencies else 0,
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            p95_latency_ms=sorted(latencies)[int(n * 0.95)] if n > 0 else 0,
            p99_latency_ms=sorted(latencies)[int(n * 0.99)] if n > 0 else 0,
            stddev_latency_ms=stdev(latencies) if n > 1 else 0,
            tokens_per_second=sum(tokens) / max(latencies) / 1000 if latencies else 0,
            total_tokens=sum(tokens),
            avg_tokens_per_request=mean(tokens) if tokens else 0,
            cost_per_1k_input=self.config.default_input_cost,
            cost_per_1k_output=self.config.default_output_cost,
            estimated_hourly_cost=0,
            estimated_monthly_cost=0,
            context_window_used=self.config.max_tokens,
            max_context_available=128000,
            context_utilization_pct=0,
            raw_latencies=latencies,
            raw_tokens=tokens,
        )
        
        self.results.append(result)
        return result
    
    async def run_cost_benchmark(
        self,
        provider: str,
        model: str,
        input_cost_per_1m: float,
        output_cost_per_1m: float,
        hours_per_day: float = 8,
        days_per_month: float = 22
    ) -> BenchmarkResult:
        """
        Run cost benchmark - estimates operational costs.
        
        Calculates:
        - Cost per 1K input/output tokens
        - Estimated hourly cost at utilization
        - Estimated monthly cost
        """
        logger.info(f"Running cost benchmark: {provider}/{model}")
        
        # Run sample requests to get token counts
        tokens = []
        for _ in range(10):
            try:
                response = await self._test_single_request(provider, model)
                token_count = len(response.content.split()) * 1.3
                tokens.append(int(token_count))
            except:
                pass
        
        avg_tokens = mean(tokens) if tokens else 1000
        
        # Calculate costs
        hourly_requests = 100  # Assuming 100 requests/hour
        hourly_input_tokens = hourly_requests * self.config.max_tokens / 1000
        hourly_output_tokens = hourly_requests * avg_tokens / 1000
        
        hourly_cost = (
            hourly_input_tokens * input_cost_per_1m / 1000000 +
            hourly_output_tokens * output_cost_per_1m / 1000000
        )
        
        monthly_cost = hourly_cost * hours_per_day * days_per_month
        
        result = BenchmarkResult(
            benchmark_type="cost",
            provider=provider,
            model=model,
            timestamp=datetime.now().isoformat(),
            total_requests=10,
            successful_requests=len(tokens),
            failed_requests=10 - len(tokens),
            error_rate=(10 - len(tokens)) / 10,
            avg_latency_ms=0,
            median_latency_ms=0,
            min_latency_ms=0,
            max_latency_ms=0,
            p95_latency_ms=0,
            p99_latency_ms=0,
            stddev_latency_ms=0,
            tokens_per_second=0,
            total_tokens=sum(tokens),
            avg_tokens_per_request=avg_tokens,
            cost_per_1k_input=input_cost_per_1m / 1000,
            cost_per_1k_output=output_cost_per_1m / 1000,
            estimated_hourly_cost=hourly_cost,
            estimated_monthly_cost=monthly_cost,
            context_window_used=self.config.max_tokens,
            max_context_available=128000,
            context_utilization_pct=0,
        )
        
        self.results.append(result)
        return result
    
    async def run_all_benchmarks(
        self,
        providers: Optional[List[str]] = None,
        models: Optional[List[str]] = None
    ) -> List[BenchmarkResult]:
        """
        Run all benchmark types for specified providers/models.
        """
        providers = providers or self.config.providers_to_test
        models = models or self.config.models_to_test
        
        logger.info(f"Running benchmarks for {len(providers)} providers")
        
        for provider in providers:
            for model in models:
                logger.info(f"Benchmarking {provider}/{model}")
                
                # Run all benchmark types
                await self.run_latency_benchmark(provider, model)
                await self.run_throughput_benchmark(provider, model, duration_seconds=30)
                await self.run_concurrent_benchmark(provider, model, concurrent_level=10)
        
        return self.results
    
    async def _test_single_request(self, provider: str, model: str) -> Any:
        """Execute a single test request"""
        if not self.api_client:
            await self.initialize()
        
        from ..clients.api_client import TaskType
        
        # Simple test prompt
        prompt = "Explain quantum computing in simple terms. " * 10
        
        response = await self.api_client.complete(
            prompt=prompt,
            task_type=TaskType.REASONING,
            provider=provider,
            model=model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )
        
        return response
    
    def generate_report(self, results: Optional[List[BenchmarkResult]] = None) -> str:
        """Generate a comprehensive benchmark report"""
        results = results or self.results
        
        report_lines = [
            "=" * 80,
            "ORA BENCHMARK REPORT",
            "=" * 80,
            f"Generated: {datetime.now().isoformat()}",
            f"Total Benchmarks: {len(results)}",
            "",
        ]
        
        # Group by provider
        by_provider = {}
        for r in results:
            key = f"{r.provider}/{r.model}"
            if key not in by_provider:
                by_provider[key] = []
            by_provider[key].append(r)
        
        # Summary table
        report_lines.extend([
            "SUMMARY",
            "-" * 80,
            f"{'Provider/Model':<30} {'Type':<15} {'Avg Latency':<15} {'Tokens/sec':<15} {'Error Rate':<12}",
            "-" * 80,
        ])
        
        for key, res in by_provider.items():
            for r in res:
                report_lines.append(
                    f"{key:<30} {r.benchmark_type:<15} "
                    f"{r.avg_latency_ms:>10.1f}ms {r.tokens_per_second:>10.1f}   {r.error_rate:>10.2%}"
                )
        
        report_lines.extend(["", "=" * 80])
        
        report = "\n".join(report_lines)
        
        # Save to file
        output_file = os.path.join(
            self.config.output_dir,
            f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        with open(output_file, 'w') as f:
            f.write(report)
        
        logger.info(f"Benchmark report saved to {output_file}")
        
        # Also save JSON
        json_file = output_file.replace('.txt', '.json')
        with open(json_file, 'w') as f:
            json.dump([r.to_dict() for r in results], f, indent=2)
        
        return report
    
    def export_csv(self, results: Optional[List[BenchmarkResult]] = None) -> str:
        """Export results to CSV"""
        results = results or self.results
        
        if not results:
            return ""
        
        import csv
        
        output_file = os.path.join(
            self.config.output_dir,
            f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        fieldnames = [
            "benchmark_type", "provider", "model", "timestamp",
            "total_requests", "successful_requests", "failed_requests", "error_rate",
            "avg_latency_ms", "median_latency_ms", "min_latency_ms", "max_latency_ms",
            "p95_latency_ms", "p99_latency_ms", "stddev_latency_ms",
            "tokens_per_second", "total_tokens", "avg_tokens_per_request",
            "cost_per_1k_input", "cost_per_1k_output",
            "estimated_hourly_cost", "estimated_monthly_cost",
            "context_window_used", "max_context_available", "context_utilization_pct",
        ]
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow(r.to_dict())
        
        logger.info(f"CSV export saved to {output_file}")
        return output_file


# Convenience function for quick benchmarks
async def quick_benchmark(
    provider: str,
    model: str,
    num_requests: int = 50
) -> BenchmarkResult:
    """Run a quick latency benchmark"""
    config = BenchmarkConfig(num_requests=num_requests)
    runner = BenchmarkRunner(config)
    await runner.initialize()
    return await runner.run_latency_benchmark(provider, model)
