# Quien.uy Navigation Reload Investigation Report

## 1. Executive summary

The full-page reload when navigating from `/login?next=...` back to the home/search page is caused by **raw `<a href>` elements** used for internal navigation instead of React Router `<Link>` or `useNavigate`. Specifically, the Navbar logo, Navbar nav links ("Buscar", "Cerca de vos"), Footer logo, and a landing page CTA button all use native anchor tags with internal route paths. These trigger browser-level document reload instead of client-side SPA routing.

## 2. Reproduction steps

1. Start the app (`npm run dev`).
2. Start JSON Server (`npm run dev:api`).
3. Navigate to `/login?next=%2Fmi-perfil` (or any `/login?next=...`).
4. From the login page, click the **Quien.uy logo** in the Navbar.
5. **Observe:** Full page reload — the entire HTML document is re-fetched from the server, React state is destroyed, dark mode may flash, and the network tab shows a document request.

Alternatively:
- Navigate to `/login?next=...`.
- Click **"Buscar"** in the Navbar nav links.
- **Observe:** Same full page reload.

## 3. Expected behavior

All internal navigation (`/login` → `/`, `/login` → `/buscar`, etc.) should use React Router's client-side routing. No HTML document request should appear in the Network tab. React state (auth, theme, query cache) should be preserved across navigations.

## 4. Actual behavior

Clicking the Navbar logo, Navbar nav links ("Buscar", "Cerca de vos"), Footer logo, or Provider CTA button causes a full browser navigation. The page completely reloads: the React app unmounts and re-initializes, query cache is cleared, theme may briefly flash, and any local component state is lost.

## 5. Files inspected

| File | Purpose |
|------|---------|
| `src/components/landing/Navbar.tsx` | Navbar with logo, nav links, mobile drawer |
| `src/components/landing/Footer.tsx` | Footer with logo, link columns |
| `src/components/landing/ProviderCTASection.tsx` | CTA section with "Sumar mi perfil" button |
| `src/pages/LoginPage.tsx` | Login page (uses `<Link>` and `navigate()` — safe) |
| `src/pages/AuthPage.tsx` | OAuth callback page |
| `src/router/AppRouter.tsx` | Route definitions |
| `src/router/ProtectedRoute.tsx` | Route guard (uses `<Navigate>` — safe) |
| `src/lib/auth.tsx` | Auth context with `login()` (OAuth redirect — intentional) |
| `src/common/MainLayout.tsx` | Shared layout for protected routes |
| `src/pages/landing/LandingPage.tsx` | Landing page (composes child components) |
| `src/components/landing/HeroSection.tsx` | Hero section |
| `src/components/landing/SearchPanel.tsx` | Search form (uses `navigate()` — safe) |
| `src/components/landing/CategorySection.tsx` | Categories section |
| `src/components/landing/CategoryCard.tsx` | Category card (uses `href="#buscar"` — safe anchor) |
| `src/components/landing/HowItWorksSection.tsx` | How it works section |
| `src/components/landing/FeaturedProfilesSection.tsx` | Featured profiles |
| `src/components/landing/TerritorySection.tsx` | Territory section |
| `src/components/landing/TrustSection.tsx` | Trust section |
| `src/components/landing/ProfessionAutocomplete.tsx` | Autocomplete (no links) |
| `src/components/landing/ThemeToggle.tsx` | Theme toggle (no links) |
| `src/pages/ProfileFormPage.tsx` | Profile form page |
| `src/pages/ProfileDetailPage.tsx` | Profile detail (uses `navigate()` — safe) |
| `src/components/profiles/ReviewForm.tsx` | Review form (uses `preventDefault` — safe) |
| `src/components/profiles/ProfileForm.tsx` | Profile form (uses react-hook-form — safe) |
| `src/pages/LoginRequiredPage.tsx` | Redirect to `/login` (uses `<Navigate>` — safe) |
| `src/pages/MyAccountPage.tsx` | Account page |
| `src/pages/MyProfilePage.tsx` | Profile page |
| `src/pages/MyReviewsPage.tsx` | Reviews page |
| `src/services/locationService.ts` | Location service (read-only `window.location` — safe) |

