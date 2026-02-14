/**
 * PulZ Editor Tab
 * Monaco Editor integration with file tree and git status
 */

import { useState } from 'react';
import Editor from '@monaco-editor/react';
import { 
  FileCode, Folder, FolderOpen, GitBranch, 
  Circle, ChevronRight, ChevronDown, Search,
  Settings, Play, Terminal
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface FileNode {
  name: string;
  type: 'file' | 'directory';
  path: string;
  children?: FileNode[];
  isOpen?: boolean;
  gitStatus?: 'modified' | 'added' | 'untracked' | 'committed';
}

// Mock file tree
const MOCK_FILE_TREE: FileNode[] = [
  {
    name: 'src',
    type: 'directory',
    path: 'src',
    isOpen: true,
    children: [
      {
        name: 'components',
        type: 'directory',
        path: 'src/components',
        children: [
          { name: 'layout', type: 'directory', path: 'src/components/layout', children: [] },
          { name: 'ui', type: 'directory', path: 'src/components/ui', children: [] },
        ]
      },
      { name: 'App.tsx', type: 'file', path: 'src/App.tsx', gitStatus: 'modified' },
      { name: 'main.tsx', type: 'file', path: 'src/main.tsx', gitStatus: 'committed' },
      { name: 'index.css', type: 'file', path: 'src/index.css', gitStatus: 'committed' },
    ]
  },
  {
    name: 'services',
    type: 'directory',
    path: 'services',
    children: [
      { name: 'quantum_layer', type: 'directory', path: 'services/quantum_layer', children: [] },
      { name: 'agent_swarm', type: 'directory', path: 'services/agent_swarm', children: [] },
    ]
  },
  { name: 'package.json', type: 'file', path: 'package.json', gitStatus: 'modified' },
  { name: 'tsconfig.json', type: 'file', path: 'tsconfig.json', gitStatus: 'committed' },
  { name: 'README.md', type: 'file', path: 'README.md', gitStatus: 'untracked' },
];

// Mock code content
const MOCK_CODE = `/**
 * PulZ - Omniscient Agent Operating System
 * Main Application Component
 */

import { useState, useEffect } from 'react';
import { 
  ResizableHandle, 
  ResizablePanel, 
  ResizablePanelGroup 
} from '@/components/ui/resizable';

// Layout Components
import { LeftSidebar } from '@/components/layout/LeftSidebar';
import { RightSidebar } from '@/components/layout/RightSidebar';

export type TabType = 'chat' | 'workflow' | 'editor' | 'browser';

function App() {
  const [activeTab, setActiveTab] = useState<TabType>('chat');
  
  return (
    <div className="h-screen w-full bg-[#0d1117]">
      <ResizablePanelGroup direction="horizontal">
        <ResizablePanel defaultSize={20}>
          <LeftSidebar />
        </ResizablePanel>
        
        <ResizableHandle />
        
        <ResizablePanel defaultSize={60}>
          {/* Main content */}
        </ResizablePanel>
        
        <ResizableHandle />
        
        <ResizablePanel defaultSize={20}>
          <RightSidebar />
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}

export default App;
`;

export function EditorTab() {
  const [fileTree, setFileTree] = useState<FileNode[]>(MOCK_FILE_TREE);
  const [selectedFile, setSelectedFile] = useState<string>('src/App.tsx');
  const [code, setCode] = useState(MOCK_CODE);
  const [showTerminal, setShowTerminal] = useState(false);

  const toggleDirectory = (path: string) => {
    const toggleNode = (nodes: FileNode[]): FileNode[] => {
      return nodes.map(node => {
        if (node.path === path) {
          return { ...node, isOpen: !node.isOpen };
        }
        if (node.children) {
          return { ...node, children: toggleNode(node.children) };
        }
        return node;
      });
    };
    setFileTree(toggleNode(fileTree));
  };

  const renderFileTree = (nodes: FileNode[], depth = 0) => {
    return nodes.map(node => (
      <div key={node.path}>
        <button
          onClick={() => {
            if (node.type === 'directory') {
              toggleDirectory(node.path);
            } else {
              setSelectedFile(node.path);
            }
          }}
          className={cn(
            'w-full flex items-center gap-1 px-2 py-1 text-sm hover:bg-gray-800 transition-colors',
            selectedFile === node.path && 'bg-cyan-900/30 text-cyan-400',
            depth > 0 && 'ml-4'
          )}
        >
          {node.type === 'directory' ? (
            node.isOpen ? (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-500" />
            )
          ) : (
            <span className="w-4" />
          )}
          
          {node.type === 'directory' ? (
            node.isOpen ? (
              <FolderOpen className="w-4 h-4 text-blue-400" />
            ) : (
              <Folder className="w-4 h-4 text-blue-400" />
            )
          ) : (
            <FileCode className="w-4 h-4 text-yellow-400" />
          )}
          
          <span className={cn(
            'flex-1 text-left truncate',
            node.type === 'directory' ? 'text-gray-300' : 'text-gray-400'
          )}>
            {node.name}
          </span>
          
          {node.gitStatus && (
            <GitStatusIndicator status={node.gitStatus} />
          )}
        </button>
        
        {node.type === 'directory' && node.isOpen && node.children && (
          <div>{renderFileTree(node.children, depth + 1)}</div>
        )}
      </div>
    ));
  };

  return (
    <div className="h-full flex flex-col bg-[#0d1117]">
      {/* Toolbar */}
      <div className="h-10 bg-[#161b22] border-b border-gray-800 flex items-center justify-between px-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-gray-500" />
            <span className="text-sm text-gray-400">main</span>
            <Badge variant="outline" className="text-xs bg-yellow-900/30 text-yellow-400 border-yellow-700">
              2 changes
            </Badge>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <Search className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <Settings className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setShowTerminal(!showTerminal)}>
            <Terminal className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="sm" className="h-8">
            <Play className="w-4 h-4 mr-1" />
            Run
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* File Tree */}
        <div className="w-64 bg-[#161b22] border-r border-gray-800 flex flex-col">
          <div className="p-2 text-xs text-gray-500 uppercase tracking-wider">
            Explorer
          </div>
          <ScrollArea className="flex-1">
            {renderFileTree(fileTree)}
          </ScrollArea>
        </div>

        {/* Editor */}
        <div className="flex-1 flex flex-col">
          <div className="flex-1">
            <Editor
              height="100%"
              defaultLanguage="typescript"
              theme="vs-dark"
              value={code}
              onChange={(value) => setCode(value || '')}
              options={{
                minimap: { enabled: true },
                fontSize: 14,
                lineNumbers: 'on',
                roundedSelection: false,
                scrollBeyondLastLine: false,
                readOnly: false,
                automaticLayout: true,
                padding: { top: 16 },
              }}
            />
          </div>
          
          {/* Terminal Panel */}
          {showTerminal && (
            <div className="h-48 bg-[#0d1117] border-t border-gray-800 flex flex-col">
              <div className="flex items-center justify-between px-4 py-2 bg-[#161b22] border-b border-gray-800">
                <span className="text-xs text-gray-500">Terminal</span>
                <Button 
                  variant="ghost" 
                  size="icon" 
                  className="h-6 w-6"
                  onClick={() => setShowTerminal(false)}
                >
                  <span className="text-gray-500">×</span>
                </Button>
              </div>
              <div className="flex-1 p-4 font-mono text-sm text-gray-300 overflow-y-auto">
                <div className="text-green-400">user@pulz:~/projects/pulz$</div>
                <div className="mt-2 text-gray-400">
                  PulZ Agent OS v1.0.0 - Omniscient Edition
                </div>
                <div className="text-gray-500">
                  Type 'help' for available commands
                </div>
                <div className="mt-2 flex items-center">
                  <span className="text-green-400">user@pulz:~/projects/pulz$</span>
                  <span className="ml-2 animate-pulse">_</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Status Bar */}
      <div className="h-6 bg-[#007acc] text-white text-xs flex items-center px-4 justify-between">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1">
            <GitBranch className="w-3 h-3" />
            main*
          </span>
          <span>0 errors, 0 warnings</span>
        </div>
        <div className="flex items-center gap-4">
          <span>Ln 12, Col 34</span>
          <span>UTF-8</span>
          <span>TypeScript</span>
          <span>PulZ</span>
        </div>
      </div>
    </div>
  );
}

// Git Status Indicator Component
function GitStatusIndicator({ status }: { status: FileNode['gitStatus'] }) {
  const colors = {
    modified: 'text-yellow-400',
    added: 'text-green-400',
    untracked: 'text-gray-500',
    committed: 'text-transparent',
  };

  return (
    <Circle className={cn('w-2 h-2 fill-current', colors[status || 'committed'])} />
  );
}
