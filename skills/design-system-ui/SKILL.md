---
name: design-system-ui
description: Frontend and UI work discipline. Detects and reuses an existing design system before writing any interface code, and applies sound UI craft when no system exists. Use whenever creating or modifying components, pages, layouts, themes, styling, or any visual interface.
---

# Design system first

Inventing UI is how agents produce beautiful interfaces that look nothing like the rest of the app. If a design system exists, your job is composition, not creativity.

## Workflow

1. **Inventory before writing a line of UI.** Find what already governs this codebase:

   ```sh
   better-grep "design tokens theme" --max-results 5
   better-find . --name "tailwind.config.*"
   ```

   Look for: component library directories (`components/ui/`, `packages/ui`), token sources (`tailwind.config`, `theme.ts`, `tokens.css`, CSS custom properties), installed kits in `package.json` (shadcn, Radix, MUI, Chakra, Ant, Mantine), Storybook stories, and one or two existing screens that show the house style.

2. **Map requirements to what exists.** For each UI element you're about to build: reuse an existing component, compose several, or — only when nothing composes — build new following the system's conventions (file location, prop patterns, styling approach).

3. **Token discipline.** Never hardcode values the system already names. No hex colors duplicating palette entries, no magic pixel spacings off-scale, no ad-hoc radii or shadows. If a needed value genuinely doesn't exist as a token, that's a design-system decision: add it to the token source once, then use it everywhere.

4. **Match interaction reality.** Every state the app's other components handle, yours handles too: hover, focus-visible, active, disabled, loading, error, empty. Agents notoriously ship only the happy path — the loading/error/empty trio is where homemade components get caught.

5. **Consistency checks** against neighboring screens: same breakpoints, same page padding rhythm, same icon set, same heading hierarchy. Dark mode if the app supports it — grep for `dark:` or `.dark` to know.

6. **Accessibility floor** (non-negotiable): semantic elements over div-soup, labeled form controls, visible focus states, hit targets ≥ 40px on touch, contrast ≥ WCAG AA, respect `prefers-reduced-motion` for animation.

## When no design system exists

Say so explicitly, then follow fundamentals so the code you write becomes the seed of one:

- Spacing on a 4/8px scale; type on a limited scale (12/14/16/20/24/32); one radius family; one shadow family.
- Layout first, decoration second: alignment and hierarchy carry the design; color and ornament finish it.
- Define tokens for anything used three or more times, in one file, and reference them everywhere.
- Restraint beats flourish: consistent spacing and clear hierarchy read as professional far more than gradients do.

## Anti-slop check (run on your own output before calling it done)

Models regress to the statistical mean of their training data, and UI training data is saturated with one aesthetic: the Tailwind-indigo SaaS template. These specific patterns *are* that mean. Each is survivable alone; stacked, they're a machine-made fingerprint.

- **Color:** indigo→violet gradients (`#6366F1` / `#8B5CF6`), `bg-clip-text` gradient headlines, default `blue-600` buttons, timid evenly-spread palettes with no dominant color, untouched shadcn zinc/slate.
- **Type:** Inter or Roboto as the only face, Space Grotesk chosen as if it were a decision, serif-italic accent word on a sans page, all-caps section labels everywhere, decorative monospace.
- **Layout:** the skeleton of centered hero + sparkle badge pill + exactly three feature cards (icon, heading, two lines) + CTA; four-column footer; zero asymmetry anywhere; uniform `gap-4` / `p-6` with no spatial hierarchy.
- **Components:** `rounded-2xl shadow-lg p-6` shadcn card untouched; the colored left-border strip (the single most reliable tell); glassmorphism by reflex (`backdrop-blur` + white-alpha + glow) regardless of what sits behind it; icon-in-rounded-square; cards nested inside cards.
- **Details:** lucide `Sparkles`/`Zap` defaults, emoji as feature icons, the same fade-in-up on every element or bounce on every hover, CTA contrast below 4.5:1.

Countermeasures that actually work: commit to one direction and carry it through (a dominant color with a sharp accent beats any timid gradient); pick a typeface pairing deliberately and name why; introduce asymmetry where content allows; let motion serve one or two key moments instead of every element; measure contrast instead of eyeballing it.

## With the rest of agentmaxx

Inventory with better-context/better-find (bounded reads), verify assumptions about prop APIs with assumption-check, and let test-first pin interactive behavior.
