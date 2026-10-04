import { create } from 'zustand';

export type ConceptStatus = 'mastered' | 'developing' | 'needs_practice' | 'not_assessed';

export interface Concept {
  id: string;
  name: string;
  status: ConceptStatus;
  score: number;
}

export interface ConceptLink {
  source: string;
  target: string;
}

export interface Misconception {
  id: string;
  conceptId: string;
  description: string;
  count: number;
}

export interface Message {
  id: string;
  role: 'user' | 'tutor';
  content: string;
  hintLevel?: number;
  isStep?: boolean;
}

export type TutorMode = 'homework' | 'exam practice' | 'explore';
export type ProblemType = 'closed_form' | 'proof_derivation' | 'conceptual' | 'open_ended' | 'code' | 'mcq';

interface TutorState {
  sessionId: string | null;
  problemText: string | null;
  transferProblem: string | null;
  learningObjective: string | null;
  mode: TutorMode;
  problemType: ProblemType;
  messages: Message[];
  concepts: Concept[];
  conceptLinks: ConceptLink[];
  misconceptions: Misconception[];
  isCompleted: boolean;
  helpDependence: number;
  rewardPoints: number;
  completionKind: "verified" | "assisted" | "learning_goal" | null;
  setSession: (id: string, text: string, concepts: Concept[], mode?: TutorMode, problemType?: ProblemType, transferProblem?: string | null, conceptLinks?: ConceptLink[], learningObjective?: string | null) => void;
  restoreSession: (id: string, text: string, concepts: Concept[], misconceptions: Misconception[], mode: TutorMode, problemType: ProblemType, messages: Message[], rewardPoints?: number, transferProblem?: string | null, conceptLinks?: ConceptLink[], learningObjective?: string | null) => void;
  setMode: (mode: TutorMode) => void;
  addMessage: (msg: Omit<Message, 'id'>) => void;
  updateConcept: (id: string, status: ConceptStatus, scoreDelta: number) => void;
  addMisconception: (conceptId: string, description: string) => void;
  incrementHelpDependence: () => void;
  setRewardPoints: (points: number) => void;
  completeSession: (kind?: "verified" | "assisted" | "learning_goal") => void;
  reset: () => void;
}

export const useTutorStore = create<TutorState>((set) => ({
  sessionId: null,
  problemText: null,
  transferProblem: null,
  learningObjective: null,
  mode: 'explore',
  problemType: 'closed_form',
  messages: [],
  concepts: [],
  conceptLinks: [],
  misconceptions: [],
  isCompleted: false,
  helpDependence: 0,
  rewardPoints: 0,
  completionKind: null,
  setMode: (mode) => set({ mode }),

  setSession: (id, text, concepts, mode = 'explore', problemType = 'closed_form', transferProblem = null, conceptLinks = [], learningObjective = null) => set({
    sessionId: id,
    problemText: text,
    transferProblem,
    learningObjective,
    mode,
    problemType,
    concepts,
    conceptLinks,
    misconceptions: [],
    messages: [
      { 
        id: '1', 
        role: 'tutor', 
        content: problemType === 'code' 
          ? 'How would you start solving this programming problem?' 
          : problemType === 'open_ended' 
            ? 'What are your initial thoughts on this topic?' 
            : 'What would you try first?', 
        hintLevel: 0 
      }
    ],
    isCompleted: false,
    helpDependence: 0,
    rewardPoints: 0,
    completionKind: null,
  }),

  restoreSession: (id, text, concepts, misconceptions, mode, problemType, messages, rewardPoints = 0, transferProblem = null, conceptLinks = [], learningObjective = null) => set({
    sessionId: id,
    problemText: text,
    transferProblem,
    learningObjective,
    mode,
    problemType,
    concepts,
    conceptLinks,
    misconceptions,
    messages: messages[0]?.role !== "tutor"
      ? [{
          id: "welcome",
          role: "tutor",
          content: problemType === "code"
            ? "How would you start solving this programming problem?"
            : problemType === "open_ended"
              ? "What are your initial thoughts on this topic?"
              : "What would you try first?",
          hintLevel: 0,
        }, ...messages]
      : messages,
    isCompleted: false,
    rewardPoints,
    completionKind: null,
    helpDependence: messages.filter(message => message.role === "tutor" && (message.hintLevel ?? 0) > 0).length,
  }),

  addMessage: (msg) => set((state) => ({
    messages: [...state.messages, { ...msg, id: Math.random().toString(36).substring(7) }]
  })),

  updateConcept: (id, status, scoreDelta) => set((state) => ({
    concepts: state.concepts.map(c => {
      if (c.id === id) {
        const newScore = Math.max(0, Math.min(1, c.score + scoreDelta));
        return { ...c, status, score: newScore };
      }
      return c;
    })
  })),

  addMisconception: (conceptId, description) => set((state) => {
    const existing = state.misconceptions.find(m => m.conceptId === conceptId && m.description === description);
    if (existing) {
      return {
        misconceptions: state.misconceptions.map(m => 
          m.id === existing.id ? { ...m, count: m.count + 1 } : m
        )
      };
    }
    return {
      misconceptions: [...state.misconceptions, { id: Math.random().toString(), conceptId, description, count: 1 }]
    };
  }),

  incrementHelpDependence: () => set((state) => ({ helpDependence: state.helpDependence + 1 })),
  setRewardPoints: (points) => set({ rewardPoints: points }),

  completeSession: (kind = "verified") => set({ isCompleted: true, completionKind: kind }),
  
  reset: () => set({ sessionId: null, problemText: null, transferProblem: null, learningObjective: null, messages: [], concepts: [], conceptLinks: [], isCompleted: false, rewardPoints: 0, completionKind: null })
}));
