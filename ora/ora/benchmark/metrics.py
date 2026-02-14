"""
ORA Metrics Collection - Real-time Performance Monitoring
=================================================

Provides metrics collection for:
- Token usage tracking
- Cost accumulation
- Latency histograms
- Provider health monitoring
"""

import time
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from statistics import mean, median
import logging

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Token usage record"""
    timestamp: datetime
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float


@dataclass
class LatencyRecord:
    """Latency measurement record"""
    timestamp: datetime
    provider: str
    model: str
    latency_ms: float
    success: bool
    error_message: Optional[str] = None


class MetricsCollector:
    """
    Real-time metrics collection for ORA LLM Gateway.
    
    Tracks:
    - Token usage per provider/model
    - Cost accumulation
    - Latency histograms
    - Request counts
    - Error rates
    - Provider health
    """
    
    def __init__(self, retention_minutes: int = 60):
        self.retention_minutes = retention_minutes
        
        # Token usage tracking
        self.token_usage: deque[TokenUsage] = deque()
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.total_cost: float = 0.0
        
        # Latency tracking
        self.latencies: deque[LatencyRecord] = deque()
        self.latency_buckets: Dict[str, List[float]] = defaultdict(list)
        
        # Request tracking
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.success_counts: Dict[str, int] = defaultdict(int)
        self.error_counts: Dict[str, int] = defaultdict(int)
        
        # Provider health
        self.provider_health: Dict[str, bool] = {}
        self.last_health_check: Dict[str, datetime] = {}
        
        # Rate limiting
        self.requests_per_minute: Dict[str, deque] = defaultdict(lambda: deque(maxlen=60))
        
        logger.info("Metrics collector initialized")
    
    def record_token_usage(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float
    ):
        """Record token usage from API call"""
        record = TokenUsage(
            timestamp=datetime.now(),
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        )
        self.token_usage.append(record)
        
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += cost
        
        # Cleanup old records
        self._cleanup_old_records()
    
    def record_latency(
        self,
        provider: str,
        model: str,
        latency_ms: float,
        success: bool,
        error_message: Optional[str] = None
    ):
        """Record latency measurement"""
        record = LatencyRecord(
            timestamp=datetime.now(),
            provider=provider,
            model=model,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message
        )
        self.latencies.append(record)
        
        # Add to bucket for histogram
        key = f"{provider}/{model}"
        self.latency_buckets[key].append(latency_ms)
        
        # Update counts
        provider_key = f"{provider}/{model}"
        self.request_counts[provider_key] += 1
        if success:
            self.success_counts[provider_key] += 1
        else:
            self.error_counts[provider_key] += 1
        
        # Track requests per minute
        self.requests_per_minute[provider_key].append(time.time())
        
        # Cleanup old records
        self._cleanup_old_records()
    
    def update_provider_health(self, provider: str, is_healthy: bool):
        """Update provider health status"""
        self.provider_health[provider] = is_healthy
        self.last_health_check[provider] = datetime.now()
    
    def _cleanup_old_records(self):
        """Remove records older than retention period"""
        cutoff = datetime.now() - timedelta(minutes=self.retention_minutes)
        
        # Clean token usage
        while self.token_usage and self.token_usage[0].timestamp < cutoff:
            self.token_usage.popleft()
        
        # Clean latencies
        while self.latencies and self.latencies[0].timestamp < cutoff:
            self.latencies.popleft()
    
    def get_total_tokens(self) -> Dict[str, int]:
        """Get total token counts"""
        return {
            "input": self.total_input_tokens,
            "output": self.total_output_tokens,
            "total": self.total_input_tokens + self.total_output_tokens
        }
    
    def get_total_cost(self) -> float:
        """Get total accumulated cost"""
        return self.total_cost
    
    def get_cost_per_hour(self) -> float:
        """Calculate estimated cost per hour"""
        if not self.token_usage:
            return 0.0
        
        # Get tokens from last hour
        cutoff = datetime.now() - timedelta(hours=1)
        hour_tokens = [t for t in self.token_usage if t.timestamp > cutoff]
        
        if not hour_tokens:
            return 0.0
        
        return sum(t.cost for t in hour_tokens)
    
    def get_tokens_per_hour(self) -> Dict[str, int]:
        """Calculate tokens processed per hour"""
        cutoff = datetime.now() - timedelta(hours=1)
        hour_usage = [t for t in self.token_usage if t.timestamp > cutoff]
        
        return {
            "input": sum(t.input_tokens for t in hour_usage),
            "output": sum(t.output_tokens for t in hour_usage),
            "total": sum(t.input_tokens + t.output_tokens for t in hour_usage)
        }
    
    def get_latency_stats(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """Get latency statistics"""
        if provider:
            records = [l for l in self.latencies if l.provider == provider]
        else:
            records = list(self.latencies)
        
        if not records:
            return {}
        
        latencies = [r.latency_ms for r in records]
        latencies.sort()
        
        n = len(latencies)
        
        return {
            "count": n,
            "avg_ms": mean(latencies),
            "median_ms": median(latencies),
            "min_ms": min(latencies),
            "max_ms": max(latencies),
            "p50_ms": latencies[int(n * 0.50)],
            "p90_ms": latencies[int(n * 0.90)],
            "p95_ms": latencies[int(n * 0.95)] if n > 0 else 0,
            "p99_ms": latencies[int(n * 0.99)] if n > 0 else 0,
        }
    
    def get_error_rate(self, provider: Optional[str] = None) -> float:
        """Calculate error rate"""
        if provider:
            total = sum(1 for r in self.latencies if r.provider == provider)
            errors = sum(1 for r in self.latencies if r.provider == provider and not r.success)
        else:
            total = len(self.latencies)
            errors = sum(1 for r in self.latencies if not r.success)
        
        return errors / total if total > 0 else 0.0
    
    def get_requests_per_minute(self, provider: str) -> float:
        """Get current requests per minute for provider"""
        cutoff = time.time() - 60
        provider_key = provider  # Simplified
        
        recent = [t for t in self.requests_per_minute[provider_key] if t > cutoff]
        return len(recent)
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        status = {}
        
        for provider, is_healthy in self.provider_health.items():
            key = provider
            total = self.request_counts.get(key, 0)
            errors = self.error_counts.get(key, 0)
            
            status[provider] = {
                "healthy": is_healthy,
                "total_requests": total,
                "errors": errors,
                "error_rate": errors / total if total > 0 else 0,
                "last_check": self.last_health_check.get(provider),
            }
        
        return status
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        return {
            "tokens": self.get_total_tokens(),
            "cost": {
                "total": self.total_cost,
                "per_hour": self.get_cost_per_hour(),
            },
            "latency": self.get_latency_stats(),
            "error_rate": self.get_error_rate(),
            "providers": self.get_provider_status(),
            "requests_per_minute": {
                provider: self.get_requests_per_minute(provider)
                for provider in self.provider_health.keys()
            }
        }
    
    def export_json(self) -> Dict[str, Any]:
        """Export all metrics as JSON-serializable dict"""
        return {
            "timestamp": datetime.now().isoformat(),
            "retention_minutes": self.retention_minutes,
            "token_usage": [
                {
                    "timestamp": t.timestamp.isoformat(),
                    "provider": t.provider,
                    "model": t.model,
                    "input_tokens": t.input_tokens,
                    "output_tokens": t.output_tokens,
                    "cost": t.cost
                }
                for t in self.token_usage
            ],
            "totals": self.get_total_tokens(),
            "cost": {
                "total": self.total_cost,
                "per_hour": self.get_cost_per_hour()
            },
            "latency_stats": self.get_latency_stats(),
            "error_rate": self.get_error_rate(),
            "provider_status": self.get_provider_status(),
        }


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
