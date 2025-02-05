"use client"

import { useEffect, useRef } from 'react'
import mermaid from 'mermaid'

interface MermaidProps {
  diagram: string
}

export function MermaidDiagram({ diagram }: MermaidProps) {
  const elementRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const renderDiagram = async () => {
      try {
        // Initialize mermaid with basic config
        mermaid.initialize({ 
          startOnLoad: false,
          theme: 'default',
          securityLevel: 'loose',
        })

        // Generate unique ID for this diagram
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`
        
        if (elementRef.current) {
          const { svg } = await mermaid.render(id, diagram)
          elementRef.current.innerHTML = svg
        }
      } catch (error) {
        console.error('Mermaid rendering failed:', error)
        if (elementRef.current) {
          elementRef.current.innerHTML = `<div class="text-red-500">Error rendering diagram: ${error.message}</div>`
        }
      }
    }

    renderDiagram()
  }, [diagram])

  return <div ref={elementRef} className="bg-white p-4 rounded-lg" />
} 