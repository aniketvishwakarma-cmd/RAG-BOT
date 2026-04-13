import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { forceX, forceY } from 'd3'
import ForceGraph2D from 'react-force-graph-2d'
import { useNavigate } from 'react-router-dom'

type DocKey = 'rbi' | 'cicra05' | 'reg' | 'rules'
type EntityType = 'penalty' | 'timeline' | 'stakeholder' | 'obligation' | 'process'

export interface GraphNode {
  id: string
  label: string
  type: 'doc' | 'entity'
  docKey?: DocKey
  chunks?: number
  entityType?: EntityType
  desc?: string
  sources?: string[]
  section?: string
  title?: string
  layer?: string
  node_type?: string
}

export interface GraphEdge {
  source: string
  target: string
  relation: string
  color?: string
  dashed?: boolean
  thick?: boolean
}

type BackendGraphPayload = {
  nodes?: Array<Record<string, unknown>>
  edges?: Array<Record<string, unknown>>
}

type RenderNode = GraphNode & { x?: number; y?: number; vx?: number; vy?: number; fx?: number; fy?: number }
type RenderLink = GraphEdge & { source: string | RenderNode; target: string | RenderNode }

const DOC_STYLES: Record<DocKey, { fill: string; stroke: string; textColor: string; size: number; buttonBg: string; buttonText: string }> = {
  rbi: { fill: '#EEEDFE', stroke: '#534AB7', textColor: '#3C3489', size: 30, buttonBg: '#EEEDFE', buttonText: '#3C3489' },
  cicra05: { fill: '#E6F1FB', stroke: '#185FA5', textColor: '#0C447C', size: 28, buttonBg: '#E6F1FB', buttonText: '#0C447C' },
  reg: { fill: '#E1F5EE', stroke: '#0F6E56', textColor: '#085041', size: 26, buttonBg: '#E1F5EE', buttonText: '#085041' },
  rules: { fill: '#FAEEDA', stroke: '#BA7517', textColor: '#633806', size: 24, buttonBg: '#FAEEDA', buttonText: '#633806' }
}

const ENTITY_STYLES: Record<EntityType, { color: string; size: number }> = {
  penalty: { color: '#534AB7', size: 18 },
  timeline: { color: '#D85A30', size: 18 },
  stakeholder: { color: '#185FA5', size: 16 },
  obligation: { color: '#0F6E56', size: 15 },
  process: { color: '#BA7517', size: 14 }
}

