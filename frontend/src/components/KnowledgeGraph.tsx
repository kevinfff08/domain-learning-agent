import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import type { ConceptNode, GraphEdge } from '../types'

interface Props {
  nodes: ConceptNode[]
  edges: GraphEdge[]
  onNodeClick?: (conceptId: string) => void
}

interface SimNode extends d3.SimulationNodeDatum {
  id: string
  name: string
  status: string
  mastery_level: number
}

interface SimLink extends d3.SimulationLinkDatum<SimNode> {
  relationship: string
}

const statusColor: Record<string, string> = {
  pending: '#94a3b8',
  in_progress: '#eab308',
  completed: '#22c55e',
}

export default function KnowledgeGraph({ nodes, edges, onNodeClick }: Props) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const width = svgRef.current.clientWidth
    const height = svgRef.current.clientHeight

    // Arrow marker
    svg
      .append('defs')
      .append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 25)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#94a3b8')

    const simNodes: SimNode[] = nodes.map((n) => ({
      id: n.id,
      name: n.name,
      status: n.status,
      mastery_level: n.mastery_level,
    }))

    const nodeById = new Map(simNodes.map((n) => [n.id, n]))

    const simLinks: SimLink[] = edges
      .filter((e) => nodeById.has(e.source) && nodeById.has(e.target))
      .map((e) => ({
        source: e.source,
        target: e.target,
        relationship: e.relationship,
      }))

    const simulation = d3
      .forceSimulation(simNodes)
      .force(
        'link',
        d3
          .forceLink<SimNode, SimLink>(simLinks)
          .id((d) => d.id)
          .distance(120)
      )
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide(40))

    const g = svg.append('g')

    // Zoom
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 3])
      .on('zoom', (e) => {
        g.attr('transform', e.transform)
      })

    svg.call(zoom)

    // Links
    const link = g
      .append('g')
      .selectAll('line')
      .data(simLinks)
      .join('line')
      .attr('stroke', '#cbd5e1')
      .attr('stroke-width', 1.5)
      .attr('marker-end', 'url(#arrowhead)')

    // Node groups
    const node = g
      .append('g')
      .selectAll<SVGGElement, SimNode>('g')
      .data(simNodes)
      .join('g')
      .style('cursor', 'pointer')
      .on('click', (_, d) => {
        onNodeClick?.(d.id)
      })
      .call(
        d3
          .drag<SVGGElement, SimNode>()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart()
            d.fx = d.x
            d.fy = d.y
          })
          .on('drag', (event, d) => {
            d.fx = event.x
            d.fy = event.y
          })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0)
            d.fx = null
            d.fy = null
          })
      )

    // Node circles
    node
      .append('circle')
      .attr('r', 18)
      .attr('fill', (d) => statusColor[d.status] || '#94a3b8')
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)

    // Node labels
    node
      .append('text')
      .text((d) => d.name)
      .attr('text-anchor', 'middle')
      .attr('dy', 32)
      .attr('font-size', '11px')
      .attr('fill', '#334155')
      .attr('font-weight', '500')

    simulation.on('tick', () => {
      link
        .attr('x1', (d) => (d.source as SimNode).x!)
        .attr('y1', (d) => (d.source as SimNode).y!)
        .attr('x2', (d) => (d.target as SimNode).x!)
        .attr('y2', (d) => (d.target as SimNode).y!)

      node.attr('transform', (d) => `translate(${d.x},${d.y})`)
    })

    return () => {
      simulation.stop()
    }
  }, [nodes, edges, onNodeClick])

  return (
    <svg
      ref={svgRef}
      className="w-full h-full bg-white rounded-lg border border-slate-200"
      style={{ minHeight: '500px' }}
    />
  )
}
