'use client'

import { useState, useEffect } from 'react'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { Button } from "../components/ui/button"
import { Textarea } from "../components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select"
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import { FileText, Trash, Download } from 'lucide-react'

interface HistoryItem {
  timestamp: number
  model: string
  prompt: string
  response: string
  duration: number
}

const BACKEND_URL = 'http://localhost:8083'
const MODELS = {
  chat: 'Deepseek Deepseek V3',
  reasoner: 'Deepseek Deepseek R1',
  groq: 'Groq Deepseek R1',
  perplexity: 'Perplexity Sonar Deepseek R1',
  ollama: 'Ollama Deepseek R1',
  gumtree: 'Gumtree Deepseek R1',
} as const

// Add this mapping for backend model values
const MODEL_VALUES = {
  chat: 'deepseek-chat',
  reasoner: 'deepseek-reasoner',
  groq: 'groq-deepseek-r1',
  perplexity: 'perplexity-sonar',
  ollama: 'ollama-deepseek-r1',
  gumtree: 'gumtree-deepseek-r1',
} as const

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Add this helper function at the top level
const isStorageAvailable = () => {
  try {
    return typeof window !== 'undefined' && 
           typeof window.indexedDB !== 'undefined' && 
           window.isSecureContext;
  } catch {
    return false;
  }
};

