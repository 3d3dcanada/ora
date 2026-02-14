/**
 * PulZ Chat Tab
 * Discord-like interface with message bubbles, tool execution cards
 * Connected to backend via WebSocket for real AI responses
 */

import { useState, useRef, useEffect } from 'react';
import { 
  Send, Mic, MicOff, Bot, User, Terminal, 
  CheckCircle, XCircle, Loader2, Wifi, WifiOff
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

// API configuration
const API_BASE_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  toolCalls?: ToolCall[];
  citations?: Citation[];
  confidence?: number;
}

interface Citation {
  file: string;
  lines: string;
  relevance: number;
}

interface ToolCall {
  id: string;
  tool: string;
  command: string;
  stdout?: string;
  stderr?: string;
  exitCode: number;
  status: 'running' | 'success' | 'error';
  executionTime: number;
}

export function ChatTab() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'system',
      content: 'Welcome to PulZ - Omniscient Agent OS. How can I assist you today?',
      timestamp: Date.now(),
    }
  ]);
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Connect to WebSocket
  useEffect(() => {
    const connectWebSocket = () => {
      try {
        const ws = new WebSocket(WS_URL);
        
        ws.onopen = () => {
          console.log('WebSocket connected');
          setIsConnected(true);
        };
        
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
          } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
          }
        };
        
        ws.onclose = () => {
          console.log('WebSocket disconnected');
          setIsConnected(false);
          // Attempt to reconnect after 3 seconds
          setTimeout(connectWebSocket, 3000);
        };
        
        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          setIsConnected(false);
        };
        
        wsRef.current = ws;
      } catch (error) {
        console.error('Failed to connect WebSocket:', error);
        setIsConnected(false);
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Handle incoming WebSocket messages
  const handleWebSocketMessage = (data: any) => {
    if (data.type === 'chat_response') {
      // Add assistant message from backend
      const assistantMessage: Message = {
        id: `assistant_${Date.now()}`,
        role: 'assistant',
        content: data.message || 'No response',
        timestamp: Date.now(),
        confidence: 0.8,
      };
      
      setMessages(prev => [...prev, assistantMessage]);
      setIsStreaming(false);
    } else if (data.type === 'connected') {
      console.log('Connected to backend, client_id:', data.client_id);
    }
  };

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    const userMessage: Message = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: input,
      timestamp: Date.now(),
    };

    setMessages(prev => [...prev, userMessage]);
    const messageText = input;
    setInput('');
    setIsStreaming(true);

    // Try WebSocket first, then fallback to REST API
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      // Send via WebSocket
      wsRef.current.send(JSON.stringify({
        type: 'chat',
        message: messageText,
        user: 'Randall'
      }));
    } else {
      // Fallback to REST API
      try {
        const response = await fetch(`${API_BASE_URL}/kernel/process`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            command: messageText,
            user: 'Randall'
          }),
        });
        
        const data = await response.json();
        
        // Add assistant message from API response
        const assistantMessage: Message = {
          id: `assistant_${Date.now()}`,
          role: 'assistant',
          content: data.output || 'No response',
          timestamp: Date.now(),
          confidence: 0.8,
        };
        
        setMessages(prev => [...prev, assistantMessage]);
      } catch (error) {
        console.error('API call failed:', error);
        const errorMessage: Message = {
          id: `error_${Date.now()}`,
          role: 'assistant',
          content: 'Failed to connect to backend. Please check if the server is running on port 8000.',
          timestamp: Date.now(),
        };
        setMessages(prev => [...prev, errorMessage]);
      }
      
      setIsStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleRecording = () => {
    setIsRecording(!isRecording);
    // In a real implementation, this would use Web Speech API
  };

  return (
    <div className="h-full flex flex-col bg-[#0d1117]">
      {/* Connection Status */}
      <div className="px-4 py-2 border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">Status:</span>
          {isConnected ? (
            <div className="flex items-center gap-1 text-green-400">
              <Wifi className="w-4 h-4" />
              <span className="text-xs">Connected</span>
            </div>
          ) : (
            <div className="flex items-center gap-1 text-red-400">
              <WifiOff className="w-4 h-4" />
              <span className="text-xs">Disconnected</span>
            </div>
          )}
        </div>
        <span className="text-xs text-gray-500">Backend: {API_BASE_URL}</span>
      </div>

      {/* Messages Area */}
      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        <div className="space-y-4">
          {messages.map(message => (
            <MessageBubble 
              key={message.id} 
              message={message} 
              isStreaming={isStreaming && message.role === 'assistant' && !message.content}
            />
          ))}
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div className="p-4 border-t border-gray-800 bg-[#161b22]">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            className={cn(
              'shrink-0',
              isRecording && 'text-red-400 animate-pulse'
            )}
            onClick={toggleRecording}
          >
            {isRecording ? <Mic className="w-5 h-5" /> : <MicOff className="w-5 h-5" />}
          </Button>
          
          <div className="flex-1 relative">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message or use / for commands..."
              className="bg-[#0d1117] border-gray-700 pr-12"
              disabled={isStreaming}
            />
            {isStreaming && (
              <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 animate-spin text-cyan-400" />
            )}
          </div>
          
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className="shrink-0 bg-cyan-600 hover:bg-cyan-700"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
        
        <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
          <span>Press Enter to send</span>
          <span>•</span>
          <span>Shift+Enter for new line</span>
          <span>•</span>
          <span>Type / for commands</span>
        </div>
      </div>
    </div>
  );
}

