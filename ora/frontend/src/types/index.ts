/**
 * PulZ Type Definitions
 */

export interface Agent {
  id: string;
  name: string;
  type: 'architect' | 'auditor' | 'tester' | 'writer' | 'executor';
  status: 'idle' | 'running' | 'paused' | 'error' | 'killed';
  currentTask?: string;
  progress: number;
  tokenBurn: number;
}

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

export interface WorkflowNode {
  id: string;
  type: 'agent' | 'tool' | 'condition' | 'merge';
  position: { x: number; y: number };
  data: Record<string, any>;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

export interface ToolCall {
  id: string;
  tool: string;
  command: string;
  stdout?: string;
  stderr?: string;
  exitCode: number;
  status: 'running' | 'success' | 'error';
  executionTime: number;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  toolCalls?: ToolCall[];
}
