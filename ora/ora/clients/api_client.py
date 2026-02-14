"""
OrA Universal API Client - Model-Agnostic LLM Gateway
=====================================================

This client is completely model-agnostic. It works with ANY LLM API that follows
the OpenAI-compatible chat completions format. Simply configure your API endpoints
and keys - the system automatically detects capabilities and routes requests.

Supported Providers (via configuration):
- Any OpenAI-compatible API (OpenAI, Azure OpenAI, Local LLM servers)
- Anthropic-compatible APIs
- Google Gemini APIs
- Meta Llama endpoints
- Mistral AI
- Cohere
- Together AI
- Fireworks AI
- Anyscale
- Replicate
- Plus ANY custom endpoint following OpenAI format

No hardcoded model names. No provider-specific logic. Pure configuration.
"""

import os
import json
import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import aiohttp

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Task classification for intelligent routing - completely agnostic to models"""
    REASONING = "reasoning"      # Complex logic, analysis, planning
    CODING = "coding"            # Code generation, debugging
    CREATIVE = "creative"        # Writing, content creation
    STRUCTURED = "structured"    # JSON, data extraction
    CHAT = "chat"                # General conversation
    LONG_CONTEXT = "long_context" # Large document processing
    EMBEDDING = "embedding"      # Vector embeddings


@dataclass
class ProviderConfig:
    """Configuration for ANY LLM provider - fully flexible"""
    name: str                           # Human-readable name
    api_base_url: str                   # Base URL for API
    api_key: str                        # API key (or env var reference)
    models: List[str]                   # Available models
    max_context_window: int = 128000    # Context window size
    supports_streaming: bool = True     # Streaming support
    supports_vision: bool = False       # Vision/image support
    supports_function_calling: bool = True
    cost_tier: str = "medium"          # low, medium, high
    latency_estimate_ms: int = 500      # Expected latency
    reliability_score: float = 1.0      # 0-1 reliability
    is_active: bool = True              # Enable/disable
    custom_headers: Dict[str, str] = field(default_factory=dict)
    extra_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Citation:
    """Source citation for factual claims - model agnostic"""
    file: str
    lines: str
    relevance: float


@dataclass
class LLMResponse:
    """Universal response format - works with any model"""
    content: str
    model: str = ""
    provider: str = ""
    citations: List[Citation] = field(default_factory=list)
    confidence: float = 1.0
    verified: bool = False
    raw_response: Optional[Dict] = None
    usage: Dict[str, int] = field(default_factory=dict)
    latency_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseProvider(ABC):
    """Abstract base class for any LLM provider"""
    
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: str = "",
        **kwargs
    ) -> LLMResponse:
        """Execute completion request"""
        pass
    
    @abstractmethod
    async def streaming_complete(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: str = "",
        callback: Callable[[str], None] = None,
        **kwargs
    ) -> LLMResponse:
        """Execute streaming completion"""
        pass
    
    @abstractmethod
    async def list_models(self) -> List[str]:
        """List available models"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check provider availability"""
        pass


class UniversalProvider(BaseProvider):
    """
    Universal LLM provider that works with ANY OpenAI-compatible API.
    No hardcoded models - everything is configured at runtime.
    """
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self._get_api_key()}",
                    "Content-Type": "application/json",
                    **self.config.custom_headers
                }
            )
        return self._session
    
    def _get_api_key(self) -> str:
        """Resolve API key from config or environment"""
        key = self.config.api_key
        # If starts with "env:", read from environment
        if key.startswith("env:"):
            env_var = key[4:]
            return os.getenv(env_var, "")
        return key
    
    async def complete(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: str = "",
        **kwargs
    ) -> LLMResponse:
        """Execute completion against ANY compatible API"""
        import time
        start_time = time.time()
        
        session = await self._get_session()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        try:
            async with session.post(
                f"{self.config.api_base_url}/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                latency = int((time.time() - start_time) * 1000)
                
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API error ({response.status}): {error_text}")
                
                data = await response.json()
                
                content = data["choices"][0]["message"]["content"]
                
                return LLMResponse(
                    content=content,
                    model=model,
                    provider=self.config.name,
                    raw_response=data,
                    latency_ms=latency,
                    usage=data.get("usage", {}),
                )
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
    
    async def streaming_complete(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: str = "",
        callback: Callable[[str], None] = None,
        **kwargs
    ) -> LLMResponse:
        """Execute streaming completion"""
        import time
        start_time = time.time()
        
        session = await self._get_session()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs
        }
        
        full_content = ""
        
        try:
            async with session.post(
                f"{self.config.api_base_url}/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API error ({response.status}): {error_text}")
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            chunk = data["choices"][0].get("delta", {}).get("content", "")
                            if chunk:
                                full_content += chunk
                                if callback:
                                    callback(chunk)
                        except:
                            pass
                
                latency = int((time.time() - start_time) * 1000)
                
                return LLMResponse(
                    content=full_content,
                    model=model,
                    provider=self.config.name,
                    latency_ms=latency,
                )
                
        except Exception as e:
            logger.error(f"Streaming request failed: {e}")
            raise
    
    async def list_models(self) -> List[str]:
        """List models from API"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.config.api_base_url}/models",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return [m.get("id", "") for m in data.get("data", [])]
        except:
            pass
        return self.config.models  # Fallback to configured models
    
    async def health_check(self) -> bool:
        """Check if provider is available"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.config.api_base_url}/models",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
        except:
            return False


