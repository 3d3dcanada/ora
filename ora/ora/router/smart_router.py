"""
OrA Smart Router - Intelligent LLM model routing
Port from BUZZ Neural Core SmartRouter
"""

import re
from enum import Enum
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class TaskType(Enum):
    REASONING = "reasoning"      # Deep logic, math, complex analysis
    CODING = "coding"            # Code generation, debugging
    CREATIVE = "creative"        # Writing, explanations
    STRUCTURED = "structured"    # JSON, schemas, strict formatting
    CHAT = "chat"                # General conversation
    LONG_CONTEXT = "long_context"  # Document analysis, large inputs


@dataclass
class CloudModel:
    """Model definition with metadata"""
    name: str
    api_name: str
    provider: str  # nvidia, kimi, openai, ollama, etc.
    size: str
    strengths: List[str]
    cost_tier: str  # low, medium, high
    max_tokens: int
    temperature: float
    context_window: int = 8192
    supports_streaming: bool = True
    supports_vision: bool = False
    is_local: bool = False
    last_seen: Optional[str] = None


@dataclass
class ModelCache:
    """Cache for model discovery results"""
    models: Dict[str, CloudModel] = field(default_factory=dict)
    last_updated: Optional[datetime] = None
    ttl_minutes: int = 60
    
    def is_stale(self) -> bool:
        if not self.last_updated:
            return True
        return datetime.now() - self.last_updated > timedelta(minutes=self.ttl_minutes)
    
    def update(self, models: Dict[str, CloudModel]):
        self.models = models
        self.last_updated = datetime.now()


