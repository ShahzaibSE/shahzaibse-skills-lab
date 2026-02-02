---
name: create-nextjs-project
description: |
  Guides professional engineers in creating enterprise-grade, production-ready
  Next.js projects. Use when users want to scaffold a new Next.js project,
  need enterprise architecture guidance, or want recommendations for
  Tailwind CSS and shadcn/ui integration. Leverages fetch-library-docs for
  authoritative documentation and vercel-react-best-practices for
  performance guidance.
---

# Create Next.js Project Skill

## What This Skill Does

- Guides engineers in creating enterprise-grade, production-ready Next.js projects
- Provides project structure recommendations for scalable, team-friendly codebases
- Offers rendering strategy guidance (Server Components vs Client Components)
- Recommends Tailwind CSS configuration aligned with App Router
- Advises on shadcn/ui integration conventions
- Suggests testing framework setup (Vitest/Jest)
- Provides conceptual state management patterns (server-first approach)
- Delivers configuration and validation checklists

## What This Skill Does NOT Do

- Execute CLI commands or generate full project code
- Provide deployment, Docker, CI/CD, or Kubernetes guidance
- Generate UI component code
- Select, configure, or implement state management libraries
- Select, configure, or implement async data fetching libraries
- Provide backend API implementation details

---

## Workflow Overview

### How This Skill Operates

1. **Gather Requirements**: Ask minimal clarifying questions (project name, specific needs)
2. **Apply Defaults**: Use enterprise-grade defaults (App Router, TypeScript, Tailwind, shadcn/ui)
3. **Reference Documentation**: Delegate to `fetch-library-docs` for authoritative Next.js, Tailwind, and shadcn documentation
4. **Apply Performance Guidance**: Reference `vercel-react-best-practices` for rendering and performance decisions
5. **Deliver Structured Output**: Provide guidance following the Output Contract Template

### Supporting Skills (Reference Only)

- **fetch-library-docs**: Use for authoritative documentation on Next.js, Tailwind CSS, shadcn/ui
- **vercel-react-best-practices**: Use for rendering strategy and performance optimization guidance

---

## Clarifying Questions

Ask only these minimal questions before providing guidance:

1. **Project name**: What is the name of your project?
2. **Specific requirements**: Do you have any specific requirements beyond the defaults (App Router, TypeScript, Tailwind CSS, shadcn/ui)?

### Default Assumptions (if not specified)

- **Router**: App Router (not Pages Router)
- **Language**: TypeScript (not JavaScript)
- **Styling**: Tailwind CSS (required)
- **UI Components**: shadcn/ui (required)
- **Testing**: Vitest (preferred) or Jest
- **Posture**: Enterprise-grade, long-lived, team-scalable

---

## Output Contract Template

All guidance MUST follow this exact structure:

### 1. Assumptions
List all assumptions made based on defaults and user input.

### 2. Project Intent
Describe the enterprise-grade baseline and project goals.

### 3. Project Creation Steps
Ordered steps to create the project using `create-next-app` with appropriate flags.

### 4. Recommended Structure
Directory layout following App Router conventions.

### 5. Rendering & Performance Strategy
Server Components vs Client Components guidance with performance considerations.

### 6. State Management Patterns (Conceptual)
Server-first architecture emphasis with conceptual client state guidance.

### 7. Styling & UI System
Tailwind CSS and shadcn/ui integration approach.

### 8. Testing Strategy
Testing framework setup and organization conventions.

### 9. Configuration Checklist
TypeScript, ESLint, Prettier, environment variables, Next.js config.

### 10. Validation Checklist
Build, type checking, linting, dev server, tests.

### 11. Out-of-Scope Reminder
Explicit reminder of what this guidance does NOT cover.

---

## Enterprise-Grade Project Structure