const HARD_CODED_NODES: GraphNode[] = [
  { id: 'doc_rbi', label: 'RBI Circular', type: 'doc', docKey: 'rbi', chunks: 68 },
  { id: 'doc_cicra05', label: 'CICRA Act 2005', type: 'doc', docKey: 'cicra05', chunks: 47 },
  { id: 'doc_reg', label: 'CICRA 2006 Regs', type: 'doc', docKey: 'reg', chunks: 40 },
  { id: 'doc_rules', label: 'CICRA 2006 Rules', type: 'doc', docKey: 'rules', chunks: 24 },
  { id: 'e_100', label: '₹100/day Consumer', type: 'entity', entityType: 'penalty', desc: 'Compensation paid TO CONSUMER for delayed dispute resolution', sources: ['doc_rbi', 'doc_cicra05'], section: 'RBI Circular RBI/2023-24/72' },
  { id: 'e_5000', label: '₹5000/day Regulator', type: 'entity', entityType: 'penalty', desc: 'Penalty paid TO RBI REGULATOR for data reporting violations', sources: ['doc_rbi'], section: 'CICRA Act 2005 Section 23' },
  { id: 'e_30day', label: '30-Day Hard Window', type: 'entity', entityType: 'timeline', desc: 'Total mandatory resolution window: 21 days (CI) + 9 days (CIC)', sources: ['doc_rbi', 'doc_cicra05', 'doc_reg', 'doc_rules'] },
  { id: 'e_21day', label: '21-Day CI Window', type: 'entity', entityType: 'timeline', desc: 'Credit Institution must confirm/rectify within 21 calendar days', sources: ['doc_rbi', 'doc_rules'] },
  { id: 'e_9day', label: '9-Day CIC Window', type: 'entity', entityType: 'timeline', desc: 'Credit Information Company resolves within remaining 9 days', sources: ['doc_rbi', 'doc_reg'] },
  { id: 'e_rbi', label: 'RBI Regulator', type: 'entity', entityType: 'stakeholder', desc: 'Supreme regulatory authority. Issues Master Directions. Enforces via CICRA' },
  { id: 'e_ci', label: 'Credit Institution', type: 'entity', entityType: 'stakeholder', desc: 'Banks & NBFCs. Source of truth for loan records. 21-day window' },
  { id: 'e_cic', label: 'Credit Info Company', type: 'entity', entityType: 'stakeholder', desc: 'CIBIL, Equifax, Experian, CRIF. 9-day window. Governed by CICRA 2005' },
  { id: 'e_consumer', label: 'Consumer/Borrower', type: 'entity', entityType: 'stakeholder', desc: 'Initiates dispute. Receives ₹100/day compensation if delay' },
  { id: 'e_sec21', label: 'CICRA Section 21', type: 'entity', entityType: 'obligation', desc: 'Dispute settlement provisions. Legal foundation for 30-day rule', sources: ['doc_cicra05'] },
  { id: 'e_ucrf', label: 'UCRF Format', type: 'entity', entityType: 'obligation', desc: 'Uniform Credit Reporting Format. Forms 1,2,3 for Consumer, Commercial, MFI', sources: ['doc_rbi', 'doc_reg'] },
  { id: 'e_dqi', label: 'Data Quality Index', type: 'entity', entityType: 'obligation', desc: 'Quarterly checks for PAN/Aadhaar inconsistencies. Mandatory per RBI', sources: ['doc_rbi', 'doc_reg'] },
  { id: 'e_reg100cr', label: '₹100Cr Min Capital', type: 'entity', entityType: 'obligation', desc: 'Minimum paid-up capital for CIC registration', sources: ['doc_cicra05'] },
  { id: 'e_dispute', label: 'Dispute Process', type: 'entity', entityType: 'process', desc: 'Consumer → CIC → CI → Resolution. SRN assigned on filing' },
  { id: 'e_report', label: 'Reporting Cycle', type: 'entity', entityType: 'process', desc: 'Fortnightly UCRF submission. +5 days CI validation. +7 days CIC ingestion' },
  { id: 'e_penalty_proc', label: 'Penalty Procedure', type: 'entity', entityType: 'process', desc: 'UPI payment to consumer within 5 working days. Pro-rata CI vs CIC' }
]

const HARD_CODED_EDGES: GraphEdge[] = [
  { source: 'doc_rbi', target: 'e_100', relation: 'defines', color: '#534AB7' },
  { source: 'doc_rbi', target: 'e_5000', relation: 'defines', color: '#534AB7' },
  { source: 'doc_rbi', target: 'e_21day', relation: 'defines', color: '#534AB7' },
  { source: 'doc_rbi', target: 'e_9day', relation: 'defines', color: '#534AB7' },
  { source: 'doc_rbi', target: 'e_ucrf', relation: 'defines', color: '#534AB7' },
  { source: 'doc_rbi', target: 'e_dqi', relation: 'defines', color: '#534AB7' },
  { source: 'doc_cicra05', target: 'e_sec21', relation: 'defines', color: '#185FA5' },
  { source: 'doc_cicra05', target: 'e_cic', relation: 'governs', color: '#185FA5' },
  { source: 'doc_cicra05', target: 'e_reg100cr', relation: 'mandates', color: '#185FA5' },
  { source: 'doc_reg', target: 'e_report', relation: 'defines', color: '#0F6E56' },
  { source: 'doc_reg', target: 'e_dispute', relation: 'defines', color: '#0F6E56' },
  { source: 'doc_rules', target: 'e_penalty_proc', relation: 'defines', color: '#BA7517' },
  { source: 'e_sec21', target: 'e_30day', relation: 'establishes', color: '#D85A30', dashed: true },
  { source: 'e_30day', target: 'e_21day', relation: 'splits into', color: '#D85A30' },
  { source: 'e_30day', target: 'e_9day', relation: 'splits into', color: '#D85A30' },
  { source: 'e_30day', target: 'e_100', relation: 'breach triggers', color: '#D85A30', dashed: true },
  { source: 'e_ci', target: 'e_21day', relation: 'owns', color: '#888780' },
  { source: 'e_cic', target: 'e_9day', relation: 'owns', color: '#888780' },
  { source: 'e_consumer', target: 'e_100', relation: 'receives', color: '#534AB7', dashed: true },
  { source: 'e_consumer', target: 'e_dispute', relation: 'initiates', color: '#0F6E56' },
  { source: 'e_penalty_proc', target: 'e_100', relation: 'executes', color: '#BA7517', dashed: true },
  { source: 'e_report', target: 'e_ucrf', relation: 'uses', color: '#0F6E56' },
  { source: 'e_rbi', target: 'e_5000', relation: 'collects', color: '#534AB7' },
  { source: 'doc_cicra05', target: 'doc_reg', relation: 'parent of', color: '#185FA5', thick: true },
  { source: 'doc_cicra05', target: 'doc_rules', relation: 'parent of', color: '#185FA5', thick: true },
  { source: 'doc_rbi', target: 'doc_reg', relation: 'references', color: '#534AB7', dashed: true }
]

