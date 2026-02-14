/**
 * PulZ Browser Tab
 * Embedded browser with proxy controls, stealth mode, screenshot + OCR
 */

import { useState, useRef } from 'react';
import { 
  Globe, Shield, Camera, Eye, EyeOff, 
  RefreshCw, Lock, Unlock, AlertTriangle,
  ChevronLeft, ChevronRight, Home
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

// Allowed domains for security
const ALLOWED_DOMAINS = [
  'github.com',
  'stackoverflow.com',
  'docs.python.org',
  'developer.mozilla.org',
  'api.openai.com',
  'api.moonshot.cn',
  'localhost',
  '127.0.0.1',
];

export function BrowserTab() {
  const [url, setUrl] = useState('https://github.com/openclaw');
  const [inputUrl, setInputUrl] = useState('https://github.com/openclaw');
  const [isStealthMode, setIsStealthMode] = useState(false);
  const [isProxyEnabled, setIsProxyEnabled] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [screenshot, setScreenshot] = useState<string | null>(null);
  const [ocrResult, setOcrResult] = useState<string | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const isUrlAllowed = (checkUrl: string): boolean => {
    try {
      const urlObj = new URL(checkUrl);
      return ALLOWED_DOMAINS.some(domain => 
        urlObj.hostname === domain || urlObj.hostname.endsWith(`.${domain}`)
      );
    } catch {
      return false;
    }
  };

  const handleNavigate = () => {
    if (!isUrlAllowed(inputUrl)) {
      toast.error('Domain not in allowlist', {
        description: 'This domain is blocked for security'
      });
      return;
    }
    setIsLoading(true);
    setUrl(inputUrl);
    setTimeout(() => setIsLoading(false), 1000);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleNavigate();
    }
  };

  const handleScreenshot = async () => {
    toast.info('Screenshot captured', {
      description: 'OCR processing...'
    });
    
    // Simulate screenshot and OCR
    setScreenshot('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAwIiBoZWlnaHQ9IjYwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMGQxMTE3Ii8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZpbGw9IiM2YjcyODAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSJtb25vc3BhY2UiPlNjcmVlbnNob3QgUHJldmlldzwvdGV4dD48L3N2Zz4=');
    
    setTimeout(() => {
      setOcrResult('Detected text:\n- OpenClaw Repository\n- MIT License\n- Agent Operating System');
      toast.success('OCR Complete');
    }, 1500);
  };

  const getSecurityStatus = () => {
    if (isStealthMode && isProxyEnabled) return { text: 'Maximum Security', color: 'text-green-400', bg: 'bg-green-900/30' };
    if (isStealthMode || isProxyEnabled) return { text: 'Enhanced Security', color: 'text-yellow-400', bg: 'bg-yellow-900/30' };
    return { text: 'Standard', color: 'text-gray-400', bg: 'bg-gray-800' };
  };

  const security = getSecurityStatus();

  return (
    <div className="h-full flex flex-col bg-[#0d1117]">
      {/* Toolbar */}
      <div className="h-14 bg-[#161b22] border-b border-gray-800 flex items-center gap-2 px-4">
        {/* Navigation */}
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="h-9 w-9">
            <ChevronLeft className="w-5 h-5" />
          </Button>
          <Button variant="ghost" size="icon" className="h-9 w-9">
            <ChevronRight className="w-5 h-5" />
          </Button>
          <Button variant="ghost" size="icon" className="h-9 w-9" onClick={() => setIsLoading(true)}>
            <RefreshCw className={cn('w-5 h-5', isLoading && 'animate-spin')} />
          </Button>
          <Button variant="ghost" size="icon" className="h-9 w-9">
            <Home className="w-5 h-5" />
          </Button>
        </div>

        {/* URL Bar */}
        <div className="flex-1 flex items-center gap-2">
          <div className="relative flex-1">
            <div className="absolute left-3 top-1/2 -translate-y-1/2">
              {isUrlAllowed(inputUrl) ? (
                <Lock className="w-4 h-4 text-green-400" />
              ) : (
                <Unlock className="w-4 h-4 text-red-400" />
              )}
            </div>
            <Input
              value={inputUrl}
              onChange={(e) => setInputUrl(e.target.value)}
              onKeyDown={handleKeyDown}
              className="pl-10 pr-4 bg-[#0d1117] border-gray-700"
              placeholder="Enter URL..."
            />
          </div>
          <Button onClick={handleNavigate} className="bg-cyan-600 hover:bg-cyan-700">
            <Globe className="w-4 h-4 mr-2" />
            Go
          </Button>
        </div>

        {/* Security Controls */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Eye className="w-4 h-4 text-gray-500" />
            <Switch
              checked={isStealthMode}
              onCheckedChange={setIsStealthMode}
            />
            <EyeOff className={cn('w-4 h-4', isStealthMode ? 'text-cyan-400' : 'text-gray-500')} />
            <span className="text-xs text-gray-500">Stealth</span>
          </div>

          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-gray-500" />
            <Switch
              checked={isProxyEnabled}
              onCheckedChange={setIsProxyEnabled}
            />
            <span className="text-xs text-gray-500">Proxy</span>
          </div>

          <Button variant="ghost" size="icon" onClick={handleScreenshot}>
            <Camera className="w-5 h-5" />
          </Button>
        </div>
      </div>

      {/* Security Status Bar */}
      <div className="h-8 bg-[#0d1117] border-b border-gray-800 flex items-center justify-between px-4">
        <div className="flex items-center gap-4">
          <Badge className={cn('text-xs', security.bg, security.color, 'border-0')}>
            <Shield className="w-3 h-3 mr-1" />
            {security.text}
          </Badge>
          
          {isStealthMode && (
            <span className="text-xs text-cyan-400 flex items-center gap-1">
              <EyeOff className="w-3 h-3" />
              Playwright Stealth Active
            </span>
          )}
          
          {isProxyEnabled && (
            <span className="text-xs text-purple-400 flex items-center gap-1">
              <Globe className="w-3 h-3" />
              Proxy Routing
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Allowlist:</span>
          <div className="flex items-center gap-1">
            {ALLOWED_DOMAINS.slice(0, 3).map(domain => (
              <Badge key={domain} variant="outline" className="text-xs">
                {domain}
              </Badge>
            ))}
            <Badge variant="outline" className="text-xs">
              +{ALLOWED_DOMAINS.length - 3} more
            </Badge>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Browser View */}
        <div className="flex-1 bg-white">
          <iframe
            ref={iframeRef}
            src={url}
            className="w-full h-full border-0"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
            title="PulZ Browser"
          />
        </div>

        {/* Screenshot & OCR Panel */}
        {(screenshot || ocrResult) && (
          <div className="w-80 bg-[#161b22] border-l border-gray-800 flex flex-col">
            <div className="p-3 border-b border-gray-800 flex items-center justify-between">
              <span className="text-sm font-medium text-gray-300">Screenshot & OCR</span>
              <Button 
                variant="ghost" 
                size="icon" 
                className="h-6 w-6"
                onClick={() => { setScreenshot(null); setOcrResult(null); }}
              >
                <span className="text-gray-500">×</span>
              </Button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {screenshot && (
                <div>
                  <div className="text-xs text-gray-500 mb-2">Screenshot</div>
                  <img 
                    src={screenshot} 
                    alt="Screenshot" 
                    className="w-full rounded border border-gray-700"
                  />
                </div>
              )}
              
              {ocrResult && (
                <div>
                  <div className="text-xs text-gray-500 mb-2">OCR Result</div>
                  <div className="bg-[#0d1117] p-3 rounded border border-gray-700">
                    <pre className="text-xs text-gray-300 whitespace-pre-wrap">
                      {ocrResult}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Warning for blocked domains */}
      {!isUrlAllowed(inputUrl) && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-red-900/90 text-red-100 px-4 py-2 rounded-lg flex items-center gap-2">
          <AlertTriangle className="w-5 h-5" />
          <span>This domain is not in the allowlist</span>
        </div>
      )}
    </div>
  );
}
