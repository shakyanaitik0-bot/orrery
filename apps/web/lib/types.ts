export type Relation = "prerequisite" | "related" | "confused_with";

export interface SceneNode {
  id: string;
  slug: string;
  title: string;
  summary: string | null;
  subject: string;
  position: { x: number; y: number; z: number };
  depth: number;
  mastery: number;
  mastered: boolean;
  locked: boolean;
  blockedBy: string[];
}

export interface SceneEdge {
  source: string;
  target: string;
  relation: Relation;
  weight: number;
}

export interface Scene {
  nodes: SceneNode[];
  edges: SceneEdge[];
  layers: number;
  layerHeight?: number;
  layerRadius?: number[];
  masteryThreshold: number;
  subject: { slug: string; title: string; accent: string };
}

export interface AnswerResult {
  conceptId: string;
  mastery: number;
  observations: number;
  mastered: boolean;
  threshold: number;
}