function inferDocKey(label: string, layer?: string): DocKey | null {
  const value = `${label} ${layer || ''}`.toLowerCase()
  if (value.includes('rbi') && value.includes('circular')) return 'rbi'
  if (value.includes('cicra') && value.includes('act')) return 'cicra05'
  if (value.includes('reg')) return 'reg'
  if (value.includes('rule')) return 'rules'
  return null
}

function inferEntityType(label: string, desc = ''): EntityType {
  const value = `${label} ${desc}`.toLowerCase()
  if (value.includes('day') || value.includes('window') || value.includes('timeline')) return 'timeline'
  if (value.includes('penalty') || value.includes('compensation') || value.includes('₹')) return 'penalty'
  if (value.includes('consumer') || value.includes('institution') || value.includes('company') || value.includes('regulator')) return 'stakeholder'
  if (value.includes('process') || value.includes('cycle') || value.includes('procedure')) return 'process'
  return 'obligation'
}

function getDocStyle(docKey?: DocKey) {
  return docKey ? DOC_STYLES[docKey] : { fill: '#F8FAFC', stroke: '#475569', textColor: '#0F172A', size: 24, buttonBg: '#F8FAFC', buttonText: '#0F172A' }
}

function getNodeColor(node: GraphNode) {
  if (node.type === 'doc') return getDocStyle(node.docKey).stroke
  return node.entityType ? ENTITY_STYLES[node.entityType].color : '#64748B'
}

function getNodeSize(node: GraphNode) {
  if (node.type === 'doc') return getDocStyle(node.docKey).size
  return node.entityType ? ENTITY_STYLES[node.entityType].size : 12
}

function wrapLabel(label: string) {
  if (label.length <= 12) return [label]
  const words = label.split(' ')
  const mid = Math.ceil(words.length / 2)
  return [words.slice(0, mid).join(' '), words.slice(mid).join(' ')]
}

function dedupeNodes(nodes: GraphNode[]) {
  const seen = new Map<string, GraphNode>()
  nodes.forEach((node) => {
    if (!seen.has(node.id)) seen.set(node.id, node)
  })
  return Array.from(seen.values())
}

function dedupeEdges(edges: GraphEdge[]) {
  const seen = new Map<string, GraphEdge>()
  edges.forEach((edge) => {
    const key = `${edge.source}|${edge.target}|${edge.relation}`
    if (!seen.has(key)) seen.set(key, edge)
  })
  return Array.from(seen.values())
}