```
project-root/
├── src/
│   ├── app/                    # App Router pages and layouts
│   │   ├── (auth)/             # Route groups for authentication
│   │   ├── (dashboard)/        # Route groups for dashboard
│   │   ├── api/                # API routes
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Home page
│   │   ├── loading.tsx         # Loading UI
│   │   ├── error.tsx           # Error UI
│   │   ├── not-found.tsx       # 404 UI
│   │   └── global-error.tsx    # Global error boundary
│   │
│   ├── components/             # Shared components
│   │   ├── ui/                 # shadcn/ui components (auto-generated)
│   │   ├── forms/              # Form components
│   │   ├── layouts/            # Layout components
│   │   └── shared/             # Other shared components
│   │
│   ├── lib/                    # Utility functions and shared logic
│   │   ├── utils.ts            # General utilities (includes cn() for shadcn)
│   │   ├── validations/        # Zod schemas and validation logic
│   │   └── constants.ts        # App-wide constants
│   │
│   ├── hooks/                  # Custom React hooks
│   │
│   ├── types/                  # TypeScript type definitions
│   │   ├── index.ts            # Shared types
│   │   └── api.ts              # API-related types
│   │
│   ├── styles/                 # Global styles
│   │   └── globals.css         # Tailwind directives and global CSS
│   │
│   └── config/                 # Configuration files
│       ├── site.ts             # Site metadata and config
│       └── navigation.ts       # Navigation configuration
│
├── public/                     # Static assets
│   ├── images/
│   └── fonts/
│
├── tests/                      # Test files (mirrors src structure)
│   ├── components/
│   ├── lib/
│   └── setup.ts                # Test setup file
│
├── .env.example                # Environment variable template
├── .env.local                  # Local environment variables (gitignored)
├── components.json             # shadcn/ui configuration
├── tailwind.config.ts          # Tailwind configuration
├── tsconfig.json               # TypeScript configuration
├── next.config.ts              # Next.js configuration
├── vitest.config.ts            # Vitest configuration (if using Vitest)
└── package.json
```

### Key Conventions

- **Route Groups**: Use `(groupName)` for logical grouping without affecting URL structure
- **Colocation**: Keep page-specific components near their pages when not shared
- **shadcn/ui Location**: Components go in `src/components/ui/` by default
- **Utils Location**: The `cn()` utility for className merging lives in `src/lib/utils.ts`

---

## Rendering Strategy Guidance

### Server Components (Default)

Use Server Components for:
- Data fetching from databases or APIs
- Accessing backend resources directly
- Keeping sensitive information on the server (tokens, API keys)
- Large dependencies that would increase client bundle
- SEO-critical content

### Client Components

Use Client Components (`"use client"`) only when you need:
- Interactivity (onClick, onChange, etc.)
- Browser APIs (localStorage, window, etc.)
- React hooks that use state or effects (useState, useEffect, useReducer)
- Custom hooks that depend on state or effects

### Performance Principles

Reference `vercel-react-best-practices` for detailed guidance on:
- Component composition patterns
- Minimizing client-side JavaScript
- Proper use of Suspense boundaries
- Streaming and progressive rendering
- Bundle optimization strategies

### Key Rules

1. **Start with Server Components** - only add `"use client"` when necessary
2. **Push client boundaries down** - keep client components as leaf nodes
3. **Compose Server and Client** - pass Server Components as children to Client Components
4. **Avoid unnecessary client-side data fetching** - prefer server-side data loading

---

## Tailwind CSS Configuration

### Setup Aligned with App Router

The `globals.css` file should contain:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### Theme Customization Approach

Configure `tailwind.config.ts` for:
- Custom color palette aligned with design system
- Typography scale
- Spacing scale extensions
- Custom breakpoints if needed
- Animation utilities

### Performance Considerations

- Use Tailwind's JIT mode (default in v3+)
- Configure `content` paths correctly to enable tree-shaking
- Avoid `@apply` in large stylesheets (prefer utility classes directly)
- Use CSS variables for theme values that shadcn/ui can reference

### shadcn/ui Theme Integration

shadcn/ui uses CSS variables for theming. Ensure your `globals.css` includes the CSS variable definitions that shadcn/ui generates during initialization.