## 6. Search audit

### `window.location` usage (4 matches)

| File | Line | Code | Risk |
|------|------|------|------|
| `src/lib/auth.tsx` | 113 | `window.location.href = \`${base}/api/auth/login/google?force=1\`` | **Intentional** — OAuth redirect to backend |
| `src/pages/ProfileFormPage.tsx` | 23 | `window.location.pathname.includes('/editar')` | Safe (read-only) |
| `src/services/locationService.ts` | 30 | `window.location.search` | Safe (read-only) |
| `src/pages/AuthPage.tsx` | 41 | `window.location.pathname` | Safe (read-only) |

### `<a href="/">` (raw internal links)

| File | Line | Code | Risk |
|------|------|------|------|
| `src/components/landing/Navbar.tsx` | 55 | `<a href="/" className="flex items-center gap-2.5">` | **HIGH** — logo link |
| `src/components/landing/Footer.tsx` | 20 | `<a href="/" className="flex items-center gap-2.5">` | **HIGH** — logo link |

### `<a href={link.href}>` with internal route paths

| File | Lines | Code | Risk |
|------|-------|------|------|
| `src/components/landing/Navbar.tsx` | 9-14, 67-73 | `NAV_LINKS` array: `{ href: '/buscar' }`, `{ href: '/cerca-de-mi' }` rendered as `<a href={link.href}>` | **HIGH** — desktop nav links |
| `src/components/landing/Navbar.tsx` | 9-14, 242-249 | Same `NAV_LINKS` rendered in mobile drawer as `<a href={link.href}>` | **HIGH** — mobile nav links |

### `<a href="/auth">` (CTA button)

| File | Line | Code | Risk |
|------|------|------|------|
| `src/components/landing/ProviderCTASection.tsx` | 30-35 | `<a href="/auth" className="btn ...">Sumar mi perfil</a>` | **MEDIUM** — CTA button navigates to auth |

### `onSubmit` / `preventDefault` (forms)

| File | Line | Status |
|------|------|--------|
| `src/components/landing/SearchPanel.tsx` | 113, 139 | Safe — `e.preventDefault()` called |
| `src/components/profiles/ReviewForm.tsx` | 39, 73 | Safe — `e.preventDefault()` called |
| `src/components/profiles/ProfileForm.tsx` | 151 | Safe — react-hook-form handles |

### React Router usage (safe patterns)

| File | Pattern | Status |
|------|---------|--------|
| `src/pages/LoginPage.tsx` | `<Link to="/">` (line 107) | Safe |
| `src/pages/LoginPage.tsx` | `navigate(next)` (line 43) | Safe |
| `src/router/ProtectedRoute.tsx` | `<Navigate to="/login?next=...">` (line 35) | Safe |
| `src/router/AppRouter.tsx` | `<Navigate to="/mi-cuenta">` (line 73-75) | Safe |
| `src/pages/LoginRequiredPage.tsx` | `<Navigate to="/login?next=...">` (line 13) | Safe |
| `src/components/landing/SearchPanel.tsx` | `navigate(queryString ? ...)` (line 123) | Safe |

### `form action`

No matches found.

### `type="submit"`

| File | Line | Status |
|------|------|--------|
| `src/components/profiles/ReviewForm.tsx` | 154 | Safe — form has `onSubmit` with `preventDefault` |
| `src/components/profiles/ProfileForm.tsx` | 303 | Safe — react-hook-form wraps with `preventDefault` |
| `src/components/landing/SearchPanel.tsx` | 198 | Safe — form has `onSubmit` with `preventDefault` |

## 7. Findings

### Finding 1: Navbar logo uses raw `<a href="/">`
- **File:** `src/components/landing/Navbar.tsx`
- **Line:** 55
- **Code:** `<a href="/" className="flex items-center gap-2.5">`
- **Why it causes reload:** Native `<a href="/">` triggers a full browser navigation to `/`. The browser fetches the HTML document from the server, re-initializes the React app, and destroys all client state.
- **Confidence:** HIGH