function normalizeBackendGraph(payload?: BackendGraphPayload) {
  if (!payload) return { nodes: [] as GraphNode[], links: [] as GraphEdge[] }

  const nodes: GraphNode[] = []
  const links: GraphEdge[] = []
  const idMap = new Map<string, string>()

  for (const rawNode of payload.nodes || []) {
    const originalId = String(rawNode.id || '')
    const label = String(rawNode.title || rawNode.label || rawNode.id || '')
    const layer = rawNode.layer ? String(rawNode.layer) : undefined
    const backendType = rawNode.node_type ? String(rawNode.node_type) : undefined

    if (!originalId || !label || backendType === 'chunk') continue

    if (backendType === 'document') {
      const docKey = inferDocKey(label, layer)
      if (docKey) {
        idMap.set(originalId, `doc_${docKey}`)
      } else {
        const mappedId = `backend_doc_${originalId}`
        idMap.set(originalId, mappedId)
        nodes.push({ id: mappedId, label, type: 'doc', title: label, layer })
      }
      continue
    }

    const mappedId = originalId.startsWith('e_') ? originalId : `backend_${originalId}`
    idMap.set(originalId, mappedId)
    nodes.push({
      id: mappedId,
      label,
      type: 'entity',
      entityType: inferEntityType(label, String(rawNode.desc || '')),
      desc: String(rawNode.desc || rawNode.section_no || rawNode.clause_no || ''),
      section: rawNode.section ? String(rawNode.section) : undefined
    })
  }

  for (const rawEdge of payload.edges || []) {
    const source = idMap.get(String(rawEdge.source || '')) || String(rawEdge.source || '')
    const target = idMap.get(String(rawEdge.target || '')) || String(rawEdge.target || '')
    if (!source || !target) continue
    links.push({
      source,
      target,
      relation: String(rawEdge.relation || 'connected'),
      color: rawEdge.color ? String(rawEdge.color) : '#94A3B8',
      dashed: Boolean(rawEdge.dashed),
      thick: Boolean(rawEdge.thick)
    })
  }

  return { nodes: dedupeNodes(nodes), links: dedupeEdges(links) }
}

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