---

## shadcn/ui Integration

### Directory Conventions

- Components install to `src/components/ui/` by default
- Configure via `components.json` in project root
- Each component is a separate file (not a monolithic library)

### Component Organization

```
src/components/
├── ui/                 # shadcn/ui primitives (button, card, dialog, etc.)
├── forms/              # Composed form components using ui primitives
├── layouts/            # Layout compositions
└── shared/             # Other shared components built on ui primitives
```

### Theming Alignment

- shadcn/ui uses CSS variables defined in `globals.css`
- Customize the color palette in the CSS variables, not in individual components
- Support dark mode via the `.dark` class on `<html>` element
- Use the `cn()` utility from `src/lib/utils.ts` for conditional classes

### Best Practices

1. **Don't modify ui/ components directly** - extend by composition
2. **Create wrapper components** for app-specific variants
3. **Keep primitives primitive** - add business logic in composed components
4. **Use the provided variants** - leverage the built-in variant system

---

## State Management Patterns (Conceptual)

### Server-First Architecture

Next.js App Router is designed for a server-first approach:
- **Most state lives on the server** - fetched via Server Components
- **URL state** - use searchParams for filterable/shareable state
- **Form state** - use Server Actions for mutations

### When Server State is Sufficient (Most Cases)

- Data fetched at request time via Server Components
- Revalidation via `revalidatePath` or `revalidateTag`
- Optimistic updates via Server Actions
- No need for client-side caching libraries in most scenarios

### When React Context is Appropriate

- Theme/appearance preferences
- Authentication state (user session)
- Feature flags
- Locale/internationalization

### When Lightweight Client State is Justified

- Complex multi-step forms
- Highly interactive UI state (drag-and-drop, real-time collaboration)
- Offline-first requirements
- Optimistic UI with complex rollback logic

### Component & Client-Side State (Conceptual)

- **Default to local component state** - `useState` and `useReducer` are sufficient for most component-level state
- **Action-reducer patterns** (Redux Toolkit-style) are useful mental models for complex state transitions, but should be considered only for genuinely complex scenarios
- **Lift state minimally** - only lift state when genuinely shared between components
- **Avoid premature abstraction** - don't add state management complexity until proven necessary

### Async Data Management (Conceptual)

- **Server Components are the default** for data fetching in Next.js App Router
- **Server Actions** handle mutations without client-side fetching libraries
- **Client-side async patterns** (TanStack Query-style, RTK Query-style) are optional tools for edge cases:
  - Real-time subscriptions
  - Infinite scroll with client-side caching
  - Complex optimistic updates
  - Offline sync requirements
- **Start without client async libraries** - add only when server-driven patterns prove insufficient

---

## Testing Strategy

### Framework Recommendations

- **Vitest** (Preferred): Faster, ESM-native, compatible with Vite ecosystem
- **Jest** (Alternative): Mature ecosystem, wider community support

### Test File Organization

```
tests/
├── components/
│   └── button.test.tsx
├── lib/
│   └── utils.test.ts
├── hooks/
│   └── use-custom-hook.test.ts
└── setup.ts
```

Or colocate tests with source files:
```
src/
├── components/
│   ├── button.tsx
│   └── button.test.tsx
```

### Component Testing Approach

- Use **React Testing Library** for component tests
- Test behavior, not implementation details
- Focus on user interactions and accessibility
- Mock Server Components appropriately in tests

### Integration with App Router

- Test Server Components by testing their output
- Test Client Components with standard React Testing Library patterns
- Use MSW (Mock Service Worker) for API mocking when needed
- Test Server Actions by invoking them directly in tests

### Test Configuration

For Vitest, configure `vitest.config.ts`:
- Set up React Testing Library
- Configure path aliases to match `tsconfig.json`
- Add setup file for global test configuration

---

## Configuration Checklist

### TypeScript Configuration (`tsconfig.json`)