// Message Bubble Component
function MessageBubble({ 
  message, 
  isStreaming 
}: { 
  message: Message; 
  isStreaming?: boolean;
}) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  return (
    <div className={cn(
      'flex gap-3',
      isUser && 'flex-row-reverse'
    )}>
      {/* Avatar */}
      <div className={cn(
        'w-8 h-8 rounded-full flex items-center justify-center shrink-0',
        isUser ? 'bg-cyan-600' : isSystem ? 'bg-gray-700' : 'bg-purple-600'
      )}>
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : isSystem ? (
          <Bot className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-white" />
        )}
      </div>

      {/* Content */}
      <div className={cn(
        'max-w-[80%]',
        isUser && 'text-right'
      )}>
        <div className={cn(
          'inline-block px-4 py-2 rounded-2xl text-left',
          isUser 
            ? 'bg-cyan-600 text-white rounded-br-md' 
            : isSystem
            ? 'bg-gray-800 text-gray-300 rounded-bl-md'
            : 'bg-[#161b22] text-gray-100 border border-gray-700 rounded-bl-md'
        )}>
          {message.content}
          {isStreaming && (
            <span className="inline-block w-2 h-4 bg-cyan-400 ml-1 animate-pulse" />
          )}
        </div>

        {/* Citations Display */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-2 p-2 bg-gray-800/50 rounded text-xs">
            <div className="text-gray-400 mb-1">Sources:</div>
            {message.citations.map((cit, idx) => (
              <div key={idx} className="text-cyan-400">
                {cit.file}:{cit.lines} (relevance: {cit.relevance})
              </div>
            ))}
          </div>
        )}

        {/* Confidence Display */}
        {message.confidence !== undefined && (
          <div className="mt-1 flex items-center gap-2">
            <span className="text-xs text-gray-500">Confidence:</span>
            <Badge variant="outline" className={cn(
              'text-xs',
              message.confidence >= 0.8 ? 'text-green-400 border-green-400' :
              message.confidence >= 0.5 ? 'text-yellow-400 border-yellow-400' :
              'text-red-400 border-red-400'
            )}>
              {(message.confidence * 100).toFixed(0)}%
            </Badge>
          </div>
        )}

        {/* Tool Calls */}
        {message.toolCalls && message.toolCalls.map(toolCall => (
          <ToolCallCard key={toolCall.id} toolCall={toolCall} />
        ))}

        {/* Timestamp */}
        <div className="text-xs text-gray-500 mt-1">
          {new Date(message.timestamp).toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}

// Tool Call Card Component
function ToolCallCard({ toolCall }: { toolCall: ToolCall }) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="mt-2 bg-[#0d1117] border border-gray-700 rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-gray-800/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-gray-400" />
          <span className="text-sm font-medium text-gray-300">{toolCall.tool}</span>
          <code className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded">
            {toolCall.command}
          </code>
        </div>
        <div className="flex items-center gap-2">
          {toolCall.status === 'running' ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-yellow-400" />
              <span className="text-xs text-yellow-400">Running...</span>
            </>
          ) : toolCall.status === 'success' ? (
            <>
              <CheckCircle className="w-4 h-4 text-green-400" />
              <span className="text-xs text-green-400">{toolCall.executionTime}ms</span>
            </>
          ) : (
            <>
              <XCircle className="w-4 h-4 text-red-400" />
              <span className="text-xs text-red-400">Error</span>
            </>
          )}
        </div>
      </button>

      {/* Output */}
      {isExpanded && (
        <div className="border-t border-gray-800">
          {toolCall.stdout && (
            <div className="p-3">
              <div className="text-xs text-gray-500 mb-1">stdout</div>
              <pre className="text-xs text-gray-300 bg-gray-900 p-2 rounded overflow-x-auto">
                {toolCall.stdout}
              </pre>
            </div>
          )}
          {toolCall.stderr && (
            <div className="p-3">
              <div className="text-xs text-red-500 mb-1">stderr</div>
              <pre className="text-xs text-red-300 bg-red-900/20 p-2 rounded overflow-x-auto">
                {toolCall.stderr}
              </pre>
            </div>
          )}
          <div className="px-3 pb-3">
            <Badge variant="outline" className="text-xs">
              Exit Code: {toolCall.exitCode}
            </Badge>
          </div>
        </div>
      )}
    </div>
  );
}
