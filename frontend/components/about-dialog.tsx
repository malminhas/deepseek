"use client"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { MermaidDiagram } from "@/components/mermaid-diagram"
import { useEffect, useState } from 'react'
import { X } from "lucide-react"
import * as DialogPrimitive from "@radix-ui/react-dialog"

const diagram = `
flowchart TD
    U[User Browser]
    
    subgraph FE[Frontend :8084]
        N[Next.js]
        T[Tailwind CSS]
        S[shadcn/ui]
        N --> T & S
    end
    
    subgraph BE[Backend :8083]
        F[FastAPI]
        subgraph LLM[LLM APIs]
            D[Deepseek Chat V3]
            R[Deepseek Reasoner R1]
            G[Groq Deepseek R1]
            P[Perplexity Sonar]
            O[Ollama Deepseek R1]
        end
        F --> D & R & G & P & O
    end
    
    U --> N
    N -- "HTTP/REST" --> F
    
    %% Styling
    style U fill:#e8f4f8,stroke:#333
    style N fill:#d9e7ff,stroke:#333
    style T fill:#d9e7ff,stroke:#333
    style S fill:#d9e7ff,stroke:#333
    style F fill:#ffe7d9,stroke:#333
    style D fill:#d9ffe7,stroke:#333
    style R fill:#d9ffe7,stroke:#333
    style G fill:#d9ffe7,stroke:#333
    style P fill:#d9ffe7,stroke:#333
    style O fill:#d9ffe7,stroke:#333
    style FE fill:#f9f9f9,stroke:#333,stroke-width:2px
    style BE fill:#f9f9f9,stroke:#333,stroke-width:2px
    style LLM fill:#f0f0f0,stroke:#666,stroke-width:1px
`

interface VersionInfo {
  version: string
  author: string
  releaseDate: string
  license: string
}

// Add props interface
interface AboutDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AboutDialog({ open, onOpenChange }: AboutDialogProps) {
  const [versionInfo, setVersionInfo] = useState<VersionInfo | null>(null);

  useEffect(() => {
    const fetchVersionInfo = async () => {
      try {
        const response = await fetch('http://localhost:8083/version');
        const data: VersionInfo = await response.json();
        setVersionInfo(data);
      } catch (error) {
        console.error('Failed to fetch version info:', error);
        setVersionInfo({
          version: 'unknown',
          author: 'unknown',
          releaseDate: 'unknown',
          license: 'unknown'
        });
      }
    };

    fetchVersionInfo();
  }, []);

  const currentDate = new Date().toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="top-[50%] left-[50%] translate-x-[-50%] translate-y-[-50%] fixed w-[95vw] max-w-[900px] max-h-[90vh] overflow-y-auto bg-white dark:bg-gray-900 rounded-lg shadow-lg border p-6">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold">About Deepseek Chat</DialogTitle>
          <DialogDescription>
            System Architecture and Technical Overview
          </DialogDescription>
        </DialogHeader>

        <div className="mt-6 space-y-6">
          {/* Version Info Section */}
          <div className="space-y-2">
            <div className="font-medium">Version: {versionInfo?.version || 'Loading...'}</div>
            <div className="font-medium">Author: {versionInfo?.author || 'Loading...'}</div>
            <div className="font-medium">Release Date: {versionInfo?.releaseDate || 'Loading...'}</div>
            <div className="font-medium">License: {versionInfo?.license || 'Loading...'}</div>
          </div>

          {/* Architecture Diagram */}
          <div className="border rounded-lg p-6 bg-white">
            <h3 className="text-lg font-semibold mb-4">System Architecture Diagram</h3>
            <MermaidDiagram diagram={diagram} />
          </div>

          {/* Frontend Architecture */}
          <div className="space-y-3">
            <h3 className="text-lg font-semibold">Frontend Architecture</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong>Next.js:</strong> React framework providing server-side rendering, routing, and API handling</li>
              <li><strong>Tailwind CSS:</strong> Utility-first CSS framework for responsive and maintainable styling</li>
              <li><strong>shadcn/ui:</strong> Reusable component library built on Radix UI, providing accessible UI components</li>
            </ul>
          </div>

          {/* Backend Architecture */}
          <div className="space-y-3">
            <h3 className="text-lg font-semibold">Backend Architecture</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong>FastAPI:</strong> Modern Python web framework for building high-performance APIs</li>
              <li><strong>Documentation:</strong> <a href="http://localhost:8083/docs" target="_blank" className="text-blue-500 hover:underline">API Documentation (Swagger UI)</a></li>
            </ul>
          </div>

          {/* LLM Models */}
          <div className="space-y-3">
            <h3 className="text-lg font-semibold">LLM Integration</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li>
                <strong>Deepseek Chat V3:</strong> Primary chat model
                <ul className="list-disc pl-6 mt-1">
                  <li>67B parameters, optimized for dialogue</li>
                  <li>Enhanced context understanding and response coherence</li>
                </ul>
              </li>
              <li>
                <strong>Deepseek Reasoner R1:</strong> Enhanced reasoning capabilities
                <ul className="list-disc pl-6 mt-1">
                  <li>Specialized in complex problem-solving and logical reasoning</li>
                  <li>Improved mathematical and analytical capabilities</li>
                </ul>
              </li>
              <li>
                <strong>Groq Deepseek R1:</strong> High-performance inference
                <ul className="list-disc pl-6 mt-1">
                  <li>Optimized for low-latency responses</li>
                  <li>Hardware-accelerated inference</li>
                </ul>
              </li>
              <li>
                <strong>Perplexity Sonar:</strong> Alternative model provider
                <ul className="list-disc pl-6 mt-1">
                  <li>Specialized in factual accuracy and current information</li>
                  <li>Enhanced knowledge retrieval capabilities</li>
                </ul>
              </li>
              <li>
                <strong>Ollama Deepseek R1:</strong> Local model deployment
                <ul className="list-disc pl-6 mt-1">
                  <li>Self-hosted option for privacy and control</li>
                  <li>Optimized for local hardware acceleration</li>
                </ul>
              </li>
            </ul>
          </div>

          {/* System Requirements */}
          <div className="space-y-3">
            <h3 className="text-lg font-semibold">System Requirements</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong>Frontend:</strong> Runs on port 8084</li>
              <li><strong>Backend:</strong> Runs on port 8083</li>
              <li><strong>Communication:</strong> HTTP/REST API with JSON payloads</li>
              <li><strong>Environment:</strong> Docker containerized deployment</li>
            </ul>
          </div>
        </div>

        <DialogPrimitive.Close className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground">
          <X className="h-4 w-4" />
          <span className="sr-only">Close</span>
        </DialogPrimitive.Close>
      </DialogContent>
    </Dialog>
  )
} 