export default function Home() {
  const [prompt, setPrompt] = useState('')
  const [output, setOutput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [completionHistory, setCompletionHistory] = useState<HistoryItem[]>([])
  const [selectedModel, setSelectedModel] = useState('chat')
  const [completionTime, setCompletionTime] = useState<number | null>(null)
  const [db, setDb] = useState<IDBDatabase | null>(null)
  const [selectedHistoryId, setSelectedHistoryId] = useState<number | null>(null)
  const [isHistoryView, setIsHistoryView] = useState(false)
  const [deletedItems, setDeletedItems] = useState<HistoryItem[]>([])
  const [lastDeletedTimestamp, setLastDeletedTimestamp] = useState<number | null>(null)
  const [sidebarWidth, setSidebarWidth] = useState(256) // 256px = 16rem = w-64 default
  const [isResizing, setIsResizing] = useState(false)

  // Update the IndexedDB initialization
  useEffect(() => {
    if (!isStorageAvailable()) {
      console.log('Storage not available in this context');
      return;
    }

    const initDB = async () => {
      try {
        const request = indexedDB.open('DeepseekDB', 1);
        
        request.onerror = (event) => {
          console.error('IndexedDB error:', event);
        };

        request.onupgradeneeded = (event) => {
          const db = (event.target as IDBOpenDBRequest).result;
          if (!db.objectStoreNames.contains('history')) {
            db.createObjectStore('history', { keyPath: 'timestamp' });
          }
        };

        request.onsuccess = (event) => {
          const db = (event.target as IDBOpenDBRequest).result;
          setDb(db);
          
          try {
            // Load existing history
            const transaction = db.transaction(['history'], 'readonly');
            const store = transaction.objectStore('history');
            const getAllRequest = store.getAll();
            
            getAllRequest.onsuccess = () => {
              const items = getAllRequest.result as HistoryItem[];
              setCompletionHistory(items.sort((a, b) => b.timestamp - a.timestamp));
            };
          } catch (error) {
            console.error('Error loading history:', error);
          }
        };
      } catch (error) {
        console.error('Failed to initialize IndexedDB:', error);
      }
    };

    initDB();

    return () => {
      if (db) {
        db.close();
      }
    };
  }, []);

  // Also update the saveToHistory function to be more defensive
  const saveToHistory = async (item: HistoryItem) => {
    if (!db || !isStorageAvailable()) {
      console.log('Storage not available, cannot save history');
      return;
    }

    try {
      const transaction = db.transaction(['history'], 'readwrite');
      const store = transaction.objectStore('history');
      await store.add(item);
      
      // Update local state
      setCompletionHistory(prev => [item, ...prev]);
    } catch (error) {
      console.error('Failed to save to history:', error);
    }
  };

  const exportHistory = () => {
    if (!completionHistory.length) return

    try {
      const csvRows = [['Timestamp', 'Model', 'Backend Model', 'Duration', 'Prompt', 'Response']]
      
      completionHistory.forEach(item => {
        const escapeCsvField = (field: string | number): string => {
          const stringField = String(field)
          if (typeof field === 'number') return stringField
          
          if (stringField.includes('"') || stringField.includes(',') || stringField.includes('\n')) {
            return `"${stringField.replace(/"/g, '""')}"`
          }
          return stringField
        }

        csvRows.push([
          new Date(item.timestamp).toISOString(),
          escapeCsvField(MODELS[item.model as keyof typeof MODELS]),
          escapeCsvField(MODEL_VALUES[item.model as keyof typeof MODEL_VALUES]),
          item.duration.toString(),
          escapeCsvField(item.prompt),
          escapeCsvField(item.response)
        ])
      })

      const csvContent = csvRows.map(row => row.join(',')).join('\n')
      const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `deepseek_history_${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(link.href)
    } catch (error) {
      console.error('Failed to export history:', error)
      alert('Failed to export history. Please check console for details.')
    }
  }

  const handleSubmit = async () => {
    if (!prompt.trim() || isLoading) return;

    const backendModel = MODEL_VALUES[selectedModel as keyof typeof MODEL_VALUES];
    console.log('Submitting completion request:', {
      model: {
        frontend: selectedModel,
        backend: backendModel,
        display: MODELS[selectedModel as keyof typeof MODELS]
      },
      prompt: prompt.trim(),
      timestamp: new Date().toISOString()
    });

    setIsLoading(true);
    setOutput('');
    setCompletionTime(null);
    const startTime = Date.now();

    try {
      const response = await fetch(`${BACKEND_URL}/completion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          prompt: prompt.trim(),
          model: backendModel
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Completion request failed:', {
          status: response.status,
          statusText: response.statusText,
          error: errorText,
          model: backendModel,
          timestamp: new Date().toISOString()
        });
        throw new Error(errorText || 'Failed to get completion');
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      // Set up streaming
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        fullResponse += chunk;
        setOutput(fullResponse);
      }

      const duration = (Date.now() - startTime) / 1000;
      setCompletionTime(duration);

      // Save to history
      const historyItem: HistoryItem = {
        timestamp: startTime,
        model: selectedModel,
        prompt: prompt.trim(),
        response: fullResponse,
        duration
      };

      await saveToHistory(historyItem);
    } catch (error) {
      console.error('Error in completion request:', {
        error,
        model: backendModel,
        timestamp: new Date().toISOString()
      });
      setOutput('Error getting completion. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const renderHistoryItem = (item: HistoryItem) => {
    const date = new Date(item.timestamp)
    const formattedDate = date.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    })
    const formattedTime = date.toLocaleTimeString([], { 
      hour: 'numeric',
      minute: '2-digit',
      hour12: true 
    })

    const metadata = `<div class="bg-gray-50 p-2 rounded">Model: ${MODELS[item.model as keyof typeof MODELS]}<br>
Backend Model: ${MODEL_VALUES[item.model as keyof typeof MODEL_VALUES]}<br>
Date: ${formattedDate}<br>
Time: ${formattedTime}<br>
Duration: ${item.duration.toFixed(2)}s
</div>

${item.response}`

    return metadata
  }

  // Update useEffect for keyboard navigation
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!completionHistory.length) return

      if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
        event.preventDefault() // Prevent page scrolling

        const currentIndex = selectedHistoryId 
          ? completionHistory.findIndex(item => item.timestamp === selectedHistoryId)
          : -1

        const exportButton = document.querySelector('button[title="Export History"]') as HTMLElement

        let newIndex = currentIndex // Declare newIndex here

        if (event.key === 'ArrowUp') {
          // If export button is highlighted, go back to last item
          if (exportButton?.classList.contains('bg-blue-100')) {
            const lastItem = completionHistory[completionHistory.length - 1]
            setSelectedHistoryId(lastItem.timestamp)
            setIsHistoryView(true)
            setPrompt(lastItem.prompt)
            const content = `# ${lastItem.prompt}\n\n${renderHistoryItem(lastItem)}`
            setOutput(content)
            setCompletionTime(lastItem.duration)
            exportButton.classList.remove('bg-blue-100', 'hover:bg-blue-200')
            return
          }

          // If we're at the first item and going up, clear selection
          if (currentIndex === 0) {
            setSelectedHistoryId(null)
            setIsHistoryView(false)
            setPrompt('')
            setOutput('')
            setCompletionTime(null)
            return
          }
          // Otherwise move up (to older items)
          newIndex = currentIndex === -1 
            ? completionHistory.length - 1 
            : Math.max(0, currentIndex - 1)
        } else {
          // If we're at the last item and going down, highlight export button
          if (currentIndex === completionHistory.length - 1) {
            if (exportButton) {
              exportButton.classList.add('bg-blue-100', 'hover:bg-blue-200')
            }
            return
          }
          // Otherwise move down (to newer items)
          newIndex = currentIndex === -1 
            ? 0 
            : Math.min(completionHistory.length - 1, currentIndex + 1)
        }

        if (newIndex >= 0 && newIndex < completionHistory.length) {
          const selectedItem = completionHistory[newIndex]
          setSelectedHistoryId(selectedItem.timestamp)
          setIsHistoryView(true)
          setPrompt(selectedItem.prompt)
          const content = `# ${selectedItem.prompt}\n\n${renderHistoryItem(selectedItem)}`
          setOutput(content)
          setCompletionTime(selectedItem.duration)

          // Scroll the selected item into view
          const element = document.querySelector(`[data-timestamp="${selectedItem.timestamp}"]`)
          element?.scrollIntoView({ block: 'nearest' })
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [completionHistory, selectedHistoryId]) // Add dependencies

  // Update the model selection handler with more logging
  const handleModelChange = async (value: string) => {
    const frontendModel = value;
    const backendModel = MODEL_VALUES[value as keyof typeof MODEL_VALUES];
    const displayName = MODELS[value as keyof typeof MODELS];

    console.log('Model selection changed:', {
      frontendModel,
      backendModel,
      displayName,
      timestamp: new Date().toISOString()
    });

    setSelectedModel(value);
    
    try {
      console.log('Sending model update to backend:', {
        url: `${BACKEND_URL}/model`,
        model: backendModel
      });

      const response = await fetch(`${BACKEND_URL}/model`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: backendModel })
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Model update failed:', {
          status: response.status,
          statusText: response.statusText,
          error: errorText
        });
        throw new Error(`Failed to update model: ${errorText}`);
      }

      const result = await response.json();
      console.log('Model update successful:', {
        result,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error('Error updating model:', {
        error,
        model: backendModel,
        timestamp: new Date().toISOString()
      });
    }
  };

  // Add this new function for handling undo
  const handleUndo = async () => {
    if (deletedItems.length === 0 || !lastDeletedTimestamp) return;
    
    const itemToRestore = deletedItems[deletedItems.length - 1];
    console.log('Restoring item:', itemToRestore);

    try {
      // Add back to IndexedDB
      if (db) {
        const transaction = db.transaction(['history'], 'readwrite');
        const store = transaction.objectStore('history');
        await store.add(itemToRestore);
      }

      // Update state
      setCompletionHistory(prev => [itemToRestore, ...prev]);
      setDeletedItems(prev => prev.slice(0, -1));
      setLastDeletedTimestamp(null);
      
      console.log('Successfully restored item');
    } catch (error) {
      console.error('Failed to restore item:', error);
    }
  };

  // Add keyboard listener for Ctrl+Z
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        handleUndo();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [deletedItems, lastDeletedTimestamp]);

  // Update the delete function
  const deleteHistoryItem = async (timestamp: number) => {
    const itemToDelete = completionHistory.find(item => item.timestamp === timestamp);
    if (!itemToDelete) return;

    try {
      // Remove from IndexedDB
      if (db) {
        const transaction = db.transaction(['history'], 'readwrite');
        const store = transaction.objectStore('history');
        await store.delete(timestamp);
      }

      // Update states
      setCompletionHistory(prev => prev.filter(item => item.timestamp !== timestamp));
      setDeletedItems(prev => [...prev, itemToDelete]);
      setLastDeletedTimestamp(timestamp);
      
      // Reset view if we're deleting the currently viewed item
      if (selectedHistoryId === timestamp) {
        setSelectedHistoryId(null);
        setIsHistoryView(false);
        setPrompt('');
        setOutput('');
        setCompletionTime(null);
      }

      console.log('Successfully deleted item');
    } catch (error) {
      console.error('Failed to delete item:', error);
    }
  };

  // Add resize handler
  const startResizing = (e: React.MouseEvent) => {
    setIsResizing(true)
    e.preventDefault()
  }

  const stopResizing = () => {
    setIsResizing(false)
  }

  const resize = (e: MouseEvent) => {
    if (isResizing) {
      const newWidth = e.clientX
      if (newWidth > 150 && newWidth < 800) { // Min 150px, max 800px
        setSidebarWidth(newWidth)
      }
    }
  }

  useEffect(() => {
    window.addEventListener('mousemove', resize)
    window.addEventListener('mouseup', stopResizing)
    return () => {
      window.removeEventListener('mousemove', resize)
      window.removeEventListener('mouseup', stopResizing)
    }
  }, [isResizing])

  const handleExportToRichText = () => {
    if (!selectedHistoryId) return;
    
    const item = completionHistory.find(item => item.timestamp === selectedHistoryId);
    if (!item) return;

    try {
      // Create a new blob with HTML content
      const date = new Date(item.timestamp);
      const formattedDate = date.toLocaleDateString('en-GB', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      });
      const formattedTime = date.toLocaleTimeString([], { 
        hour: 'numeric',
        minute: '2-digit',
        hour12: true 
      });

      const htmlContent = `
        <html>
          <head>
            <style>
              body { font-family: Arial, sans-serif; line-height: 1.6; }
              .metadata { background: #f5f5f5; padding: 1rem; margin: 1rem 0; border-radius: 4px; }
              .content { margin: 1rem 0; }
            </style>
          </head>
          <body>
            <h1>${item.prompt}</h1>
            <div class="metadata">
              <div>Model: ${MODELS[item.model as keyof typeof MODELS]}</div>
              <div>Backend Model: ${MODEL_VALUES[item.model as keyof typeof MODEL_VALUES]}</div>
              <div>Date: ${formattedDate}</div>
              <div>Time: ${formattedTime}</div>
              <div>Duration: ${item.duration.toFixed(2)}s</div>
            </div>
            <div class="content">
              ${DOMPurify.sanitize(marked.parse(item.response))}
            </div>
          </body>
        </html>
      `;

      // Create a sanitized filename from the prompt
      const sanitizedPrompt = item.prompt
        .replace(/[^a-z0-9]/gi, '_') // Replace invalid chars with underscore
        .replace(/_+/g, '_')         // Replace multiple underscores with single
        .substring(0, 50)            // Limit length to 50 chars
        .trim();                     // Trim any trailing spaces/underscores

      const blob = new Blob([htmlContent], { type: 'text/html' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${sanitizedPrompt}.html`;
      
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      console.log('Export successful');
    } catch (error) {
      console.error('Error exporting history:', error);
    }
  };

  const handleExportToPDF = async () => {
    try {
      const html2pdf = (await import('html2pdf.js')).default;
      
      const element = document.getElementById('export-content');
      if (!element) {
        throw new Error('Export content not found');
      }

      // Get the current history item
      const item = completionHistory.find(item => item.timestamp === selectedHistoryId);
      if (!item) {
        throw new Error('History item not found');
      }

      // Create a sanitized filename from the prompt
      // Replace invalid filename characters and trim length
      const sanitizedPrompt = item.prompt
        .replace(/[^a-z0-9]/gi, '_') // Replace invalid chars with underscore
        .replace(/_+/g, '_')         // Replace multiple underscores with single
        .substring(0, 50)            // Limit length to 50 chars
        .trim();                     // Trim any trailing spaces/underscores

      const opt = {
        margin: 1,
        filename: `${sanitizedPrompt}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2 },
        jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' }
      };

      await html2pdf().set(opt).from(element).save();
    } catch (error) {
      console.error('Error exporting to PDF:', error);
      // Add proper error handling here
    }
  };

  return (
    <div className="flex h-screen">
      {/* Sidebar with dynamic width */}
      <div 
        className="bg-gray-50 border-r border-gray-200 flex flex-col relative" 
        style={{ width: sidebarWidth }}
      >
        <Button 
          onClick={() => {
            setPrompt('')
            setOutput('')
            setCompletionTime(null)
            setSelectedHistoryId(null)
            setIsHistoryView(false)
          }}
          variant="secondary"
          className={`m-2 bg-gray-200 hover:bg-gray-300 ${selectedHistoryId === null ? 'bg-blue-100 hover:bg-blue-200' : ''}`}
        >
          New Prompt
        </Button>

        <div className="flex-1 overflow-y-auto">
          {completionHistory.map((item) => (
            <div 
              key={item.timestamp}
              data-timestamp={item.timestamp}
              className={`p-2 border-b border-gray-200 cursor-pointer text-sm ${
                selectedHistoryId === item.timestamp 
                  ? 'bg-blue-100 hover:bg-blue-200' 
                  : 'hover:bg-gray-100'
              }`}
              onClick={() => {
                setSelectedHistoryId(item.timestamp)
                setIsHistoryView(true)
                setPrompt(item.prompt)
                const content = `# ${item.prompt}\n\n${renderHistoryItem(item)}`
                setOutput(content)
                setCompletionTime(item.duration)
              }}
            >
              <div className="truncate">{item.prompt}</div>
            </div>
          ))}
        </div>

        <Button 
          onClick={exportHistory}
          variant="secondary"
          className="m-2 bg-gray-200 hover:bg-gray-300 w-full justify-start [&>svg]:hidden"
        >
          Export History
        </Button>

        {/* Add resize handle */}
        <div
          className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-500 hover:w-1"
          onMouseDown={startResizing}
        />
      </div>

      {/* Main Content */}
      <div className="flex-1 p-6 overflow-y-auto">
        <div className="max-w-3xl mx-auto space-y-4">
          {isHistoryView && (
            <div className="absolute top-0 right-0 flex gap-2 p-2">
              <Button
                onClick={handleExportToRichText}
                variant="outline"
                size="icon"
                className="hover:bg-blue-100 hover:text-blue-500 transition-colors"
                title="Export as HTML"
              >
                <FileText className="h-4 w-4" />
              </Button>
              <Button
                onClick={handleExportToPDF}
                variant="outline"
                size="icon"
                className="hover:bg-blue-100 hover:text-blue-500 transition-colors"
                title="Export as PDF"
              >
                <Download className="h-4 w-4" />
              </Button>
              <Button
                onClick={() => selectedHistoryId && deleteHistoryItem(selectedHistoryId)}
                variant="outline"
                size="icon"
                className="hover:bg-red-100 hover:text-red-500 transition-colors"
                title="Delete (Ctrl+Z to undo)"
              >
                <Trash className="h-4 w-4" />
              </Button>
            </div>
          )}

          {!isHistoryView ? (
            <>
              <div className="w-full bg-white">
                <Select
                  value={selectedModel}
                  onValueChange={handleModelChange}
                >
                  <SelectTrigger className="w-full bg-white border border-input">
                    <SelectValue placeholder="Select a model" />
                  </SelectTrigger>
                  <SelectContent className="bg-white border shadow-md">
                    {Object.entries(MODELS).map(([value, label]) => (
                      <SelectItem 
                        key={value} 
                        value={value}
                        className="hover:bg-gray-100"
                      >
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <Textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Enter your prompt..."
                className="min-h-[2.5rem] max-h-[2.5rem] resize-none py-2"
              />

              <div className="flex items-center gap-4">
                <Button
                  onClick={handleSubmit}
                  disabled={isLoading || !prompt.trim()}
                  className="flex items-center gap-2 bg-gray-200 hover:bg-gray-300"
                >
                  {isLoading && (
                    <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  )}
                  {isLoading ? 'Processing...' : 'Get Completion'}
                </Button>
                {completionTime !== null && (
                  <span className="text-sm text-gray-500">
                    Completed in {completionTime.toFixed(2)}s
                  </span>
                )}
              </div>
            </>
          ) : null}

          {output && (
            <div 
              id="export-content"
              className="prose prose-sm max-w-none dark:prose-invert [&_.bg-gray-50]:bg-gray-50 [&_.bg-gray-50]:my-4 text-sm"
              dangerouslySetInnerHTML={{ 
                __html: DOMPurify.sanitize(marked.parse(output)) 
              }} 
            />
          )}
        </div>
      </div>
    </div>
  )
}
