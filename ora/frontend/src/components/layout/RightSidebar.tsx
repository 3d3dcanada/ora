/**
 * PulZ Right Sidebar
 * Agent Swarm Monitor, Security Dashboard, System Metrics
 */

import { useEffect, useState } from 'react';
import { 
  Activity, Shield, Cpu, Zap, AlertTriangle, 
  CheckCircle, XCircle, Pause, Play, Skull,
  TrendingUp, Wifi, DollarSign
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { toast } from 'sonner';
import { usePulzStore, type Agent } from '@/store/pulzStore';

// Agent type icons
const AGENT_ICONS: Record<Agent['type'], React.ElementType> = {
  architect: Zap,
  auditor: Shield,
  tester: Activity,
  writer: Activity,
  executor: Cpu,
};

// Agent type colors
const AGENT_COLORS: Record<Agent['type'], string> = {
  architect: 'text-cyan-400',
  auditor: 'text-green-400',
  tester: 'text-yellow-400',
  writer: 'text-purple-400',
  executor: 'text-orange-400',
};

export function RightSidebar() {
  const { 
    agents, 
    killAgent, 
    pauseAgent, 
    resumeAgent,
    securityGates,
    cpuUsage,
    gpuUsage,
    memoryUsage,
    tokenCost,
    networkLatency
  } = usePulzStore();

  const [auditLog, setAuditLog] = useState<string[]>([
    '[10:42:15] System initialized',
    '[10:42:16] Vault locked (TIER_1_MODERN)',
    '[10:42:18] 4 agents loaded',
    '[10:42:20] Security gates: 6/6 secure',
  ]);

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      // Add random audit log entries
      if (Math.random() > 0.9) {
        const events = [
          'Security scan completed',
          'Agent heartbeat received',
          'Token usage updated',
          'Network latency check',
        ];
        const event = events[Math.floor(Math.random() * events.length)];
        const time = new Date().toLocaleTimeString('en-US', { hour12: false });
        setAuditLog(prev => [`[${time}] ${event}`, ...prev].slice(0, 50));
      }
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const handleKillAgent = (agentId: string, agentName: string) => {
    killAgent(agentId);
    toast.warning(`Agent ${agentName} terminated`, {
      description: 'Kill switch activated'
    });
  };

  const activeAgents = agents.filter(a => a.status !== 'killed');
  const totalTokenBurn = agents.reduce((sum, a) => sum + a.tokenBurn, 0);

  return (
    <div className="h-full bg-[#161b22] border-l border-gray-800 flex flex-col">
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-6">
          
          {/* Agent Swarm Monitor */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyan-400" />
                Agent Swarm
              </h3>
              <Badge variant="outline" className="text-xs">
                {activeAgents.length} Active
              </Badge>
            </div>
            
            <div className="space-y-2">
              {agents.map(agent => {
                const Icon = AGENT_ICONS[agent.type];
                const isActive = agent.status !== 'killed';
                
                return (
                  <div 
                    key={agent.id}
                    className={`
                      p-3 rounded-lg border transition-all
                      ${isActive 
                        ? 'bg-[#0d1117] border-gray-700' 
                        : 'bg-gray-900/50 border-gray-800 opacity-50'
                      }
                    `}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Icon className={`w-4 h-4 ${AGENT_COLORS[agent.type]}`} />
                        <span className="text-sm font-medium text-gray-300">
                          {agent.name}
                        </span>
                      </div>
                      <div className="flex items-center gap-1">
                        {agent.status === 'running' && (
                          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                        )}
                        {agent.status === 'paused' && (
                          <div className="w-2 h-2 rounded-full bg-yellow-500" />
                        )}
                        {agent.status === 'killed' && (
                          <div className="w-2 h-2 rounded-full bg-red-500" />
                        )}
                      </div>
                    </div>
                    
                    {agent.currentTask && (
                      <div className="text-xs text-gray-500 mb-2">
                        {agent.currentTask}
                      </div>
                    )}
                    
                    {agent.status === 'running' && (
                      <Progress value={agent.progress} className="h-1 mb-2" />
                    )}
                    
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-500">
                        ${agent.tokenBurn.toFixed(4)}
                      </span>
                      
                      {isActive && (
                        <div className="flex items-center gap-1">
                          {agent.status === 'running' ? (
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              className="h-6 w-6"
                              onClick={() => pauseAgent(agent.id)}
                            >
                              <Pause className="w-3 h-3" />
                            </Button>
                          ) : (
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              className="h-6 w-6"
                              onClick={() => resumeAgent(agent.id)}
                            >
                              <Play className="w-3 h-3" />
                            </Button>
                          )}
                          <Button 
                            variant="ghost" 
                            size="icon" 
                            className="h-6 w-6 hover:bg-red-900/50 hover:text-red-400"
                            onClick={() => handleKillAgent(agent.id, agent.name)}
                          >
                            <Skull className="w-3 h-3" />
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
            
            {/* Token Burn Rate */}
            <div className="mt-3 p-3 bg-[#0d1117] rounded-lg border border-gray-700">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">Token Burn</span>
                <span className="text-cyan-400 font-mono">
                  ${totalTokenBurn.toFixed(4)}/sec
                </span>
              </div>
            </div>
          </div>

          {/* Security Dashboard */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
                <Shield className="w-4 h-4 text-green-400" />
                Security Gates
              </h3>
              <Badge 
                variant="outline" 
                className="text-xs bg-green-900/30 text-green-400 border-green-700"
              >
                Secure
              </Badge>
            </div>
            
            <div className="grid grid-cols-2 gap-2">
              {securityGates.map(gate => (
                <div 
                  key={gate.id}
                  className={`
                    p-2 rounded border text-center
                    ${gate.status === 'secure' 
                      ? 'bg-green-900/20 border-green-800' 
                      : gate.status === 'warning'
                      ? 'bg-yellow-900/20 border-yellow-800'
                      : 'bg-red-900/20 border-red-800'
                    }
                  `}
                >
                  <div className="flex items-center justify-center gap-1 mb-1">
                    {gate.status === 'secure' ? (
                      <CheckCircle className="w-3 h-3 text-green-400" />
                    ) : gate.status === 'warning' ? (
                      <AlertTriangle className="w-3 h-3 text-yellow-400" />
                    ) : (
                      <XCircle className="w-3 h-3 text-red-400" />
                    )}
                  </div>
                  <div className="text-xs text-gray-400">{gate.name}</div>
                  {gate.threatCount > 0 && (
                    <div className="text-xs text-red-400 mt-1">
                      {gate.threatCount} threats
                    </div>
                  )}
                </div>
              ))}
            </div>
            
            {/* Threat Counter */}
            <div className="mt-3 p-3 bg-[#0d1117] rounded-lg border border-gray-700">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">Threats Blocked</span>
                <span className="text-green-400 font-mono">
                  {securityGates.reduce((sum, g) => sum + g.threatCount, 0)}
                </span>
              </div>
            </div>
          </div>

          {/* System Metrics */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
                <Cpu className="w-4 h-4 text-purple-400" />
                System Metrics
              </h3>
            </div>
            
            <div className="space-y-3">
              {/* CPU */}
              <div>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-gray-500">CPU</span>
                  <span className="text-gray-300">{cpuUsage}%</span>
                </div>
                <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all"
                    style={{ width: `${cpuUsage}%` }}
                  />
                </div>
              </div>
              
              {/* GPU */}
              <div>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-gray-500">GPU</span>
                  <span className="text-gray-300">{gpuUsage}%</span>
                </div>
                <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all"
                    style={{ width: `${gpuUsage}%` }}
                  />
                </div>
              </div>
              
              {/* Memory */}
              <div>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-gray-500">Memory</span>
                  <span className="text-gray-300">{memoryUsage}%</span>
                </div>
                <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-green-500 to-emerald-500 transition-all"
                    style={{ width: `${memoryUsage}%` }}
                  />
                </div>
              </div>
              
              {/* Network Latency */}
              <div className="flex items-center justify-between p-2 bg-[#0d1117] rounded border border-gray-700">
                <div className="flex items-center gap-2">
                  <Wifi className="w-4 h-4 text-gray-500" />
                  <span className="text-xs text-gray-500">Latency</span>
                </div>
                <span className="text-sm text-gray-300">{networkLatency}ms</span>
              </div>
              
              {/* Token Cost */}
              <div className="flex items-center justify-between p-2 bg-[#0d1117] rounded border border-gray-700">
                <div className="flex items-center gap-2">
                  <DollarSign className="w-4 h-4 text-gray-500" />
                  <span className="text-xs text-gray-500">Session Cost</span>
                </div>
                <span className="text-sm text-cyan-400">${tokenCost.toFixed(4)}</span>
              </div>
            </div>
          </div>

          {/* Audit Log */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-gray-400" />
                Audit Log
              </h3>
            </div>
            
            <div className="bg-[#0d1117] rounded-lg border border-gray-700 p-2 max-h-40 overflow-y-auto font-mono text-xs">
              {auditLog.map((entry, i) => (
                <div key={i} className="text-gray-500 py-0.5">
                  {entry}
                </div>
              ))}
            </div>
          </div>

        </div>
      </ScrollArea>
    </div>
  );
}
