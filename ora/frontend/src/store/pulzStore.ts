/**
 * PulZ Global State Store
 * Uses Zustand for state management
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Types
export interface MCPTool {
  id: string;
  name: string;
  description: string;
  category: ToolCategory;
  icon?: string;
}

export type ToolCategory = 
  | 'file' 
  | 'web' 
  | 'code' 
  | 'security' 
  | 'data' 
  | 'system' 
  | 'ai' 
  | 'media';

export interface ModelConfig {
  id: string;
  name: string;
  provider: 'kimi' | 'nvidia' | 'anthropic' | 'local';
  contextWindow: number;
  costTier: 'free' | 'low' | 'medium' | 'high';
  baseUrl?: string;
  latency?: number;
}

export interface Agent {
  id: string;
  name: string;
  type: 'architect' | 'auditor' | 'tester' | 'writer' | 'executor';
  status: 'idle' | 'running' | 'paused' | 'error' | 'killed';
  currentTask?: string;
  progress: number;
  tokenBurn: number;
}

export interface SecurityGate {
  id: string;
  name: string;
  status: 'secure' | 'warning' | 'breach';
  lastCheck: number;
  threatCount: number;
}

export interface VaultStatus {
  isLocked: boolean;
  tier: string;
  lastUnlocked?: number;
}

export interface AuthorityLevel {
  level: 'A0' | 'A1' | 'A2' | 'A3' | 'A4' | 'A5';
  permissions: string[];
}

interface PulzState {
  // Initialization
  isInitialized: boolean;
  initialize: () => Promise<void>;
  
  // Vault
  vaultStatus: VaultStatus;
  checkVaultStatus: () => Promise<void>;
  unlockVault: (password: string) => Promise<boolean>;
  lockVault: () => Promise<void>;
  
  // Tools
  tools: MCPTool[];
  selectedTools: string[];
  toggleTool: (toolId: string) => void;
  
  // Models
  models: ModelConfig[];
  selectedModel: string;
  setSelectedModel: (modelId: string) => void;
  
  // Agents
  agents: Agent[];
  killAgent: (agentId: string) => void;
  pauseAgent: (agentId: string) => void;
  resumeAgent: (agentId: string) => void;
  
  // Security
  securityGates: SecurityGate[];
  
  // Authority
  authority: AuthorityLevel;
  requestEscalation: () => Promise<void>;
  
  // System Metrics
  cpuUsage: number;
  gpuUsage: number;
  memoryUsage: number;
  tokenCost: number;
  networkLatency: number;
}

// Built-in MCP tools (400+ tools would be loaded from MCP Bridge)
const BUILT_IN_TOOLS: MCPTool[] = [
  { id: 'fs_read', name: 'Read File', description: 'Read file contents', category: 'file' },
  { id: 'fs_write', name: 'Write File', description: 'Write to file', category: 'file' },
  { id: 'fs_list', name: 'List Directory', description: 'List directory contents', category: 'file' },
  { id: 'web_fetch', name: 'Fetch URL', description: 'Fetch web content', category: 'web' },
  { id: 'web_search', name: 'Web Search', description: 'Search the web', category: 'web' },
  { id: 'code_execute', name: 'Execute Code', description: 'Execute code snippet', category: 'code' },
  { id: 'code_lint', name: 'Lint Code', description: 'Lint code for errors', category: 'code' },
  { id: 'git_commit', name: 'Git Commit', description: 'Create git commit', category: 'code' },
  { id: 'security_scan', name: 'Security Scan', description: 'Scan for vulnerabilities', category: 'security' },
  { id: 'data_query', name: 'Query Data', description: 'Query database', category: 'data' },
  { id: 'system_exec', name: 'System Command', description: 'Execute system command', category: 'system' },
  { id: 'ai_generate', name: 'AI Generate', description: 'Generate with AI', category: 'ai' },
  { id: 'media_convert', name: 'Convert Media', description: 'Convert media files', category: 'media' },
];

// Model registry (10+ models)
const MODEL_REGISTRY: ModelConfig[] = [
  { 
    id: 'kimi-2.5', 
    name: 'Kimi 2.5 (200K)', 
    provider: 'kimi', 
    contextWindow: 200000, 
    costTier: 'medium',
    baseUrl: 'https://api.moonshot.cn'
  },
  { 
    id: 'nvidia-mistral-3', 
    name: 'Mistral Large 3 (675B)', 
    provider: 'nvidia', 
    contextWindow: 128000, 
    costTier: 'high' 
  },
  { 
    id: 'nvidia-deepseek-v3', 
    name: 'DeepSeek V3 (685B)', 
    provider: 'nvidia', 
    contextWindow: 64000, 
    costTier: 'medium' 
  },
  { 
    id: 'nvidia-devstral-2', 
    name: 'Devstral 2 (123B)', 
    provider: 'nvidia', 
    contextWindow: 32000, 
    costTier: 'low' 
  },
  { 
    id: 'nvidia-nemotron', 
    name: 'Nemotron (340B)', 
    provider: 'nvidia', 
    contextWindow: 128000, 
    costTier: 'high' 
  },
  { 
    id: 'nvidia-glm-4', 
    name: 'GLM-4.7 (9B)', 
    provider: 'nvidia', 
    contextWindow: 32000, 
    costTier: 'low' 
  },
  { 
    id: 'claude-3-5-sonnet', 
    name: 'Claude 3.5 Sonnet', 
    provider: 'anthropic', 
    contextWindow: 200000, 
    costTier: 'high' 
  },
  { 
    id: 'claude-3-haiku', 
    name: 'Claude 3 Haiku', 
    provider: 'anthropic', 
    contextWindow: 200000, 
    costTier: 'low' 
  },
  { 
    id: 'ollama-llama3', 
    name: 'Llama 3 (Local)', 
    provider: 'local', 
    contextWindow: 32000, 
    costTier: 'free' 
  },
  { 
    id: 'ollama-mistral', 
    name: 'Mistral (Local)', 
    provider: 'local', 
    contextWindow: 32000, 
    costTier: 'free' 
  },
];

// Security gates (6 gates)
const SECURITY_GATES: SecurityGate[] = [
  { id: 'prompt_injection', name: 'Prompt Injection', status: 'secure', lastCheck: Date.now(), threatCount: 0 },
  { id: 'shell_sanitizer', name: 'Shell Sanitizer', status: 'secure', lastCheck: Date.now(), threatCount: 0 },
  { id: 'sandbox', name: 'Sandbox', status: 'secure', lastCheck: Date.now(), threatCount: 0 },
  { id: 'credentials', name: 'Credentials', status: 'secure', lastCheck: Date.now(), threatCount: 0 },
  { id: 'network', name: 'Network', status: 'secure', lastCheck: Date.now(), threatCount: 0 },
  { id: 'workspace', name: 'Workspace', status: 'secure', lastCheck: Date.now(), threatCount: 0 },
];

// Mock agents
const MOCK_AGENTS: Agent[] = [
  { id: 'agent_1', name: 'CodeArchitect', type: 'architect', status: 'idle', progress: 0, tokenBurn: 0 },
  { id: 'agent_2', name: 'SecurityAuditor', type: 'auditor', status: 'idle', progress: 0, tokenBurn: 0 },
  { id: 'agent_3', name: 'TestEngineer', type: 'tester', status: 'idle', progress: 0, tokenBurn: 0 },
  { id: 'agent_4', name: 'DocWriter', type: 'writer', status: 'idle', progress: 0, tokenBurn: 0 },
];

export const usePulzStore = create<PulzState>()(
  persist(
    (set, get) => ({
      // Initialization
      isInitialized: false,
      initialize: async () => {
        // Simulate initialization
        await new Promise(resolve => setTimeout(resolve, 1500));
        set({ isInitialized: true });
      },
      
      // Vault
      vaultStatus: { isLocked: true, tier: 'TIER_1_MODERN' },
      checkVaultStatus: async () => {
        // Check vault status from API
        try {
          const response = await fetch('http://localhost:8000/vault/status');
          const data = await response.json();
          set({ vaultStatus: { isLocked: !data.unlocked, tier: data.tier } });
        } catch (error) {
          console.error('Vault check failed:', error);
        }
      },
      unlockVault: async (password: string) => {
        try {
          const hardwareId = 'mock-hardware-id';
          const response = await fetch('http://localhost:8000/vault/unlock', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password, hardware_id: hardwareId })
          });
          const data = await response.json();
          if (data.unlocked) {
            set({ vaultStatus: { ...get().vaultStatus, isLocked: false, lastUnlocked: Date.now() } });
            return true;
          }
          return false;
        } catch (error) {
          console.error('Vault unlock failed:', error);
          return false;
        }
      },
      lockVault: async () => {
        try {
          await fetch('http://localhost:8000/vault/lock', { method: 'POST' });
          set({ vaultStatus: { ...get().vaultStatus, isLocked: true } });
        } catch (error) {
          console.error('Vault lock failed:', error);
        }
      },
      
      // Tools
      tools: BUILT_IN_TOOLS,
      selectedTools: [],
      toggleTool: (toolId: string) => {
        const { selectedTools } = get();
        if (selectedTools.includes(toolId)) {
          set({ selectedTools: selectedTools.filter(id => id !== toolId) });
        } else {
          set({ selectedTools: [...selectedTools, toolId] });
        }
      },
      
      // Models
      models: MODEL_REGISTRY,
      selectedModel: 'kimi-2.5',
      setSelectedModel: (modelId: string) => {
        set({ selectedModel: modelId });
      },
      
      // Agents
      agents: MOCK_AGENTS,
      killAgent: (agentId: string) => {
        const { agents } = get();
        set({
          agents: agents.map(agent =>
            agent.id === agentId ? { ...agent, status: 'killed' as const } : agent
          )
        });
      },
      pauseAgent: (agentId: string) => {
        const { agents } = get();
        set({
          agents: agents.map(agent =>
            agent.id === agentId ? { ...agent, status: 'paused' as const } : agent
          )
        });
      },
      resumeAgent: (agentId: string) => {
        const { agents } = get();
        set({
          agents: agents.map(agent =>
            agent.id === agentId ? { ...agent, status: 'idle' as const } : agent
          )
        });
      },
      
      // Security
      securityGates: SECURITY_GATES,
      
      // Authority
      authority: { level: 'A2', permissions: ['read', 'write', 'execute'] },
      requestEscalation: async () => {
        // Simulate escalation request
        await new Promise(resolve => setTimeout(resolve, 1000));
      },
      
      // System Metrics (simulated)
      cpuUsage: 15,
      gpuUsage: 8,
      memoryUsage: 32,
      tokenCost: 0.0042,
      networkLatency: 45,
    }),
    {
      name: 'pulz-storage',
      partialize: (state) => ({ 
        selectedModel: state.selectedModel,
        authority: state.authority 
      }),
    }
  )
);