- [ ] `strict: true` enabled
- [ ] Path aliases configured (`@/*` → `src/*`)
- [ ] `moduleResolution: "bundler"` for Next.js 13.4+
- [ ] `jsx: "preserve"` for Next.js
- [ ] Include `next-env.d.ts`

### ESLint Configuration

- [ ] `next/core-web-vitals` extends enabled
- [ ] TypeScript ESLint rules configured
- [ ] Import sorting rules (optional but recommended)
- [ ] Accessibility rules via `eslint-plugin-jsx-a11y`

### Prettier Configuration

- [ ] Tailwind CSS plugin for class sorting (`prettier-plugin-tailwindcss`)
- [ ] Consistent formatting rules defined
- [ ] Integration with ESLint (avoid conflicts)

### Environment Variables

- [ ] `.env.example` template created
- [ ] `.env.local` in `.gitignore`
- [ ] `NEXT_PUBLIC_` prefix for client-side variables
- [ ] Server-only variables kept without prefix

### Next.js Configuration (`next.config.ts`)

- [ ] Image domains configured if using external images
- [ ] Redirects and rewrites defined if needed
- [ ] Headers configured for security
- [ ] Experimental features evaluated and enabled as needed

### shadcn/ui Configuration (`components.json`)

- [ ] Style: "default" or "new-york"
- [ ] Base color configured
- [ ] CSS variables enabled
- [ ] Path aliases aligned with tsconfig

---

## Validation Checklist

Before considering the project setup complete, verify:

### Build & Type Safety

- [ ] `npm run build` succeeds without errors
- [ ] `npx tsc --noEmit` passes type checking
- [ ] No TypeScript errors in IDE

### Code Quality

- [ ] `npm run lint` passes without errors
- [ ] Prettier formatting applied consistently
- [ ] No ESLint warnings in critical paths

### Development Server

- [ ] `npm run dev` starts without errors
- [ ] Home page renders correctly
- [ ] No console errors in browser
- [ ] Hot reload works as expected

### Testing

- [ ] Test suite runs (`npm test`)
- [ ] All tests pass
- [ ] Test coverage meets team standards (if applicable)

### UI System

- [ ] Tailwind CSS styles apply correctly
- [ ] shadcn/ui components render properly
- [ ] Dark mode toggle works (if implemented)
- [ ] CSS variables are properly defined

---

## Conflict Resolution

When guidance from different sources conflicts:

1. **Official Next.js Documentation** takes precedence for Next.js-specific behavior
2. **Tailwind CSS Documentation** takes precedence for styling configuration
3. **shadcn/ui Documentation** takes precedence for component installation and customization
4. **vercel-react-best-practices** provides performance guidance but may be superseded by newer official docs

### Explaining Tradeoffs

When multiple valid approaches exist:
- Present options clearly with pros and cons
- Recommend the approach aligned with enterprise-grade, long-lived goals
- Defer to official documentation for authoritative answers
- Use `fetch-library-docs` to retrieve current documentation when uncertain

---

## Skill References

### Documentation Grounding

Use **fetch-library-docs** skill to retrieve authoritative documentation for:
- Next.js App Router setup and configuration
- Tailwind CSS installation and configuration
- shadcn/ui installation, components, and theming
- React Server Components patterns

### Performance Guidance

Use **vercel-react-best-practices** skill for:
- Rendering strategy decisions
- Bundle optimization techniques
- Component composition patterns
- Performance monitoring approaches

---

## Out-of-Scope Reminder

This skill explicitly does NOT cover:

- **Deployment**: No Vercel, AWS, Docker, Kubernetes, or CI/CD guidance
- **Code Generation**: No full component or page code generation
- **Command Execution**: No CLI commands are executed by this skill
- **State Libraries**: No Redux, Zustand, Jotai, or other library selection/configuration
- **Async Libraries**: No TanStack Query, SWR, or RTK Query selection/configuration
- **Backend Implementation**: No API design, database, or authentication implementation
- **Testing Implementation**: No specific test file generation

For these topics, consult appropriate specialized skills or documentation directly.
