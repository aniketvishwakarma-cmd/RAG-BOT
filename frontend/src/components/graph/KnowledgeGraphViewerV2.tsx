import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { forceCollide } from 'd3'
import ForceGraph2D from 'react-force-graph-2d'
import { graphApi } from '../../api/graphApi'

type BackendGraphPayload = {
  nodes?: Array<Record<string, unknown>>
  edges?: Array<Record<string, unknown>>
}

type GraphNode = {
  id: string
  label: string
  nodeType: string
  layer?: string
  desc?: string
  degree: number
  radius: number
  x?: number
  y?: number
  vx?: number
  vy?: number
}

type GraphLink = {
  source: string
  target: string
  relation: string
}

type RenderNode = GraphNode
type RenderLink = GraphLink & { source: string | RenderNode; target: string | RenderNode }

function useElementSize<T extends HTMLElement>() {
  const ref = useRef<T | null>(null)
  const [size, setSize] = useState({ width: 900, height: 640 })

  useEffect(() => {
    const element = ref.current
    if (!element) return
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (!entry) return
      setSize({
        width: Math.max(320, Math.floor(entry.contentRect.width)),
        height: Math.max(420, Math.floor(entry.contentRect.height))
      })
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  return [ref, size] as const
}

function inferNodeType(rawNode: Record<string, unknown>) {
  const explicit = String(rawNode.node_type || '').trim()
  if (explicit) return explicit

  const id = String(rawNode.id || '').toLowerCase()
  if (id.startsWith('document:') || id.startsWith('doc_')) return 'document'
  if (id.startsWith('section:')) return 'section'
  if (id.startsWith('process:')) return 'process'
  if (id.startsWith('timeline:')) return 'timeline'
  if (id.startsWith('penalty:')) return 'penalty'
  if (id.startsWith('regulator:')) return 'regulator'
  if (id.startsWith('act:')) return 'act'
  return 'entity'
}

function colorForType(nodeType: string) {
  switch (nodeType) {
    case 'document':
      return '#2563EB'
    case 'regulator':
      return '#7C3AED'
    case 'act':
      return '#0F766E'
    case 'section':
      return '#D97706'
    case 'process':
      return '#DC2626'
    case 'timeline':
      return '#9333EA'
    case 'penalty':
      return '#059669'
    default:
      return '#475569'
  }
}

function wrapLabel(label: string) {
  if (label.length <= 18) return [label]
  const words = label.split(' ')
  if (words.length === 1) return [label]
  const midpoint = Math.ceil(words.length / 2)
  return [words.slice(0, midpoint).join(' '), words.slice(midpoint).join(' ')]
}

function normalizeGraph(payload: BackendGraphPayload | undefined, width: number, height: number) {
  const nodeMap = new Map<string, GraphNode>()
  const links: GraphLink[] = []

  for (const rawNode of payload?.nodes || []) {
    const nodeType = inferNodeType(rawNode)
    if (nodeType === 'chunk') continue

    const id = String(rawNode.id || '').trim()
    if (!id) continue

    nodeMap.set(id, {
      id,
      label: String(rawNode.title || rawNode.label || rawNode.id || '').trim() || id,
      nodeType,
      layer: rawNode.layer ? String(rawNode.layer) : undefined,
      desc: String(rawNode.section_no || rawNode.clause_no || rawNode.title || rawNode.label || '').trim() || undefined,
      degree: 0,
      radius: 12
    })
  }

  for (const rawEdge of payload?.edges || []) {
    const source = String(rawEdge.source || '').trim()
    const target = String(rawEdge.target || '').trim()
    if (!source || !target || source === target) continue

    if (!nodeMap.has(source)) {
      nodeMap.set(source, {
        id: source,
        label: source,
        nodeType: inferNodeType({ id: source }),
        degree: 0,
        radius: 12
      })
    }

    if (!nodeMap.has(target)) {
      nodeMap.set(target, {
        id: target,
        label: target,
        nodeType: inferNodeType({ id: target }),
        degree: 0,
        radius: 12
      })
    }

    links.push({
      source,
      target,
      relation: String(rawEdge.relation || 'related_to')
    })
  }

  for (const link of links) {
    const source = nodeMap.get(link.source)
    const target = nodeMap.get(link.target)
    if (source) source.degree += 1
    if (target) target.degree += 1
  }

  const nodes = Array.from(nodeMap.values())
  const columns = Math.max(1, Math.ceil(Math.sqrt(nodes.length || 1)))
  const rows = Math.max(1, Math.ceil(nodes.length / columns))
  const usableWidth = Math.max(320, width - 160)
  const usableHeight = Math.max(320, height - 160)

  return {
    nodes: nodes.map((node, index) => {
      const column = index % columns
      const row = Math.floor(index / columns)
      return {
        ...node,
        radius: Math.min(34, 10 + node.degree * 3),
        x: -usableWidth / 2 + ((column + 0.5) * usableWidth) / columns,
        y: -usableHeight / 2 + ((row + 0.5) * usableHeight) / rows
      }
    }),
    links
  }
}

export function KnowledgeGraphViewerV2() {
  const fgRef = useRef<any>(null)
  const [containerRef, graphSize] = useElementSize<HTMLDivElement>()
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)

  const graphQuery = useQuery<BackendGraphPayload>({
    queryKey: ['graph-relations'],
    queryFn: () => graphApi.relations(500),
    refetchInterval: 30000
  })

  const graphData = useMemo(
    () => normalizeGraph(graphQuery.data, graphSize.width, graphSize.height),
    [graphQuery.data, graphSize]
  )

  useEffect(() => {
    const fg = fgRef.current
    if (!fg || !graphData.nodes.length) return

    fg.d3Force('charge')?.strength?.(-300)
    fg.d3Force('link')?.distance?.(120)
    fg.d3Force('collision', forceCollide(40))
    fg.d3ReheatSimulation?.()

    const timer = window.setTimeout(() => {
      fg.zoomToFit?.(600, 80)
    }, 1200)

    return () => window.clearTimeout(timer)
  }, [graphData])

  useEffect(() => {
    if (selectedNode && !graphData.nodes.some((node) => node.id === selectedNode.id)) {
      setSelectedNode(null)
    }
  }, [graphData, selectedNode])

  return (
    <div className="flex h-[760px] flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div className="text-sm font-medium text-slate-800">
          Knowledge graph - {graphData.nodes.length} nodes - {graphData.links.length} edges
        </div>
        <div className="text-xs text-slate-500">Drag to pan - Scroll to zoom - Click a node for details</div>
      </div>

      {graphQuery.isLoading ? (
        <div className="flex flex-1 items-center justify-center text-sm text-slate-500">Loading graph relations...</div>
      ) : graphQuery.isError ? (
        <div className="flex flex-1 items-center justify-center text-sm text-rose-600">
          Failed to load graph: {(graphQuery.error as Error).message}
        </div>
      ) : graphData.nodes.length === 0 ? (
        <div className="flex flex-1 items-center justify-center text-sm text-slate-500">
          No graph relations found yet. Run the graph relation builder script first.
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 overflow-hidden">
          <div ref={containerRef} className="min-w-0 flex-1 bg-white">
            <ForceGraph2D
              ref={fgRef}
              width={graphSize.width}
              height={graphSize.height}
              graphData={graphData}
              nodeId="id"
              backgroundColor="#FFFFFF"
              enableNodeDrag
              enablePanInteraction
              enableZoomInteraction
              cooldownTicks={180}
              onNodeClick={(node) => setSelectedNode(node as GraphNode)}
              onBackgroundClick={() => setSelectedNode(null)}
              nodeCanvasObjectMode={() => 'replace'}
              nodeCanvasObject={(nodeObject, ctx, globalScale) => {
                const node = nodeObject as RenderNode
                const color = colorForType(node.nodeType)
                const radius = node.radius
                const fontSize = Math.max(9, 12 / globalScale)
                const labelLines = wrapLabel(node.label)

                ctx.beginPath()
                ctx.arc(node.x || 0, node.y || 0, radius, 0, 2 * Math.PI)
                ctx.fillStyle = color
                ctx.fill()
                ctx.strokeStyle = '#FFFFFF'
                ctx.lineWidth = 2
                ctx.stroke()

                ctx.font = `600 ${fontSize}px sans-serif`
                const widestLine = Math.max(...labelLines.map((line) => ctx.measureText(line).width))
                const labelHeight = labelLines.length * (fontSize + 2)
                const labelX = (node.x || 0) - widestLine / 2 - 6
                const labelY = (node.y || 0) + radius + 10

                ctx.fillStyle = 'rgba(255,255,255,0.92)'
                ctx.fillRect(labelX, labelY, widestLine + 12, labelHeight + 8)

                ctx.textAlign = 'center'
                ctx.textBaseline = 'top'
                ctx.fillStyle = '#0F172A'
                labelLines.forEach((line, index) => {
                  ctx.fillText(line, node.x || 0, labelY + 4 + index * (fontSize + 2))
                })
              }}
              linkCanvasObjectMode={() => 'replace'}
              linkCanvasObject={(linkObject, ctx, globalScale) => {
                const link = linkObject as RenderLink
                const source = link.source as RenderNode
                const target = link.target as RenderNode

                ctx.strokeStyle = '#CBD5E1'
                ctx.lineWidth = Math.max(1, 1.25 / globalScale)
                ctx.beginPath()
                ctx.moveTo(source.x || 0, source.y || 0)
                ctx.lineTo(target.x || 0, target.y || 0)
                ctx.stroke()

                if (globalScale > 1.2) {
                  ctx.font = `${Math.max(7, 9 / globalScale)}px sans-serif`
                  ctx.fillStyle = '#64748B'
                  ctx.textAlign = 'center'
                  ctx.textBaseline = 'bottom'
                  ctx.fillText(
                    link.relation,
                    ((source.x || 0) + (target.x || 0)) / 2,
                    ((source.y || 0) + (target.y || 0)) / 2 - 4
                  )
                }
              }}
            />
          </div>

          {selectedNode && (
            <aside className="w-[280px] border-l border-slate-200 bg-slate-50 p-4">
              <div className="text-sm font-semibold" style={{ color: colorForType(selectedNode.nodeType) }}>
                {selectedNode.label}
              </div>
              <div className="mt-2 text-xs uppercase tracking-wide text-slate-500">{selectedNode.nodeType}</div>
              {selectedNode.layer && <div className="mt-2 text-xs text-slate-500">Layer: {selectedNode.layer}</div>}
              {selectedNode.desc && <p className="mt-3 text-sm leading-6 text-slate-700">{selectedNode.desc}</p>}
              <div className="mt-4 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
                Connections: {selectedNode.degree}
              </div>
            </aside>
          )}
        </div>
      )}
    </div>
  )
}