### Finding 2: Navbar nav links use raw `<a href={link.href}>`
- **File:** `src/components/landing/Navbar.tsx`
- **Lines:** 67-73 (desktop), 242-249 (mobile drawer)
- **Code:** `<a key={link.href} href={link.href} ...>` rendering NAV_LINKS which includes `{ href: '/buscar' }` and `{ href: '/cerca-de-mi' }`
- **Why it causes reload:** Same as Finding 1 — native anchor tags with internal route paths trigger full page reloads. The `#categorias` and `#como-funciona` anchors are safe (same-page scroll anchors), but `/buscar` and `/cerca-de-mi` are full route navigations.
- **Confidence:** HIGH

### Finding 3: Footer logo uses raw `<a href="/">`
- **File:** `src/components/landing/Footer.tsx`
- **Line:** 20
- **Code:** `<a href="/" className="flex items-center gap-2.5">`
- **Why it causes reload:** Same mechanism as Finding 1.
- **Confidence:** HIGH

### Finding 4: Provider CTA section uses raw `<a href="/auth">`
- **File:** `src/components/landing/ProviderCTASection.tsx`
- **Lines:** 30-35
- **Code:** `<a href="/auth" className="btn ...">Sumar mi perfil</a>`
- **Why it causes reload:** Native anchor with internal route path `/auth` triggers full page reload.
- **Confidence:** HIGH

### Finding 5: OAuth redirect is intentional (not a bug)
- **File:** `src/lib/auth.tsx`
- **Line:** 113
- **Code:** `window.location.href = \`${base}/api/auth/login/google?force=1\``
- **Why it causes reload:** This navigates to the backend OAuth endpoint, which is a different origin. Full page navigation is expected and correct for OAuth flows.
- **Confidence:** N/A (not a bug)

### Finding 6: Footer link columns use raw anchors
- **File:** `src/components/landing/Footer.tsx`
- **Lines:** 43-44 (FOOTER_LINKS), 60-61 (LEGAL_LINKS), 79-82 (social links)
- **Code:** `<a href="#buscar">`, `<a href="#">`, etc.
- **Why it does NOT cause reload:** These are same-page anchor links (`#buscar`, `#categorias`, `#sumar-perfil`, `#`). They scroll within the current page. The social links use `href="#"` which scrolls to top.
- **Confidence:** LOW (not a reload issue)

## 8. Confirmed root cause or strongest hypothesis

**Root cause: Raw `<a href>` elements used for internal React Router routes.**

The Navbar (`src/components/landing/Navbar.tsx`) is the primary offender:

1. **Logo link** (line 55): `<a href="/">` — when clicked from any page (including `/login`), this triggers a full browser navigation to `/`, causing a complete page reload.

2. **Nav links** (lines 67-73, 242-249): `<a href="/buscar">` and `<a href="/cerca-de-mi">` — same mechanism.

The Footer (`src/components/landing/Footer.tsx`, line 20) has the same logo issue.

The ProviderCTASection (`src/components/landing/ProviderCTASection.tsx`, line 31) has `<a href="/auth">`.

**Why this causes a full page reload in React/Vite:**

React Router's `<Link>` component uses `event.preventDefault()` internally and calls `history.pushState()` to update the URL without a page reload. The router then re-renders only the affected components. A raw `<a href>` does none of this — the browser treats it as a traditional hyperlink, fetches the HTML document from the server, and re-initializes the entire application.

When the user clicks the logo on `/login?next=/mi-perfil` to go back to `/`, the browser sends a GET request for `/`, Vite's dev server returns `index.html`, the React app re-mounts from scratch, and all state is lost.

## 9. Recommended fix plan

### Fix 1: Navbar logo — `<a href="/">` → `<Link to="/">`
- **File:** `src/components/landing/Navbar.tsx`
- **Line:** 55
- **Change:** Replace `<a href="/">` with `<Link to="/">`
- **Required import:** Add `import { Link } from 'react-router-dom'` (already has `useNavigate` and `useLocation` from react-router-dom)

