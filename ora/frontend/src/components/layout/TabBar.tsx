/**
 * PulZ Tab Bar
 * Draggable tabs for switching between Chat, Workflow, Editor, Browser
 */

import { MessageSquare, GitBranch, Code, Globe } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { TabType } from '@/App';

interface TabBarProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
}

interface Tab {
  id: TabType;
  label: string;
  icon: React.ElementType;
}

const TABS: Tab[] = [
  { id: 'chat', label: 'Chat', icon: MessageSquare },
  { id: 'workflow', label: 'Workflow', icon: GitBranch },
  { id: 'editor', label: 'Editor', icon: Code },
  { id: 'browser', label: 'Browser', icon: Globe },
];

export function TabBar({ activeTab, onTabChange }: TabBarProps) {
  return (
    <div className="h-12 bg-[#0d1117] border-b border-gray-800 flex items-center px-2">
      <div className="flex items-center gap-1">
        {TABS.map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-t-lg text-sm font-medium transition-all',
                'hover:bg-gray-800/50',
                isActive 
                  ? 'bg-[#161b22] text-cyan-400 border-t-2 border-cyan-400' 
                  : 'text-gray-500'
              )}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>
      
      <div className="flex-1" />
      
      {/* Quick Actions */}
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
        <span className="text-xs text-gray-500">System Online</span>
      </div>
    </div>
  );
}
