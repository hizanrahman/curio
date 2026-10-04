import { useEffect, useState } from 'react';
import { createPortal } from "react-dom";
import {
  ReactFlow,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  Position,
  type Node,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useTutorStore } from '@/store/useTutorStore';
import { List, Maximize2, Network, X } from "lucide-react";
import { ConceptStatusIcon, StatusPill } from "@/components/theme/StatusPill";
import { useRef } from "react";

const statusColors = {
  mastered: "var(--mint)",
  developing: "var(--yellow)",
  needs_practice: "var(--coral)",
  not_assessed: "var(--status-neutral)",
};

import dagre from 'dagre';
import { useMemo } from 'react';

const nodeWidth = 170;
const nodeHeight = 76;

const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'TB') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: direction });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.targetPosition = Position.Top;
    node.sourcePosition = Position.Bottom;
    // We are shifting the dagre node position (anchor=center center) to the top left
    // so it matches the React Flow node anchor point (top left).
    node.position = {
      x: nodeWithPosition.x - nodeWidth / 2,
      y: nodeWithPosition.y - nodeHeight / 2,
    };

    return node;
  });

  return { nodes, edges };
};

export function ConceptMap() {
  const concepts = useTutorStore(state => state.concepts);
  const conceptLinks = useTutorStore(state => state.conceptLinks);
  const [isListView, setIsListView] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const expandButtonRef = useRef<HTMLButtonElement>(null);
  
  const { initialNodes, initialEdges } = useMemo(() => {
    const sourceNodes = concepts.map(concept => ({
      id: concept.id,
      data: { label: concept.name, status: concept.status },
    }));

    const conceptIds = new Set(sourceNodes.map(node => node.id));
    const dynamicEdges: Edge[] = conceptLinks
      .filter(link => conceptIds.has(link.source) && conceptIds.has(link.target))
      .map(link => ({
        id: `e${link.source}-${link.target}`,
        source: link.source,
        target: link.target,
        animated: true,
        label: "prerequisite for",
        labelStyle: { fill: "var(--muted)", fontSize: 10, fontWeight: 600 },
        labelBgStyle: { fill: "var(--surface)", fillOpacity: 0.9 },
        markerEnd: { type: MarkerType.ArrowClosed },
      }));

    const styledNodes: Node[] = sourceNodes.map(n => ({
      id: n.id,
      data: {
        label: (
          <span className="flex flex-col items-center gap-1">
            <span className="font-bold">{n.data.label}</span>
            <span className="flex items-center gap-1 text-[10px] font-semibold capitalize text-ink/75">
              <ConceptStatusIcon status={n.data.status as "mastered" | "developing" | "needs_practice" | "not_assessed"} className="h-3 w-3" />
              {n.data.status === "needs_practice" ? "Needs practice" : n.data.status.replace("_", " ")}
            </span>
          </span>
        ),
      },
      position: { x: 0, y: 0 },
      style: {
        background: "var(--surface)",
        border: `2px solid ${statusColors[n.data.status as keyof typeof statusColors]}`,
        borderRadius: "12px",
        padding: "10px",
        fontSize: "12px",
        width: nodeWidth,
        textAlign: "center" as const,
        color: "var(--ink)",
        fontWeight: 500,
        boxShadow: "var(--shadow-hard)"
      }
    }));

    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(styledNodes, dynamicEdges);
    
    return { initialNodes: layoutedNodes, initialEdges: layoutedEdges };
  }, [concepts, conceptLinks]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  useEffect(() => {
    if (!isExpanded) return;
    const previousOverflow = document.body.style.overflow;
    const expandButton = expandButtonRef.current;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsExpanded(false);
    };
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", handleKeyDown);
    closeButtonRef.current?.focus();
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
      expandButton?.focus();
    };
  }, [isExpanded]);

  const renderMap = () => (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      fitView
      attributionPosition="bottom-right"
    >
      <Background color="var(--lilac)" gap={16} />
    </ReactFlow>
  );

  return (
    <div className="flex h-full w-full flex-col">
      <div className="flex justify-end gap-2 p-1">
        <button
          type="button"
          onClick={() => setIsListView(current => !current)}
          aria-label={isListView ? "Show concept map" : "Show concept list"}
          aria-pressed={isListView}
          className="inline-flex min-h-9 items-center gap-2 rounded-lg border-2 border-ink bg-surface px-3 text-xs font-bold"
        >
          {isListView ? <Network aria-hidden="true" className="h-4 w-4" /> : <List aria-hidden="true" className="h-4 w-4" />}
          {isListView ? "Map view" : "List view"}
        </button>
        <button
          ref={expandButtonRef}
          type="button"
          onClick={() => setIsExpanded(true)}
          disabled={concepts.length === 0}
          aria-label="Expand learning map"
          className="inline-flex min-h-9 items-center gap-2 rounded-lg border-2 border-ink bg-surface px-3 text-xs font-bold disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Maximize2 aria-hidden="true" className="h-4 w-4" />
          Expand
        </button>
      </div>
      {concepts.length === 0 ? (
        <div className="grid flex-1 place-items-center p-5 text-center">
          <p className="max-w-xs text-sm leading-relaxed text-muted-foreground">
            No question-specific learning map is available for this session.
          </p>
        </div>
      ) : isListView ? (
        <ul className="soft-scrollbar flex-1 space-y-2 overflow-auto p-3">
          {concepts.map(concept => (
            <li key={concept.id} className="flex items-center justify-between gap-2 rounded-xl border-2 border-ink bg-surface p-3">
              <span className="text-sm font-bold">{concept.name}</span>
              <StatusPill status={concept.status} />
            </li>
          ))}
        </ul>
      ) : (
        <div className="relative min-h-0 flex-1">
          {renderMap()}
        </div>
      )}
      {isExpanded && concepts.length > 0 && createPortal(
        <div
          className="fixed inset-0 z-[100] grid place-items-center bg-ink/60 p-3 sm:p-8"
          onMouseDown={event => {
            if (event.target === event.currentTarget) setIsExpanded(false);
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="expanded-learning-map-title"
            className="flex h-[min(90dvh,900px)] w-full max-w-7xl flex-col overflow-hidden rounded-2xl border-2 border-ink bg-surface shadow-[var(--shadow-hard)]"
          >
            <header className="flex shrink-0 items-center justify-between gap-4 border-b-2 border-ink px-4 py-3 sm:px-6">
              <div>
                <h2 id="expanded-learning-map-title" className="font-display text-lg font-extrabold sm:text-xl">
                  Learning map
                </h2>
                <p className="text-xs text-muted-foreground">Follow prerequisites toward the key idea</p>
              </div>
              <button
                ref={closeButtonRef}
                type="button"
                onClick={() => setIsExpanded(false)}
                aria-label="Close expanded learning map"
                className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border-2 border-ink bg-surface"
              >
                <X aria-hidden="true" className="h-5 w-5" />
              </button>
            </header>
            {isListView ? (
              <ul className="soft-scrollbar flex-1 space-y-3 overflow-auto p-4 sm:p-6">
                {concepts.map(concept => (
                  <li key={concept.id} className="flex items-center justify-between gap-3 rounded-xl border-2 border-ink bg-surface p-4">
                    <span className="text-sm font-bold sm:text-base">{concept.name}</span>
                    <StatusPill status={concept.status} />
                  </li>
                ))}
              </ul>
            ) : (
              <div className="min-h-0 flex-1">
                {renderMap()}
              </div>
            )}
          </section>
        </div>,
        document.body,
      )}
    </div>
  );
}