class OraRouter:
    """Intelligent model selection with multi-provider support"""
    
    # Built-in model definitions (fallback when discovery fails)
    BUILTIN_MODELS = {
        # NVIDIA Models
        "deepseek": CloudModel(
            name="DeepSeek-V3.2",
            api_name="deepseek-ai/deepseek-v3.2",
            provider="nvidia",
            size="685B",
            strengths=["complex reasoning", "math", "logic puzzles", "analysis", "planning"],
            cost_tier="high",
            max_tokens=8192,
            temperature=1.0,
            context_window=128000
        ),
        "mistral-large": CloudModel(
            name="Mistral-Large-3",
            api_name="mistralai/mistral-large-3-675b-instruct-2512",
            provider="nvidia",
            size="675B",
            strengths=["general intelligence", "multi-task", "long context", "balanced performance"],
            cost_tier="high",
            max_tokens=2048,
            temperature=0.15,
            context_window=128000
        ),
        "devstral": CloudModel(
            name="Devstral-2",
            api_name="mistralai/devstral-2-123b-instruct-2512",
            provider="nvidia",
            size="123B",
            strengths=["code understanding", "efficiency", "practical coding", "real-world tasks"],
            cost_tier="medium",
            max_tokens=8192,
            temperature=0.15,
            context_window=128000
        ),
        "glm": CloudModel(
            name="GLM-4.7",
            api_name="z-ai/glm4.7",
            provider="nvidia",
            size="4.7B",
            strengths=["structured output", "JSON", "speed", "cost-effective", "thinking mode"],
            cost_tier="low",
            max_tokens=16384,
            temperature=1.0,
            context_window=32000
        ),
        "nemotron": CloudModel(
            name="Nemotron-3-Nano",
            api_name="nvidia/nemotron-3-nano-30b-a3b",
            provider="nvidia",
            size="30B",
            strengths=["reasoning", "thinking mode", "analysis", "fast inference"],
            cost_tier="medium",
            max_tokens=16384,
            temperature=1.0,
            context_window=32000
        ),
        
        # Kimi (Moonshot) Models
        "kimi-2.5": CloudModel(
            name="Kimi-2.5-LongContext",
            api_name="kimi-2.5",
            provider="kimi",
            size="Unknown",
            strengths=["long context", "document analysis", "chinese/english bilingual", "reasoning"],
            cost_tier="medium",
            max_tokens=8192,
            temperature=0.7,
            context_window=256000  # 256K context - Kimi's strength
        ),
        
        # OpenAI Models (fallback definitions)
        "gpt-4o": CloudModel(
            name="GPT-4o",
            api_name="gpt-4o",
            provider="openai",
            size="Unknown",
            strengths=["general intelligence", "vision", "coding", "reasoning"],
            cost_tier="high",
            max_tokens=4096,
            temperature=0.7,
            context_window=128000,
            supports_vision=True
        ),
        "gpt-4o-mini": CloudModel(
            name="GPT-4o-Mini",
            api_name="gpt-4o-mini",
            provider="openai",
            size="Unknown",
            strengths=["cost-effective", "fast", "good quality"],
            cost_tier="low",
            max_tokens=4096,
            temperature=0.7,
            context_window=128000
        ),
    }
    
    # Task detection patterns
    PATTERNS = {
        TaskType.REASONING: [
            r'\b(reason|analyze|logic|solve|math|prove|plan|strategy|architect|design pattern)\b',
            r'\b(complex|difficult|hard|deep thinking|step by step)\b',
            r'(why|how does|explain the concept|theory|algorithm)'
        ],
        TaskType.CODING: [
            r'\b(code|program|function|class|debug|fix|refactor|implement|write.*script)\b',
            r'\b(python|javascript|rust|go|c\+\+|java|html|css|sql|bash)\b',
            r'\b(api|endpoint|database|server|client|frontend|backend)\b',
            r'(git|build|compile|syntax|error|bug)'
        ],
        TaskType.STRUCTURED: [
            r'\b(json|yaml|xml|schema| structured|format|parse|validate)\b',
            r'(extract data|table|csv|convert to|structured output)',
            r'\b(configuration|config file|settings manifest)\b'
        ],
        TaskType.CREATIVE: [
            r'\b(write|create|generate|story|blog|article|email|letter|creative)\b',
            r'\b(improve|enhance|rewrite|polish|tone|style)\b'
        ],
        TaskType.LONG_CONTEXT: [
            r'\b(analyze.*document|summarize.*(paper|pdf|file)|extract.*from.*file)\b',
            r'\b(long context|large file|entire codebase|full text)\b',
            r'(context window|token limit|too long)'
        ]
    }
    
    def __init__(self):
        self.current_model = "glm"  # Default to cheap/safe
        self.cache = ModelCache()
        self.available_models: Dict[str, CloudModel] = dict(self.BUILTIN_MODELS)
    
    def analyze_task(self, prompt: str) -> TaskType:
        """
        Analyze prompt to determine task type
        
        Returns:
            TaskType enum
        """
        if not prompt:
            return TaskType.CHAT
        
        prompt_lower = prompt.lower()
        scores = {task_type: 0 for task_type in TaskType}
        
        # Score each pattern
        for task_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, prompt_lower, re.IGNORECASE)
                scores[task_type] += len(matches)
        
        # Complexity heuristic
        complexity_score = 0
        complexity_indicators = [
            r'\b(complex|difficult|hard|challenging|advanced|sophisticated)\b',
            r'\b(analyze|evaluate|critique|compare|contrast|assess)\b',
            r'\b(algorithm|architecture|design pattern|system design)\b',
            r'\b(prove|demonstrate|derive|calculate|compute)\b'
        ]
        
        for pattern in complexity_indicators:
            complexity_score += len(re.findall(pattern, prompt_lower, re.IGNORECASE))
        
        # Decision logic
        if scores[TaskType.LONG_CONTEXT] > 0:
            return TaskType.LONG_CONTEXT
        elif scores[TaskType.CODING] > 0:
            # Sub-classify coding
            if 'complex' in prompt_lower or 'architecture' in prompt_lower:
                return TaskType.REASONING
            return TaskType.CODING
        elif scores[TaskType.REASONING] > 0 or complexity_score > 30:
            return TaskType.REASONING
        elif scores[TaskType.STRUCTURED] > 0:
            return TaskType.STRUCTURED
        elif scores[TaskType.CREATIVE] > 0:
            return TaskType.CREATIVE
        
        return TaskType.CHAT
    
    def select_model(self, task: TaskType, prompt: str = "", preferred_provider: Optional[str] = None) -> CloudModel:
        """Choose best model for task"""
        
        # Filter by provider if specified
        available = self.available_models
        if preferred_provider:
            available = {k: v for k, v in available.items() if v.provider == preferred_provider}
        
        if not available:
            available = self.BUILTIN_MODELS
        
        if task == TaskType.LONG_CONTEXT:
            # Prioritize models with large context windows
            long_context_models = {
                k: v for k, v in available.items() 
                if v.context_window >= 128000
            }
            if long_context_models:
                # Prefer Kimi for long context (their strength)
                if "kimi-2.5" in long_context_models:
                    return long_context_models["kimi-2.5"]
                return list(long_context_models.values())[0]
        
        if task == TaskType.REASONING:
            candidates = [v for v in available.values() if v.provider == "nvidia" and "deepseek" in v.api_name]
            if candidates:
                return candidates[0]
            return self.BUILTIN_MODELS.get("deepseek", list(available.values())[0])
            
        elif task == TaskType.CODING:
            # Check if needs deep understanding vs quick generation
            if 'legacy' in prompt.lower() or 'understand' in prompt.lower():
                candidates = [v for v in available.values() if v.provider == "nvidia" and "devstral" in v.api_name]
                if candidates:
                    return candidates[0]
            candidates = [v for v in available.values() if v.provider == "nvidia" and "devstral" in v.api_name]
            if candidates:
                return candidates[0]
            return self.BUILTIN_MODELS.get("devstral", list(available.values())[0])
            
        elif task == TaskType.STRUCTURED:
            candidates = [v for v in available.values() if v.provider == "nvidia" and "glm" in v.api_name]
            if candidates:
                return candidates[0]
            return self.BUILTIN_MODELS.get("glm", list(available.values())[0])
            
        elif task == TaskType.CREATIVE:
            candidates = [v for v in available.values() if v.provider == "nvidia" and "mistral" in v.api_name]
            if candidates:
                return candidates[0]
            return self.BUILTIN_MODELS.get("mistral-large", list(available.values())[0])
        else:
            # Chat = GLM for speed/cost
            candidates = [v for v in available.values() if v.provider == "nvidia" and "glm" in v.api_name]
            if candidates:
                return candidates[0]
            return self.BUILTIN_MODELS.get("glm", list(available.values())[0])
    
    def route_request(self, prompt: str, force_model: str = None, preferred_provider: str = None) -> Dict:
        """Route request to appropriate model"""
        
        if force_model and force_model in self.available_models:
            model = self.available_models[force_model]
            task = TaskType.CHAT
        else:
            task = self.analyze_task(prompt)
            model = self.select_model(task, prompt, preferred_provider)
        
        return {
            "task_type": task.value,
            "model": model.name,
            "model_api_name": model.api_name,
            "provider": model.provider,
            "max_tokens": model.max_tokens,
            "temperature": model.temperature,
            "context_window": model.context_window,
            "reasoning": f"Selected for {task.value} task: {', '.join(model.strengths[:3])}"
        }
    
    def get_available_models(self) -> List[Dict]:
        """Get list of available models"""
        return [
            {
                "name": model.name,
                "api_name": model.api_name,
                "provider": model.provider,
                "size": model.size,
                "strengths": model.strengths,
                "cost_tier": model.cost_tier,
                "max_tokens": model.max_tokens,
                "context_window": model.context_window,
                "is_local": model.is_local
            }
            for model in self.available_models.values()
        ]
    
    def add_model(self, model: CloudModel):
        """Add a custom model"""
        self.available_models[model.name.lower()] = model
        logger.info(f"Added model: {model.name}")
    
    def remove_model(self, model_name: str):
        """Remove a model"""
        if model_name.lower() in self.available_models:
            del self.available_models[model_name.lower()]
            logger.info(f"Removed model: {model_name}")