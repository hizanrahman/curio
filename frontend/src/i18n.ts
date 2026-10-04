export const i18n = {
  en: {
    landing: {
      title: "Master any subject.",
      subtitle: "Upload any academic problem (math, physics, chemistry, biology, CS, humanities) and work through it with an AI tutor that guides your reasoning instead of doing the work for you.",
      cta: "Start Learning",
    },
    session: {
      workspaceTitle: "Session Workspace",
      learningProfile: "Learning Profile",
      conceptMap: "Concept Map",
      sessionComplete: "Session Complete",
      helpDependence: "Help Dependence",
      hints: "Hints",
    }
  },
  es: {
    landing: {
      title: "Domina cualquier tema.",
      subtitle: "Sube cualquier problema académico (matemáticas, física, química, biología, informática, humanidades) y resuélvelo con un tutor de IA que guía tu razonamiento en lugar de hacer el trabajo por ti.",
      cta: "Empezar a aprender",
    },
    session: {
      workspaceTitle: "Espacio de trabajo",
      learningProfile: "Perfil de aprendizaje",
      conceptMap: "Mapa de conceptos",
      sessionComplete: "Sesión completada",
      helpDependence: "Dependencia de ayuda",
      hints: "Pistas",
    }
  }
};

export type Language = keyof typeof i18n;
