# Frontend (Coming in Milestone 12)

This folder will contain the React + TypeScript + Tailwind CSS recruiter and
candidate dashboards.

Planned structure:
```
frontend/
├── src/
│   ├── components/     # Reusable UI components
│   ├── pages/           # Route-level pages (dashboard, candidate view, etc.)
│   ├── hooks/           # Custom React hooks
│   ├── services/        # API client layer (typed fetch wrappers)
│   ├── types/            # Shared TypeScript types/interfaces
│   └── store/            # State management
├── package.json
└── vite.config.ts
```

Left intentionally empty until the backend API surface (Milestones 2–11) is
stable enough to build against — building the UI against a moving API
contract leads to constant rework, so this is a deliberate sequencing choice,
not an oversight.