class APIClient:
    """
    Universal Model-Agnostic API Client
    ====================================
    
    Works with ANY LLM provider through configuration. No hardcoded models,
    no provider-specific code. Simply configure your endpoints and the
    system intelligently routes requests.
    
    Example Configuration (in .env):
    ```
    # Provider 1 - Custom endpoint
    PROVIDER_1_NAME=MyGPUCluster
    PROVIDER_1_API_URL=https://api.mycluster.com/v1
    PROVIDER_1_API_KEY=env:MY_API_KEY
    PROVIDER_1_MODELS=gpt-4,claude-3,llama-3
    PROVIDER_1_MAX_CONTEXT=128000
    
    # Provider 2 - Another endpoint
    PROVIDER_2_NAME=AzureOpenAI
    PROVIDER_2_API_URL=https://myresource.openai.azure.com/v1
    PROVIDER_2_API_KEY=env:AZURE_API_KEY
    PROVIDER_2_MODELS=gpt-4-32k,gpt-35-turbo
    
    # Automatic routing based on task characteristics
    ```
    """
    
    # System prompt for citation requirements - model agnostic
    CITATION_SYSTEM_PROMPT = """You are an AI assistant. For every response:
1. Cite sources with file names and line numbers when referencing code/files
2. State your confidence level (0.0-1.0) for each factual claim
3. If uncertain, say "I don't know" rather than guessing
4. Verify claims against provided context before stating them as facts
5. Format citations as: [source:filename:lines]
6. Always be honest about what you know vs what you're uncertain about
"""
    
    def __init__(self, config_overrides: Optional[Dict[str, ProviderConfig]] = None):
        self.providers: Dict[str, UniversalProvider] = {}
        self.provider_configs: Dict[str, ProviderConfig] = {}
        
        # Load providers from environment configuration
        self._load_providers_from_env()
        
        # Apply any config overrides
        if config_overrides:
            for name, config in config_overrides.items():
                self.add_provider(name, config)
        
        logger.info(f"APIClient initialized with {len(self.providers)} providers")
    
    def _load_providers_from_env(self):
        """Load provider configurations from environment variables"""
        env_vars = os.environ.keys()
        
        provider_numbers = set()
        for var in env_vars:
            if var.startswith("PROVIDER_") and "_NAME" in var:
                num = var.split("_")[1]
                provider_numbers.add(num)
        
        for num in sorted(provider_numbers):
            try:
                name = os.getenv(f"PROVIDER_{num}_NAME", f"Provider_{num}")
                api_url = os.getenv(f"PROVIDER_{num}_API_URL", "")
                api_key = os.getenv(f"PROVIDER_{num}_API_KEY", "")
                models_str = os.getenv(f"PROVIDER_{num}_MODELS", "")
                max_context = int(os.getenv(f"PROVIDER_{num}_MAX_CONTEXT", "128000"))
                cost_tier = os.getenv(f"PROVIDER_{num}_COST_TIER", "medium")
                
                if api_url and api_key:
                    config = ProviderConfig(
                        name=name,
                        api_base_url=api_url,
                        api_key=api_key,
                        models=[m.strip() for m in models_str.split(",") if m.strip()],
                        max_context_window=max_context,
                        cost_tier=cost_tier,
                        is_active=True,
                    )
                    self.add_provider(name.lower().replace(" ", "_"), config)
                    logger.info(f"Loaded provider: {name}")
            except Exception as e:
                logger.warning(f"Failed to load provider {num}: {e}")
    
    def add_provider(self, name: str, config: ProviderConfig):
        """Add a provider configuration"""
        self.provider_configs[name] = config
        self.providers[name] = UniversalProvider(config)
        logger.info(f"Added provider: {name} ({config.name})")
    
    def remove_provider(self, name: str):
        """Remove a provider"""
        if name in self.providers:
            del self.providers[name]
            del self.provider_configs[name]
            logger.info(f"Removed provider: {name}")
    
    def get_provider(self, name: str) -> Optional[UniversalProvider]:
        """Get provider by name"""
        return self.providers.get(name)
    
    def list_providers(self) -> List[str]:
        """List all provider names"""
        return list(self.providers.keys())
    
    def select_provider_for_task(
        self,
        task_type: TaskType,
        required_context: int = 4096,
        preferred_provider: Optional[str] = None
    ) -> Optional[tuple[str, UniversalProvider]]:
        """
        Intelligently select the best provider for a task.
        Completely model-agnostic selection logic.
        """
        candidates = []
        
        for name, provider in self.providers.items():
            config = provider.config
            
            if not config.is_active:
                continue
            
            # Skip if doesn't meet context requirements
            if required_context > config.max_context_window:
                continue
            
            # Score the provider
            score = 0.0
            
            # Provider preference
            if preferred_provider and name == preferred_provider:
                score += 100
            
            # Reliability score
            score += config.reliability_score * 50
            
            # Cost consideration
            if task_type == TaskType.CHAT:
                if config.cost_tier == "low":
                    score += 30
            elif task_type == TaskType.REASONING or task_type == TaskType.CODING:
                if config.cost_tier in ["medium", "high"]:
                    score += 20
            
            # Context window suitability
            context_score = min(config.max_context_window / required_context, 2.0)
            score += context_score * 10
            
            # Latency
            if config.latency_estimate_ms < 500:
                score += 20
            elif config.latency_estimate_ms < 1000:
                score += 10
            
            candidates.append((name, provider, score))
        
        if not candidates:
            return None
        
        # Return highest scoring provider
        candidates.sort(key=lambda x: x[2], reverse=True)
        return (candidates[0][0], candidates[0][1])
    
    def select_model_for_task(
        self,
        task_type: TaskType,
        provider_config: ProviderConfig
    ) -> str:
        """
        Select the best model from a provider's available models.
        Completely agnostic - just picks from the list.
        """
        models = provider_config.models
        
        if not models:
            raise ValueError(f"No models configured for provider {provider_config.name}")
        
        if len(models) == 1:
            return models[0]
        
        return models[0]
    
    async def complete(
        self,
        prompt: str,
        task_type: TaskType = TaskType.CHAT,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        max_context: bool = True,
        **kwargs
    ) -> LLMResponse:
        """
        Execute LLM completion with automatic provider/model selection.
        """
        system_prompt = self.CITATION_SYSTEM_PROMPT
        
        if max_context:
            system_prompt += "\nUse the full context window available."
        
        required_context = kwargs.get("max_tokens", 4096)
        
        if provider and provider in self.providers:
            selected_provider = self.providers[provider]
            provider_name = provider
        else:
            result = self.select_provider_for_task(task_type, required_context)
            if not result:
                raise Exception("No available providers for this task")
            provider_name, selected_provider = result
        
        if model:
            selected_model = model
        else:
            selected_model = self.select_model_for_task(task_type, selected_provider.config)
        
        try:
            response = await selected_provider.complete(
                prompt=prompt,
                model=selected_model,
                system_prompt=system_prompt,
                **kwargs
            )
            
            response.citations = self._parse_citations(response.content)
            response.confidence = self._estimate_confidence(response.content)
            response.verified = len(response.citations) > 0 or response.confidence > 0.8
            
            return response
            
        except Exception as e:
            logger.error(f"Request failed: {e}")
            
            # Try other providers if primary fails
            for name, prov in self.providers.items():
                if name != provider_name and prov.config.is_active:
                    try:
                        alt_model = self.select_model_for_task(task_type, prov.config)
                        response = await prov.complete(
                            prompt=prompt,
                            model=alt_model,
                            system_prompt=system_prompt,
                            **kwargs
                        )
                        response.citations = self._parse_citations(response.content)
                        response.confidence = self._estimate_confidence(response.content)
                        logger.info(f"Fallback succeeded with provider {name}")
                        return response
                    except:
                        continue
            
            raise Exception(f"All providers failed. Last error: {e}")
    
    async def streaming_complete(
        self,
        prompt: str,
        task_type: TaskType = TaskType.CHAT,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        callback: Callable[[str], None] = None,
        **kwargs
    ) -> LLMResponse:
        """Execute streaming completion"""
        system_prompt = self.CITATION_SYSTEM_PROMPT
        
        if provider and provider in self.providers:
            selected_provider = self.providers[provider]
        else:
            result = self.select_provider_for_task(task_type)
            if not result:
                raise Exception("No available providers")
            _, selected_provider = result
        
        if model:
            selected_model = model
        else:
            selected_model = self.select_model_for_task(task_type, selected_provider.config)
        
        return await selected_provider.streaming_complete(
            prompt=prompt,
            model=selected_model,
            system_prompt=system_prompt,
            callback=callback,
            **kwargs
        )
    
    def _parse_citations(self, content: str) -> List[Citation]:
        """Parse citations from response - model agnostic"""
        citations = []
        import re
        pattern = r'\[source:([^:]+):([^\]]+)\]'
        matches = re.findall(pattern, content)
        
        for file, lines in matches:
            citations.append(Citation(
                file=file.strip(),
                lines=lines.strip(),
                relevance=1.0
            ))
        
        return citations
    
    def _estimate_confidence(self, content: str) -> float:
        """Estimate confidence from response characteristics"""
        content_lower = content.lower()
        
        uncertainty_markers = [
            "i don't know", "i'm not sure", "uncertain", "unclear",
            "might be", "could be", "perhaps", "possibly", 
            "i believe", "i think", "probably"
        ]
        
        uncertainty_count = sum(1 for marker in uncertainty_markers if marker in content_lower)
        
        if uncertainty_count > 2:
            return 0.5
        elif uncertainty_count > 0:
            return 0.7
        
        if "[source:" in content_lower:
            return 0.9
        
        return 0.8
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all providers"""
        results = {}
        
        for name, provider in self.providers.items():
            try:
                is_healthy = await provider.health_check()
                results[name] = {
                    "healthy": is_healthy,
                    "name": provider.config.name,
                    "models": provider.config.models,
                    "latency_ms": provider.config.latency_estimate_ms,
                }
            except Exception as e:
                results[name] = {
                    "healthy": False,
                    "name": provider.config.name,
                    "error": str(e),
                }
        
        return results
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get all available models across all providers"""
        models = []
        
        for name, config in self.provider_configs.items():
            for model in config.models:
                models.append({
                    "model": model,
                    "provider": config.name,
                    "provider_key": name,
                    "context_window": config.max_context_window,
                    "cost_tier": config.cost_tier,
                    "active": config.is_active,
                })
        
        return models
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary"""
        return {
            "total_providers": len(self.providers),
            "total_models": sum(len(c.models) for c in self.provider_configs.values()),
            "providers": {
                name: {
                    "name": config.name,
                    "api_url": config.api_base_url,
                    "models_count": len(config.models),
                    "max_context": config.max_context_window,
                    "cost_tier": config.cost_tier,
                    "active": config.is_active,
                }
                for name, config in self.provider_configs.items()
            }
        }


# Singleton instance
_api_client: Optional[APIClient] = None


def get_api_client(config_overrides: Optional[Dict[str, ProviderConfig]] = None) -> APIClient:
    """Get singleton API client instance"""
    global _api_client
    if _api_client is None:
        _api_client = APIClient(config_overrides)
    return _api_client


def create_api_client(
    providers: List[ProviderConfig],
    auto_route: bool = True
) -> APIClient:
    """
    Create a new API client with specified providers.
    """
    config_overrides = {}
    for i, provider in enumerate(providers):
        key = f"provider_{i}"
        config_overrides[key] = provider
    
    return APIClient(config_overrides)