### Fix 2: Navbar NAV_LINKS — use `<Link>` for route links
- **File:** `src/components/landing/Navbar.tsx`
- **Lines:** 67-73 (desktop), 242-249 (mobile)
- **Change:** For links where `href` starts with `/` (route links like `/buscar`, `/cerca-de-mi`), use `<Link to={link.href}>`. For hash links (`#categorias`, `#como-funciona`), keep `<a href>` since they are same-page scroll anchors.
- **Approach:** Split rendering based on whether `link.href` starts with `#` or `/`.

### Fix 3: Footer logo — `<a href="/">` → `<Link to="/">`
- **File:** `src/components/landing/Footer.tsx`
- **Line:** 20
- **Change:** Replace `<a href="/">` with `<Link to="/">`
- **Required import:** Add `import { Link } from 'react-router-dom'`

### Fix 4: ProviderCTASection — `<a href="/auth">` → `<Link to="/login">`
- **File:** `src/components/landing/ProviderCTASection.tsx`
- **Lines:** 30-35
- **Change:** Replace `<a href="/auth">` with `<Link to="/login">` (since `/auth` is the OAuth callback page, the user-facing login route is `/login`)
- **Required import:** Add `import { Link } from 'react-router-dom'`

## 10. Risk assessment

| Fix | Risk Level | What Could Break | How to Test |
|-----|-----------|-----------------|-------------|
| Navbar logo → `<Link to="/">` | LOW | None — `<Link>` is a drop-in replacement for `<a href>` on internal routes | Click logo from any page, verify SPA navigation |
| NAV_LINKS → `<Link>` for route links | LOW | Hash anchors (`#categorias`, `#como-funciona`) must remain as `<a href>` | Click "Buscar" and "Cerca de vos" — verify SPA navigation. Click "Categorías" and "Cómo funciona" — verify scroll anchors still work |
| Footer logo → `<Link to="/">` | LOW | None | Click footer logo, verify SPA navigation |
| ProviderCTA → `<Link to="/login">` | LOW | Need to verify the route exists (it does at `/login`) | Click "Sumar mi perfil" on landing page — verify SPA navigation to `/login` |

## 11. Verification checklist

- [ ] Navigating from `/login` to `/` via logo click does not reload
- [ ] Navigating from `/login` to `/buscar` via nav link does not reload
- [ ] Navigating from `/login` to `/cerca-de-mi` via nav link does not reload
- [ ] Navbar logo click does not reload from any page
- [ ] Footer logo click does not reload
- [ ] "Buscar" link in Navbar does not reload
- [ ] "Cerca de vos" link in Navbar does not reload
- [ ] "Categorías" and "Cómo funciona" still scroll to correct sections (hash anchors)
- [ ] "Sumar mi perfil" CTA on landing page navigates to `/login` without reload
- [ ] Publicar mi perfil while logged out goes to `/login?next=/mi-perfil` without OAuth
- [ ] ProtectedRoute redirects to `/login?next=...` without OAuth
- [ ] Clicking "Continuar con Google" on login page is the only action that starts external auth
- [ ] Search form does not reload on submit
- [ ] Browser Network tab does not show a fresh document request for internal navigation
- [ ] React state/theme does not reset during internal navigation
- [ ] Dark mode remains unchanged during navigation
- [ ] Build passes (`npm run build`)

## 12. Notes

- The `auth.tsx` `login()` function (line 113) uses `window.location.href` to redirect to the backend OAuth endpoint. This is intentional and correct — OAuth requires a server-side redirect to a different origin. It should NOT be changed.
- The `AuthPage` at `/auth/*` is the OAuth callback handler. The ProviderCTASection links to `/auth` which is this callback page. It should be changed to `/login` (the user-facing login page).
- The Footer link columns (`FOOTER_LINKS`, `LEGAL_LINKS`) and social links use `href="#..."` anchors. These are same-page scroll links and do not cause reloads. They do not need to be changed.
- The `ProfileDetailPage`, `SearchPanel`, `ReviewForm`, and `ProfileForm` all use proper `navigate()` or `preventDefault()` patterns and are not contributors to this issue.
