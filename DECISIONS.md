# Decisions

1. **Frontend Framework**: The README specifies Next.js, but the prompt explicitly requested a Vite + React 18 + TS setup for the tech stack with React Router. To align with the user's specific prompt instructions, I chose Vite SPA instead of Next.js SSR/App Router. I will adapt the routing (e.g., `/`, `/learn`, `/session/:id`) to React Router.
2. **Styling**: Tailwind CSS with CSS Variables for tokens, combined with shadcn/ui.
3. **Data Fetching/Mocking**: Since this is an MVP build focused on the frontend initially and we don't have the real backend deployed yet, I will mock the backend logic using local state or MSW if necessary. Given the timeframe, I will build out the UI with local mock state/Zustand first to prove the loop, mimicking the expected AI behavior.
4. **Graph Library**: Using `reactflow` for the lightweight concept map.
5. **State Management**: Using `zustand` to manage the session state globally and cleanly.
6. **Backend Evolution Context**: Since the Python backend was not fully scaffolded in the MVP phase (only the frontend was), the "refactoring" will involve scaffolding the baseline FastAPI backend files at the same time as implementing the new Phase 1-3 generalized architecture.
7. **Verifiers & Guard Execution**: The Python backend relies on `sympy` for mathematical equivalence checks. 

### Assumptions & Known Limitations
1. **Mock AI Engine**: The backend `ai_tutor.py` pipeline is built, but we are running a mocked setTimeout loop in the frontend `SessionPage.tsx` to simulate the interaction and prove out the React Flow, UI elements, and pedagogy behaviors without requiring a live OpenAI key for every UI test.
2. **Code Execution Sandbox**: True sandboxing for Python code (Phase 1 rule 5) is complex on client-side; a full solution would require Pyodide (client-side) or a secure Dockerized runner on the backend. For the MVP, we assume the backend handles it via an isolated service and the frontend displays the `CodeEditor`.
3. **Multi-file / Multi-problem Upload**: The PDF / image extraction implies OCR. The MVP assumes this is handled by a standard OpenAI Vision API call behind the `problem_analyzer.py` service.
4. **i18n**: The `i18n.ts` dictionary was scaffolded, but for simplicity of the MVP flow, the app currently defaults to English. Integrating it fully across every component would require adding an i18n context provider.

## Soft Pop UI redesign decisions (2026-10-03)

This pass applies the Soft Pop visual system to the existing Vite/React app. It intentionally leaves backend code, API request/response shapes, route definitions, and learning-domain state untouched. UI-only interaction state is limited to mobile workspace tabs, drag highlighting, clipboard paste, and the demo animation.

### Landing

- **Before:** A centered headline and one action, with no product explanation.
- **After:** A responsive hero with the requested learning promise, animated local demo conversation, subject chips, four how-it-works cards, a bento feature grid, Typical AI comparison, strong next action, and privacy/terms/support guidance.
- The footer states that uploaded images/PDFs are not stored as uploads. Contact is directed to the account/school administrator because no support address or contact route exists in the app.

### Learn / upload

- **Before:** File picker, problem textarea, and start button in a plain form.
- **After:** Drag-and-drop zone, mobile camera input, clipboard text action, extraction loading state, reviewed extracted-text card, math rendering, and an explicit start action.
- The existing extraction endpoint does not return a subject classification, problem-type analysis, or confidence score. The review therefore labels the subject as unclassified and asks the student to review the extraction rather than inventing a confidence value. Session mode and request behavior remain unchanged.

### Session workspace

- **Before:** Chat and problem text shared the left column; the concept map occupied a right sidebar.
- **After:** Desktop has a dedicated problem/steps rail, a centered chat, and a concept-map rail. Mobile uses the requested four-tab navigation with Tutor selected initially, a safe-area-aware composer, markdown/math rendering, status badges, hint levels, and an in-flight tutor indicator.
- Concept status always uses a symbol, text label, and color; the map has an accessible list view. The displayed independence indicator is explicitly a hint-frequency estimate derived from existing in-session counts, not a grade or backend mastery score.
- Learning maps are now planned from the exact session question: the saved map includes a learning objective, prerequisite concepts, and prerequisite-to-target links, and that same concept list anchors tutor mastery updates. Invalid/missing map output fails visibly rather than substituting generic algebra nodes or fabricated linear links. Session restoration and transfer practice carry the map metadata through to the workspace.
- The map can be expanded into a dismissible full-screen view. Concept progress advances only on distinct student-evidence quotes that match a planned concept; mastery requires two distinct demonstrated turns, while a supported misconception returns a concept to needs-practice. The tutor prompt follows the remaining prerequisite path and should stop once its target objective is demonstrated.
- A New problem action lets a learner leave an active conversation at any point; saved work remains an in-progress session in history rather than being mislabeled as completed.
- No attach-image-to-chat or reveal-solution UI was added: the current client has no message attachment or solution-reveal API/state to present without changing behavior.

### Summary and progress

- **Before:** Plain completion totals, concepts, misconceptions, and transfer action.
- **After:** A verified-solve celebration, hint-frequency ring, compact stats, status pills, soft misconception cards, and a themed transfer-practice card.
- No elapsed-time value, trend chart, or streak is fabricated: the current frontend data contract does not provide those progress measurements. The existing Dashboard history is restyled with honest session counts and empty/loading/error states; there is no separate progress route.

### Authentication, account, and shared shell

- **Before:** Default form controls and a minimal navigation bar.
- **After:** Consistent token-based cards, focus rings, controls, mobile navigation, and themed feedback across sign-in, account deletion, and session history.
- A theme toggle was not added because Soft Pop is light-only for v1. Routes remain unchanged, so no new 404 route or error-boundary behavior was introduced.

### Validation notes

- Production TypeScript/Vite build and frontend lint are the frontend validation gates.
- The project has no frontend unit/snapshot test runner configured. Backend session and Socratic prompt tests validate map generation wiring, persistence/restore payloads, and prerequisite graph checks.
- Lighthouse scores require a deployed/served production build and browser audit; they are not asserted from compilation alone.

## Daily challenge removal

- Daily challenge generation, timezone-aware streaks, share cards, their API/UI, and their profile fields were removed from the product.
- Migration 005 is retained as historical migration history. Migration 006 removes its retired feature schema while ensuring current completion/personality fields exist; existing databases that applied 005 and fresh installs should apply 006.
- Independent and assisted completion classifications remain part of normal session completion and rewards. They no longer update a streak.
- Tutor personality remains a profile preference and tone-only prompt suffix; answer guard, verifier, hint logic, reveal policy, and mastery behavior are unchanged.
