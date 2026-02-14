/**
 * PulZ Left Sidebar
 * Tool Palette, Model Selector, Authority Badge, Vault Status
 */

import { useState } from 'react';
import { 
  Lock, Unlock, Shield, Cpu, Globe, FileCode, 
  Database, Terminal, Sparkles, Image, ChevronDown,
  ChevronRight, Key, Zap, User
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { usePulzStore, type MCPTool, type ToolCategory } from '@/store/pulzStore';

// Category icons mapping
const CATEGORY_ICONS: Record<ToolCategory, React.ElementType> = {
  file: FileCode,
  web: Globe,
  code: Terminal,
  security: Shield,
  data: Database,
  system: Cpu,
  ai: Sparkles,
  media: Image,
};

// Category colors
const CATEGORY_COLORS: Record<ToolCategory, string> = {
  file: 'text-blue-400',
  web: 'text-green-400',
  code: 'text-yellow-400',
  security: 'text-red-400',
  data: 'text-purple-400',
  system: 'text-gray-400',
  ai: 'text-cyan-400',
  media: 'text-pink-400',
};

export function LeftSidebar() {
  const [expandedCategories, setExpandedCategories] = useState<Set<ToolCategory>>(
    new Set(['ai', 'code'])
  );
  const [vaultPassword, setVaultPassword] = useState('');
  const [isUnlockDialogOpen, setIsUnlockDialogOpen] = useState(false);
  
  const { 
    tools, 
    selectedTools, 
    toggleTool,
    models,
    selectedModel,
    setSelectedModel,
    vaultStatus,
    unlockVault,
    lockVault,
    authority,
    agents
  } = usePulzStore();

  // Group tools by category
  const toolsByCategory = tools.reduce((acc, tool) => {
    if (!acc[tool.category]) acc[tool.category] = [];
    acc[tool.category].push(tool);
    return acc;
  }, {} as Record<ToolCategory, MCPTool[]>);

  const toggleCategory = (category: ToolCategory) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(category)) {
      newExpanded.delete(category);
    } else {
      newExpanded.add(category);
    }
    setExpandedCategories(newExpanded);
  };

  const handleUnlockVault = async () => {
    const success = await unlockVault(vaultPassword);
    if (success) {
      toast.success('Vault Unlocked', { description: 'Your API keys are now accessible' });
      setIsUnlockDialogOpen(false);
      setVaultPassword('');
    } else {
      toast.error('Unlock Failed', { description: 'Invalid password' });
    }
  };

  const handleLockVault = async () => {
    await lockVault();
    toast.info('Vault Locked', { description: 'API keys secured' });
  };

  const selectedModelConfig = models.find(m => m.id === selectedModel);

  return (
    <div className="h-full bg-[#161b22] border-r border-gray-800 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
            PulZ
          </h1>
        </div>
        
        {/* Model Selector */}
        <div className="space-y-2">
          <label className="text-xs text-gray-500 uppercase tracking-wider">AI Model</label>
          <Select value={selectedModel} onValueChange={setSelectedModel}>
            <SelectTrigger className="bg-[#0d1117] border-gray-700 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#161b22] border-gray-700">
              {models.map(model => (
                <SelectItem 
                  key={model.id} 
                  value={model.id}
                  className="text-sm"
                >
                  <div className="flex items-center justify-between w-full gap-4">
                    <span>{model.name}</span>
                    <span className="text-xs text-gray-500">
                      {model.contextWindow >= 1000 
                        ? `${(model.contextWindow / 1000).toFixed(0)}K` 
                        : model.contextWindow} ctx
                    </span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          {/* Model Info */}
          {selectedModelConfig && (
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <Badge variant="outline" className="text-xs">
                {selectedModelConfig.provider}
              </Badge>
              <span className={`
                ${selectedModelConfig.costTier === 'free' ? 'text-green-400' : ''}
                ${selectedModelConfig.costTier === 'low' ? 'text-yellow-400' : ''}
                ${selectedModelConfig.costTier === 'medium' ? 'text-orange-400' : ''}
                ${selectedModelConfig.costTier === 'high' ? 'text-red-400' : ''}
              `}>
                {selectedModelConfig.costTier}
              </span>
              <span className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                45ms
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Authority Badge */}
      <div className="px-4 py-3 border-b border-gray-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <User className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-300">Authority</span>
          </div>
          <Badge 
            className={`
              ${authority.level === 'A5' ? 'bg-red-600' : ''}
              ${authority.level === 'A4' ? 'bg-orange-600' : ''}
              ${authority.level === 'A3' ? 'bg-yellow-600' : ''}
              ${authority.level === 'A2' ? 'bg-blue-600' : ''}
              ${authority.level === 'A1' ? 'bg-green-600' : ''}
              ${authority.level === 'A0' ? 'bg-gray-600' : ''}
            `}
          >
            {authority.level}
          </Badge>
        </div>
        <div className="mt-2 flex gap-1 flex-wrap">
          {authority.permissions.map(perm => (
            <span key={perm} className="text-xs text-gray-500 capitalize">{perm}</span>
          ))}
        </div>
      </div>

      {/* Vault Status */}
      <div className="px-4 py-3 border-b border-gray-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Key className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-300">Vault</span>
          </div>
          {vaultStatus.isLocked ? (
            <Dialog open={isUnlockDialogOpen} onOpenChange={setIsUnlockDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="ghost" size="sm" className="h-6 px-2">
                  <Lock className="w-4 h-4 text-red-400" />
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-[#161b22] border-gray-700">
                <DialogHeader>
                  <DialogTitle>Unlock Quantum Vault</DialogTitle>
                  <DialogDescription>
                    Enter your vault password to access API keys
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 pt-4">
                  <Input
                    type="password"
                    placeholder="Vault password"
                    value={vaultPassword}
                    onChange={(e) => setVaultPassword(e.target.value)}
                    className="bg-[#0d1117] border-gray-700"
                  />
                  <Button onClick={handleUnlockVault} className="w-full">
                    <Unlock className="w-4 h-4 mr-2" />
                    Unlock
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          ) : (
            <Button variant="ghost" size="sm" className="h-6 px-2" onClick={handleLockVault}>
              <Unlock className="w-4 h-4 text-green-400" />
            </Button>
          )}
        </div>
        <div className="mt-1 text-xs text-gray-500">
          {vaultStatus.tier}
        </div>
      </div>

      {/* Tool Palette */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-4">
          <label className="text-xs text-gray-500 uppercase tracking-wider mb-3 block">
            Tool Palette ({tools.length} tools)
          </label>
          
          <div className="space-y-1">
            {(Object.keys(toolsByCategory) as ToolCategory[]).map(category => {
              const Icon = CATEGORY_ICONS[category];
              const isExpanded = expandedCategories.has(category);
              const categoryTools = toolsByCategory[category];
              
              return (
                <div key={category}>
                  <button
                    onClick={() => toggleCategory(category)}
                    className="w-full flex items-center gap-2 px-2 py-1.5 rounded hover:bg-gray-800 transition-colors"
                  >
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-gray-500" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-gray-500" />
                    )}
                    <Icon className={`w-4 h-4 ${CATEGORY_COLORS[category]}`} />
                    <span className="text-sm text-gray-300 capitalize flex-1 text-left">
                      {category}
                    </span>
                    <span className="text-xs text-gray-500">
                      {categoryTools.length}
                    </span>
                  </button>
                  
                  {isExpanded && (
                    <div className="ml-6 mt-1 space-y-1">
                      {categoryTools.map(tool => (
                        <button
                          key={tool.id}
                          onClick={() => toggleTool(tool.id)}
                          className={`
                            w-full flex items-center gap-2 px-2 py-1.5 rounded text-left
                            transition-colors
                            ${selectedTools.includes(tool.id) 
                              ? 'bg-cyan-900/30 border border-cyan-700/50' 
                              : 'hover:bg-gray-800'
                            }
                          `}
                        >
                          <div className={`
                            w-2 h-2 rounded-full
                            ${selectedTools.includes(tool.id) ? 'bg-cyan-400' : 'bg-gray-600'}
                          `} />
                          <div className="flex-1 min-w-0">
                            <div className="text-sm text-gray-300 truncate">
                              {tool.name}
                            </div>
                            <div className="text-xs text-gray-500 truncate">
                              {tool.description}
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Footer - Agent Count */}
      <div className="p-4 border-t border-gray-800">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-500">Active Agents</span>
          <Badge variant="secondary">
            {agents.filter(a => a.status !== 'killed').length}/{agents.length}
          </Badge>
        </div>
      </div>
    </div>
  );
}
