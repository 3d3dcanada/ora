/**
 * PulZ - Omniscient Agent Operating System
 * Main Application Component
 * MIT Licensed - Based on OpenClaw Foundation
 */

import { useState, useEffect } from 'react';
import { 
  ResizableHandle, 
  ResizablePanel, 
  ResizablePanelGroup 
} from '@/components/ui/resizable';
import { Toaster } from '@/components/ui/sonner';
import { toast } from 'sonner';

// Layout Components
import { LeftSidebar } from '@/components/layout/LeftSidebar';
import { RightSidebar } from '@/components/layout/RightSidebar';
import { TabBar } from '@/components/layout/TabBar';

// Tab Content Components
import { ChatTab } from '@/tabs/ChatTab';
import { WorkflowTab } from '@/tabs/WorkflowTab';
import { EditorTab } from '@/tabs/EditorTab';
import { BrowserTab } from '@/tabs/BrowserTab';

// Store
import { usePulzStore } from '@/store/pulzStore';

// Types
export type TabType = 'chat' | 'workflow' | 'editor' | 'browser';

function App() {
  const [activeTab, setActiveTab] = useState<TabType>('chat');
  const [isLoading, setIsLoading] = useState(true);
  
  const { 
    initialize, 
    checkVaultStatus 
  } = usePulzStore();

  useEffect(() => {
    // Initialize PulZ system
    const init = async () => {
      try {
        await initialize();
        await checkVaultStatus();
        setIsLoading(false);
        toast.success('PulZ System Initialized', {
          description: 'All services are online and ready'
        });
      } catch (error) {
        console.error('Initialization error:', error);
        toast.error('Initialization Failed', {
          description: 'Some services may be unavailable'
        });
        setIsLoading(false);
      }
    };

    init();
  }, []);

  // Render active tab content
  const renderTabContent = () => {
    switch (activeTab) {
      case 'chat':
        return <ChatTab />;
      case 'workflow':
        return <WorkflowTab />;
      case 'editor':
        return <EditorTab />;
      case 'browser':
        return <BrowserTab />;
      default:
        return <ChatTab />;
    }
  };

  if (isLoading) {
    return (
      <div className="h-screen w-full bg-[#0d1117] flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white mb-2">PulZ</h1>
          <p className="text-gray-400">Initializing Omniscient Agent OS...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-full bg-[#0d1117] text-gray-100 overflow-hidden">
      <ResizablePanelGroup className="h-full">
        {/* Left Panel: Tool Palette & Navigation */}
        <ResizablePanel defaultSize={20} minSize={15} maxSize={30}>
          <LeftSidebar />
        </ResizablePanel>
        
        <ResizableHandle withHandle className="bg-gray-800 hover:bg-cyan-600 transition-colors" />
        
        {/* Center Panel: Dynamic Content */}
        <ResizablePanel defaultSize={60}>
          <div className="flex flex-col h-full">
            <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
            <main className="flex-1 overflow-hidden">
              {renderTabContent()}
            </main>
          </div>
        </ResizablePanel>
        
        <ResizableHandle withHandle className="bg-gray-800 hover:bg-cyan-600 transition-colors" />
        
        {/* Right Panel: Metrics & Agent Status */}
        <ResizablePanel defaultSize={20} minSize={15} maxSize={30}>
          <RightSidebar />
        </ResizablePanel>
      </ResizablePanelGroup>
      
      <Toaster position="top-right" richColors />
    </div>
  );
}

export default App;
