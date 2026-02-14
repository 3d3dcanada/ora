/**
 * PulZ Workflow Tab
 * ReactFlow canvas for n8n-style workflow building
 */

import { useState, useCallback } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  type Node,
  type Edge,
  type Connection,
  type NodeTypes,
  Panel,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { 
  Play, Pause, Square, Save, Upload, Download,
  Bot, Wrench, GitBranch, Merge, Plus
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { usePulzStore } from '@/store/pulzStore';

// Custom Node Components
function AgentNode({ data }: { data: any }) {
  return (
    <div className="px-4 py-3 bg-gradient-to-br from-cyan-900/50 to-blue-900/50 border-2 border-cyan-500 rounded-lg min-w-[180px]">
      <div className="flex items-center gap-2 mb-2">
        <Bot className="w-5 h-5 text-cyan-400" />
        <span className="font-semibold text-cyan-100">{data.label}</span>
      </div>
      <div className="text-xs text-cyan-300/70">{data.agentType}</div>
      {data.task && (
        <div className="mt-2 text-xs text-gray-400 bg-black/30 p-2 rounded">
          {data.task}
        </div>
      )}
    </div>
  );
}

function ToolNode({ data }: { data: any }) {
  return (
    <div className="px-4 py-3 bg-gradient-to-br from-purple-900/50 to-pink-900/50 border-2 border-purple-500 rounded-lg min-w-[160px]">
      <div className="flex items-center gap-2 mb-2">
        <Wrench className="w-5 h-5 text-purple-400" />
        <span className="font-semibold text-purple-100">{data.label}</span>
      </div>
      <div className="text-xs text-purple-300/70">{data.toolId}</div>
    </div>
  );
}

function ConditionNode({ data }: { data: any }) {
  return (
    <div className="px-4 py-3 bg-gradient-to-br from-yellow-900/50 to-orange-900/50 border-2 border-yellow-500 rounded-lg transform rotate-45 min-w-[120px] min-h-[120px] flex items-center justify-center">
      <div className="transform -rotate-45 text-center">
        <GitBranch className="w-5 h-5 text-yellow-400 mx-auto mb-1" />
        <span className="font-semibold text-yellow-100 text-sm">{data.label}</span>
      </div>
    </div>
  );
}

function MergeNode({ data }: { data: any }) {
  return (
    <div className="px-4 py-3 bg-gradient-to-br from-green-900/50 to-emerald-900/50 border-2 border-green-500 rounded-full min-w-[140px]">
      <div className="flex items-center gap-2 justify-center">
        <Merge className="w-5 h-5 text-green-400" />
        <span className="font-semibold text-green-100">{data.label}</span>
      </div>
    </div>
  );
}

const nodeTypes: NodeTypes = {
  agent: AgentNode,
  tool: ToolNode,
  condition: ConditionNode,
  merge: MergeNode,
};

// Initial nodes and edges
const initialNodes: Node[] = [
  {
    id: '1',
    type: 'agent',
    position: { x: 100, y: 100 },
    data: { label: 'CodeArchitect', agentType: 'architect', task: 'Design system architecture' },
  },
  {
    id: '2',
    type: 'tool',
    position: { x: 400, y: 100 },
    data: { label: 'File System', toolId: 'fs_write' },
  },
  {
    id: '3',
    type: 'condition',
    position: { x: 650, y: 150 },
    data: { label: 'Tests Pass?' },
  },
  {
    id: '4',
    type: 'agent',
    position: { x: 900, y: 50 },
    data: { label: 'SecurityAuditor', agentType: 'auditor', task: 'Security review' },
  },
  {
    id: '5',
    type: 'merge',
    position: { x: 900, y: 250 },
    data: { label: 'Consensus' },
  },
];

const initialEdges: Edge[] = [
  { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#06b6d4' } },
  { id: 'e2-3', source: '2', target: '3', animated: true, style: { stroke: '#a855f7' } },
  { id: 'e3-4', source: '3', target: '4', label: 'Yes', animated: true, style: { stroke: '#22c55e' } },
  { id: 'e3-5', source: '3', target: '5', label: 'No', animated: true, style: { stroke: '#ef4444' } },
];

export function WorkflowTab() {
  const [nodes, setNodes] = useState<Node[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionProgress, setExecutionProgress] = useState(0);
  
  const { tools, agents } = usePulzStore();

  const onNodesChange = useCallback(
    (changes: any) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );

  const onEdgesChange = useCallback(
    (changes: any) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  const onConnect = useCallback(
    (connection: Connection) => setEdges((eds) => addEdge(connection, eds)),
    []
  );

  const handleExecute = async () => {
    if (isExecuting) return;
    
    setIsExecuting(true);
    setExecutionProgress(0);
    
    toast.info('Workflow Execution Started', {
      description: 'Running agent swarm with DCBFT consensus'
    });

    // Simulate execution
    for (let i = 0; i <= 100; i += 10) {
      await new Promise(resolve => setTimeout(resolve, 300));
      setExecutionProgress(i);
    }

    setIsExecuting(false);
    toast.success('Workflow Completed', {
      description: 'All agents reached consensus'
    });
  };

  const handleStop = () => {
    setIsExecuting(false);
    setExecutionProgress(0);
    toast.warning('Workflow Stopped', {
      description: 'Execution halted by user'
    });
  };

  const addNode = (type: string) => {
    const newNode: Node = {
      id: `${Date.now()}`,
      type,
      position: { x: Math.random() * 400 + 100, y: Math.random() * 300 + 100 },
      data: { 
        label: type === 'agent' ? 'New Agent' : type === 'tool' ? 'New Tool' : 'New Node',
        ...(type === 'agent' && { agentType: 'executor' }),
        ...(type === 'tool' && { toolId: 'fs_read' }),
      },
    };
    setNodes(prev => [...prev, newNode]);
  };

  return (
    <div className="h-full flex flex-col bg-[#0d1117]">
      {/* Toolbar */}
      <div className="h-14 bg-[#161b22] border-b border-gray-800 flex items-center justify-between px-4">
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="bg-cyan-900/30 text-cyan-400 border-cyan-700">
            Workflow Builder
          </Badge>
          
          <div className="h-6 w-px bg-gray-700 mx-2" />
          
          <Button variant="ghost" size="sm" onClick={() => addNode('agent')}>
            <Plus className="w-4 h-4 mr-1" />
            Agent
          </Button>
          <Button variant="ghost" size="sm" onClick={() => addNode('tool')}>
            <Plus className="w-4 h-4 mr-1" />
            Tool
          </Button>
          <Button variant="ghost" size="sm" onClick={() => addNode('condition')}>
            <Plus className="w-4 h-4 mr-1" />
            Condition
          </Button>
        </div>

        <div className="flex items-center gap-2">
          {isExecuting && (
            <div className="flex items-center gap-2 mr-4">
              <div className="w-32 h-2 bg-gray-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all"
                  style={{ width: `${executionProgress}%` }}
                />
              </div>
              <span className="text-xs text-gray-500">{executionProgress}%</span>
            </div>
          )}
          
          <Button
            variant="ghost"
            size="icon"
            onClick={handleExecute}
            disabled={isExecuting}
            className={isExecuting ? 'text-yellow-400' : 'text-green-400'}
          >
            {isExecuting ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
          </Button>
          
          <Button
            variant="ghost"
            size="icon"
            onClick={handleStop}
            disabled={!isExecuting}
            className="text-red-400"
          >
            <Square className="w-5 h-5" />
          </Button>
          
          <div className="h-6 w-px bg-gray-700 mx-2" />
          
          <Button variant="ghost" size="icon">
            <Save className="w-5 h-5" />
          </Button>
          <Button variant="ghost" size="icon">
            <Upload className="w-5 h-5" />
          </Button>
          <Button variant="ghost" size="icon">
            <Download className="w-5 h-5" />
          </Button>
        </div>
      </div>

      {/* ReactFlow Canvas */}
      <div className="flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          fitView
          className="bg-[#0d1117]"
        >
          <Background color="#374151" gap={20} size={1} />
          <Controls className="bg-[#161b22] border-gray-700" />
          <MiniMap 
            className="bg-[#161b22] border-gray-700"
            nodeColor={(node) => {
              if (node.type === 'agent') return '#06b6d4';
              if (node.type === 'tool') return '#a855f7';
              if (node.type === 'condition') return '#eab308';
              if (node.type === 'merge') return '#22c55e';
              return '#6b7280';
            }}
          />
          
          <Panel position="top-left" className="bg-[#161b22] p-3 rounded-lg border border-gray-700">
            <div className="text-xs text-gray-500 mb-2">Available Tools</div>
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {tools.slice(0, 8).map(tool => (
                <div 
                  key={tool.id}
                  className="text-xs text-gray-400 hover:text-cyan-400 cursor-pointer truncate"
                >
                  {tool.name}
                </div>
              ))}
            </div>
          </Panel>
          
          <Panel position="bottom-left" className="bg-[#161b22] p-3 rounded-lg border border-gray-700">
            <div className="text-xs text-gray-500 mb-2">Active Agents</div>
            <div className="space-y-1">
              {agents.filter(a => a.status !== 'killed').map(agent => (
                <div key={agent.id} className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500" />
                  <span className="text-xs text-gray-400">{agent.name}</span>
                </div>
              ))}
            </div>
          </Panel>
        </ReactFlow>
      </div>
    </div>
  );
}