export function KnowledgeGraphViewer() {
  const navigate = useNavigate()
  const fgRef = useRef<any>(null)
  const [graphPaneRef, graphSize] = useElementSize<HTMLDivElement>()
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [activeDoc, setActiveDoc] = useState<DocKey | null>(null)

  const { data: backendGraph } = useQuery<BackendGraphPayload>({
    queryKey: ['graph-relations'],
    queryFn: async () => {
      const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
      const response = await fetch(`${baseUrl}/graph/relations?limit=500`)
      if (!response.ok) throw new Error('Failed to load graph')
      return response.json()
    },
    refetchInterval: 30000
  })

  const baseGraph = useMemo(() => {
    const backend = normalizeBackendGraph(backendGraph)
    return {
      nodes: dedupeNodes([...HARD_CODED_NODES, ...backend.nodes]),
      links: dedupeEdges([...HARD_CODED_EDGES, ...backend.links])
    }
  }, [backendGraph])

  const filteredGraph = useMemo(() => {
    if (!activeDoc) return baseGraph
    const docId = `doc_${activeDoc}`
    const connectedIds = new Set(
      baseGraph.links
        .filter((link) => link.source === docId || link.target === docId)
        .flatMap((link) => [link.source, link.target])
    )
    const nodes = baseGraph.nodes.filter((node) => node.id === docId || connectedIds.has(node.id))
    const ids = new Set(nodes.map((node) => node.id))
    const links = baseGraph.links.filter((link) => ids.has(link.source) && ids.has(link.target))
    return { nodes, links }
  }, [activeDoc, baseGraph])

  const connectionsByNode = useMemo(() => {
    const nodeMap = new Map(baseGraph.nodes.map((node) => [node.id, node]))
    const map = new Map<string, GraphNode[]>()
    baseGraph.links.forEach((link) => {
      const left = nodeMap.get(link.source)
      const right = nodeMap.get(link.target)
      if (!left || !right) return
      map.set(link.source, [...(map.get(link.source) || []), right])
      map.set(link.target, [...(map.get(link.target) || []), left])
    })
    return map
  }, [baseGraph])

  useEffect(() => {
    if (selectedNode && !filteredGraph.nodes.some((node) => node.id === selectedNode.id)) {
      setSelectedNode(null)
    }
  }, [filteredGraph, selectedNode])

  useEffect(() => {
    const fg = fgRef.current
    if (!fg || !filteredGraph.nodes.length) return

    const docY: Record<DocKey, number> = { rbi: 0.15, cicra05: 0.15, reg: 0.85, rules: 0.85 }
    fg.d3Force(
      'y-layer',
      forceY((node: RenderNode) => {
        if (node.type === 'doc') return (docY[node.docKey || 'rbi'] || 0.5) * graphSize.height
        if (node.entityType === 'stakeholder' || node.entityType === 'timeline') return graphSize.height * 0.5
        if (node.entityType === 'penalty') return graphSize.height * 0.2
        if (node.entityType === 'process') return graphSize.height * 0.75
        if (node.entityType === 'obligation') return graphSize.height * 0.35
        return graphSize.height * 0.5
      }).strength(0.4)
    )
    fg.d3Force(
      'x-layer',
      forceX((node: RenderNode) => {
        if (node.docKey === 'rbi' || node.docKey === 'reg') return graphSize.width * 0.2
        if (node.docKey === 'cicra05' || node.docKey === 'rules') return graphSize.width * 0.8
        return graphSize.width * 0.5
      }).strength(0.3)
    )
    fg.d3Force('charge').strength(-400)
    fg.d3Force('link').distance((link: RenderLink) => (link.thick ? 180 : link.dashed ? 120 : 100))
    fg.d3ReheatSimulation?.()

    const timer = window.setTimeout(() => {
      fg.pauseAnimation?.()
      fg.zoomToFit?.(500, 80)
    }, 3000)
    return () => window.clearTimeout(timer)
  }, [filteredGraph, graphSize])

  return (
    <div className="flex h-[760px] flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
        <span className="text-sm font-medium text-slate-800">
          Entity Knowledge Graph · {filteredGraph.nodes.length} nodes · {filteredGraph.links.length} edges
        </span>
        <div className="flex flex-wrap gap-2">
          {(Object.keys(DOC_STYLES) as DocKey[]).map((docKey) => {
            const style = DOC_STYLES[docKey]
            const label = docKey === 'rbi' ? 'RBI' : docKey === 'cicra05' ? 'CICRA 2005' : docKey === 'reg' ? 'Regulations' : 'Rules'
            return (
              <button
                key={docKey}
                type="button"
                onClick={() => setActiveDoc((prev) => (prev === docKey ? null : docKey))}
                className="rounded-md border px-3 py-1.5 text-sm"
                style={{ background: style.buttonBg, color: style.buttonText, borderColor: activeDoc === docKey ? style.stroke : '#CBD5E1' }}
              >
                {label}
              </button>
            )
          })}
          <button type="button" onClick={() => setActiveDoc(null)} className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700">
            All
          </button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        <div ref={graphPaneRef} className="min-w-0 flex-1 bg-white">
          <ForceGraph2D
            ref={fgRef}
            width={graphSize.width}
            height={graphSize.height}
            graphData={{ nodes: filteredGraph.nodes, links: filteredGraph.links }}
            nodeId="id"
            backgroundColor="#FFFFFF"
            autoPauseRedraw={false}
            cooldownTicks={0}
            onNodeHover={(node) => setHoveredNode((node as GraphNode | null) ?? null)}
            onNodeClick={(node) => setSelectedNode(node as GraphNode)}
            nodeCanvasObjectMode={() => 'replace'}
            linkCanvasObjectMode={() => 'replace'}
            nodeCanvasObject={(nodeObj, ctx, globalScale) => {
              const node = nodeObj as RenderNode
              const color = getNodeColor(node)
              const radius = getNodeSize(node) / globalScale
              const hover = hoveredNode?.id === node.id

              if (hover) {
                ctx.beginPath()
                ctx.arc(node.x || 0, node.y || 0, radius * 1.5, 0, 2 * Math.PI)
                ctx.fillStyle = `${color}30`
                ctx.fill()
              }

              ctx.beginPath()
              ctx.arc(node.x || 0, node.y || 0, radius, 0, 2 * Math.PI)
              if (node.type === 'doc') {
                ctx.fillStyle = getDocStyle(node.docKey).fill
                ctx.fill()
                ctx.strokeStyle = color
                ctx.lineWidth = hover ? 2 / globalScale : 1.5 / globalScale
                ctx.stroke()
                ctx.fillStyle = color
                ctx.font = `bold ${10 / globalScale}px sans-serif`
                ctx.textAlign = 'center'
                ctx.fillText(`${node.chunks || 0}ch`, node.x || 0, (node.y || 0) + radius + 14 / globalScale)
              } else {
                ctx.fillStyle = color
                ctx.fill()
                if (hover) {
                  ctx.strokeStyle = '#FFFFFF'
                  ctx.lineWidth = 1.5 / globalScale
                  ctx.stroke()
                }
              }

              ctx.font = `500 ${Math.max(6, 10 / globalScale)}px sans-serif`
              ctx.textAlign = 'center'
              ctx.textBaseline = 'middle'
              ctx.fillStyle = node.type === 'doc' ? getDocStyle(node.docKey).textColor : '#FFFFFF'
              const lines = wrapLabel(node.label)
              if (lines.length > 1) {
                ctx.fillText(lines[0], node.x || 0, (node.y || 0) - 5 / globalScale)
                ctx.fillText(lines[1], node.x || 0, (node.y || 0) + 5 / globalScale)
              } else {
                ctx.fillText(lines[0], node.x || 0, node.y || 0)
              }
            }}
            linkCanvasObject={(linkObj, ctx, globalScale) => {
              const link = linkObj as RenderLink
              const source = link.source as RenderNode
              const target = link.target as RenderNode
              const color = link.color || '#888780'
              ctx.strokeStyle = color
              ctx.lineWidth = link.thick ? 2 / globalScale : 1 / globalScale
              ctx.globalAlpha = 0.6
              if (link.dashed) ctx.setLineDash([5 / globalScale, 3 / globalScale])
              ctx.beginPath()
              ctx.moveTo(source.x || 0, source.y || 0)
              ctx.lineTo(target.x || 0, target.y || 0)
              ctx.stroke()
              ctx.setLineDash([])
              ctx.globalAlpha = 1
              if (globalScale > 1.5) {
                ctx.font = `${8 / globalScale}px sans-serif`
                ctx.fillStyle = color
                ctx.textAlign = 'center'
                ctx.fillText(link.relation, ((source.x || 0) + (target.x || 0)) / 2, (((source.y || 0) + (target.y || 0)) / 2) - 5 / globalScale)
              }
            }}
          />
        </div>

        {selectedNode && (
          <div className="w-[220px] border-l border-slate-200 bg-slate-50 p-4">
            <h3 className="text-sm font-semibold" style={{ color: getNodeColor(selectedNode) }}>{selectedNode.label}</h3>
            <p className="mt-2 text-xs leading-5 text-slate-600">{selectedNode.desc || 'No additional description available.'}</p>
            <div className="mt-2 text-[11px] text-slate-500">Found in {selectedNode.sources?.length || 1} document(s)</div>
            <div className="mt-4">
              <strong className="text-[11px] text-slate-700">Connected to:</strong>
              <div className="mt-2 space-y-1">
                {(connectionsByNode.get(selectedNode.id) || []).slice(0, 8).map((node) => (
                  <div key={node.id} className="text-[11px] text-slate-600">→ {node.label}</div>
                ))}
              </div>
            </div>
            <button
              type="button"
              onClick={() => navigate(`/query?q=${encodeURIComponent(`Explain ${selectedNode.label}`)}`)}
              className="mt-4 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700"
            >
              Query about this ↗
            </button>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-4 border-t border-slate-200 px-4 py-2 text-[11px] text-slate-500">
        <span>Solid line = defines</span>
        <span>Dashed line = cross-doc link</span>
        <span>Thick line = parent → child doc</span>
        <span className="ml-auto">Hover for details · Click to explore · Scroll to zoom</span>
      </div>
    </div>
  )
}
