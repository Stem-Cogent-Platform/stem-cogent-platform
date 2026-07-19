# STEM COGENT — DOCUMENT 7: FRONTEND UX SPECIFICATION

**Document Version:** 1.0.0
**Status:** Production Draft
**Classification:** Internal Engineering — Restricted
**Owner:** Frontend Engineering / Product Design
**Document ID:** SC-DOC-007
**Cloud Provider:** AWS
**Depends On:** SC-DOC-001, SC-DOC-002, SC-DOC-006
**Referenced By:** SC-DOC-008 (Security), SC-DOC-009 (DevOps)
**Last Updated:** 2025

---

## DOCUMENT CONTROL

| Field | Value |
|---|---|
| Document ID | SC-DOC-007 |
| Document Type | Frontend UX Specification |
| Approvers | Frontend Engineering Lead, Product Director, Principal Architect |

---

## GOVERNING PRINCIPLE — THIS IS NOT AN ANALYTICS UI

This document governs the design and engineering of an **Executive Operational Intelligence Interface**, not a data dashboard or analytics product.

The distinction is architectural, not cosmetic:

| Analytics UI | Executive Intelligence Interface |
|---|---|
| Displays data and lets users find meaning | Delivers pre-processed, prioritized meaning directly |
| User must interpret charts and tables | System surfaces interpretation; user acts on it |
| Information density is a feature | Information density is a failure mode |
| Interaction model: explore | Interaction model: investigate and decide |
| Primary question: "What happened?" | Primary question: "What should I pay attention to and why?" |

Every design decision in this document is made in service of one outcome: **a senior executive or strategy lead opens Stem Cogent and within 10 seconds knows exactly what matters today and why it matters.**

---

## TABLE OF CONTENTS

1. UX Philosophy & Core Design Principles
2. Technology Stack
3. Application Shell & Navigation Architecture
4. State Management Architecture
5. Real-Time Signal Streaming (WebSocket Integration)
6. Component Blueprints
   - 6.1 Priority Alert Matrix
   - 6.2 Global Intelligence Feed
   - 6.3 Signal Card (Feed Item)
   - 6.4 Signal Dossier (Expanded Detail View)
   - 6.5 Entity Intelligence Profile
   - 6.6 Market Relationship Graph View
   - 6.7 Conversational Intelligence Layer Panel
   - 6.8 Alert Center
   - 6.9 Digest View
   - 6.10 Settings & Preferences
7. Design System Specification
8. Routing & Page Architecture
9. Responsive Behavior & Breakpoints
10. Performance Architecture
11. Accessibility Requirements
12. Error & Empty State Design

---

---

# SECTION 1 — UX PHILOSOPHY & CORE DESIGN PRINCIPLES

---

## 1.1 The Five Non-Negotiable UX Laws

These laws govern every screen, component, and interaction in Stem Cogent. Any design that violates them is rejected regardless of how polished it looks.

---

### Law 1 — Priority Before Volume

**The system must make the most important signal visible first, always.**

The user must never have to scan, sort, or filter to find what matters most. The intelligence feed is sorted by composite urgency × confidence score by default. This order is never overridden by recency alone. A low-urgency signal published 5 minutes ago does not displace a high-urgency signal published 3 hours ago.

**Implementation constraint:** Default feed sort is `(urgency_score × 0.60) + (confidence_score × 0.40) DESC`. Users may override sort but the system default always respects priority.

---

### Law 2 — Context Before Detail

**Every signal card must answer "why does this matter?" before the user clicks anything.**

A user should never have to open a signal to understand its operational significance. The card itself — in its collapsed, feed state — must surface: what it is, how urgent it is, how confident we are, and what kind of action it implies. Detail comes in the dossier. Context comes in the card.

**Implementation constraint:** Signal cards display urgency band, domain tag, confidence indicator, corroboration count, and a 2-line summary excerpt. No card shows only a headline.

---

### Law 3 — One Primary Action Per View

**Every screen has one primary action. Secondary actions are subordinate.**

The intelligence feed's primary action is "investigate this signal." The entity profile's primary action is "open CIL for this entity." The alert center's primary action is "review this alert." There is never a screen where the user must decide between multiple equally-prominent calls to action.

**Implementation constraint:** Every primary action is expressed as a visually dominant element. All secondary actions use ghost buttons, icon buttons, or overflow menus.

---

### Law 4 — No Decoration, No Filler

**Every pixel on screen must either communicate information or create space for information to breathe.**

Charts for the sake of charts, gradient backgrounds, animated counters, and "AI-powered" badges are explicitly prohibited. The visual language is minimalist, high-whitespace, and precision-first. The interface looks like a premium intelligence briefing document — not a SaaS dashboard.

**Implementation constraint:** No pie charts. No radial gauges. No animated number counters. No gradient fills on data elements. No stock photography. Permitted visual elements: confidence bands (color-coded text/line), urgency indicators (badge), domain tags (pill), relationship graphs (force-directed, minimal).

---

### Law 5 — Investigation, Not Exploration

**Users come to Stem Cogent to investigate something specific or be alerted to something unexpected. The UX must support both modes.**

Mode A — Alert-Driven: User receives a push notification or opens the app to check morning intelligence. The interface surfaces the most important items immediately. User investigates top items in order.

Mode B — Entity-Driven: User wants to investigate a specific company, regulator, or market. They navigate directly to the entity profile and open the CIL anchored to that entity.

The interface must not require users to discover their own workflow. The two entry points — feed (alert-driven) and entity (investigation-driven) — are always one tap away.

---

## 1.2 Design Voice & Aesthetic Direction

**Visual tone:** Premium strategy memo. Think Goldman Sachs research brief meets Palantir operational intelligence interface. Not Notion. Not Mixpanel. Not Linear.

**Color philosophy:** White backgrounds for primary surfaces with high-contrast content areas. One primary accent color for urgency/action states (deep amber for HIGH, red-adjacent for CRITICAL). Confidence indicators use a desaturated scale. Domain tags use a constrained 6-color taxonomy palette.

**Typography philosophy:** Two typefaces maximum. One serif for headlines and signal titles (authority, gravitas). One sans-serif for all body, metadata, and UI chrome (clarity, speed). Never use more than three font sizes on a single screen.

**Whitespace philosophy:** Space is not empty — it is clarity. Tight layouts are prohibited. Every major content section has breathing room. Cards have generous internal padding.

---

---

# SECTION 2 — TECHNOLOGY STACK

---

## 2.1 Core Stack

```
Framework:        Next.js 15 (App Router, TypeScript)
Styling:          Tailwind CSS 3.x (utility classes only — no custom CSS except design tokens)
Component base:   shadcn/ui (headless, accessible, composable)
State management: Zustand 4.x (global store) + TanStack Query 5.x (server state)
Real-time:        Native WebSocket API + custom hook (no socket.io dependency)
Graph vis:        D3.js v7 (force-directed entity relationship graph)
Charts:           Recharts (used sparingly — only signal volume timeline)
Animations:       Framer Motion (entrance animations only — no looping or gratuitous motion)
Forms:            React Hook Form + Zod validation
HTTP client:      TanStack Query with Axios (typed API client auto-generated from OpenAPI spec)
Date handling:    date-fns (lightweight; no moment.js)
Icons:            Lucide React (consistent, minimal icon set)
PDF export:       jsPDF + html2canvas (client-side export)
Testing:          Vitest + React Testing Library + Playwright (e2e)
```

## 2.2 Build & Delivery

```
Build tool:       Next.js built-in (Turbopack in development)
CDN:              AWS CloudFront (static assets + HTML)
Deployment:       AWS Amplify or ECS + CloudFront (see SC-DOC-009)
Bundle target:    < 200KB initial JS bundle (gzipped)
Image optimization: Next.js Image component (no raw <img> tags)
Font loading:     next/font with display: swap (zero layout shift)
```

---

---

# SECTION 3 — APPLICATION SHELL & NAVIGATION ARCHITECTURE

---

## 3.1 Shell Layout

```
+------------------------------------------------------------------+
|  TOP NAVIGATION BAR (fixed, 56px height)                         |
|  [Stem Cogent logo]  [Global search]  [Alert bell]  [User menu]  |
+------------------+-----------------------------------------------+
|                  |                                               |
|  LEFT SIDEBAR    |  MAIN CONTENT AREA                            |
|  (240px, fixed)  |  (fluid width, scrollable)                    |
|                  |                                               |
|  Intelligence    |  [Page-specific content]                      |
|  Entities        |                                               |
|  Alerts          |                                               |
|  Digests         |  +-------------------------------------------+|
|  ──────────────  |  | CIL PANEL (right drawer, 420px)            ||
|  Sources         |  | Slides in over main content                ||
|  Settings        |  | Does NOT push main content                 ||
|                  |  +-------------------------------------------+|
+------------------+-----------------------------------------------+
```

**Shell constraints:**
- Top navigation bar is always visible. Never hidden. Never collapsed.
- Left sidebar is always visible on desktop (≥ 1024px). Collapses to icon-only rail (64px) on tablet (768–1023px). Becomes bottom navigation sheet on mobile (< 768px).
- CIL Panel opens as a right-side drawer overlay — does not push or resize the main content area. It sits at z-index layer above main content with a subtle backdrop.
- Main content area is the only scrollable region. Sidebar and nav bar never scroll.

## 3.2 Navigation Items & Routes

```
PRIMARY NAVIGATION (sidebar):
  Intelligence Feed    → /dashboard
  Entities             → /entities
  Alert Center         → /alerts
  Digests              → /digests

SECONDARY NAVIGATION (sidebar, below divider):
  Source Registry      → /admin/sources        (ADMIN only)
  Team & Settings      → /settings

TOP NAVIGATION:
  Global Search        → Cmd+K command palette (not a page)
  Alert Bell           → Opens /alerts panel as slide-over
  User Menu            → Profile, timezone, logout
```

## 3.3 Active State & Route Indicators

Active navigation item: left border accent (3px, primary color) + background tint. No animated transitions on navigation state changes — instant feedback.

Unread alert count badge on Alert Bell: red dot with count if unread alerts > 0. Disappears when user visits /alerts and marks all read.

---

---

# SECTION 4 — STATE MANAGEMENT ARCHITECTURE

---

## 4.1 State Domains

State in Stem Cogent is divided into three distinct domains with different management strategies:

| Domain | Tool | Description |
|---|---|---|
| Server State | TanStack Query | All data fetched from API: signals, entities, alerts, digests, clusters |
| Global UI State | Zustand | User session, WebSocket connection status, CIL panel open/close, active filters, notification queue |
| Local Component State | React useState/useReducer | Form inputs, accordion open/close, tooltip visibility |

**Rule:** Server state is never duplicated in Zustand. Zustand holds only UI state and derived control flags — not data.

## 4.2 Zustand Global Store Structure

```typescript
// store/index.ts

interface StemCogentStore {
  // Authentication
  user: User | null;
  isAuthenticated: boolean;

  // WebSocket
  wsStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  wsLastHeartbeat: Date | null;

  // CIL Panel
  cilPanelOpen: boolean;
  cilAnchorType: 'SIGNAL' | 'ENTITY' | null;
  cilAnchorId: string | null;
  cilSessionId: string | null;

  // Feed filters (persisted to localStorage)
  feedFilters: {
    domains: string[];
    urgencyBands: string[];
    regions: string[];
    entityIds: string[];
    sortBy: 'priority' | 'recency' | 'confidence';
  };

  // Real-time notification queue
  // Incoming WebSocket signals that haven't been rendered into the feed yet
  pendingSignals: SignalCard[];
  pendingSignalCount: number;

  // Alert notification queue
  alertQueue: AlertNotification[];

  // Actions
  openCIL: (anchorType: 'SIGNAL' | 'ENTITY', anchorId: string) => void;
  closeCIL: () => void;
  setFeedFilters: (filters: Partial<FeedFilters>) => void;
  addPendingSignal: (signal: SignalCard) => void;
  flushPendingSignals: () => void;
  dismissAlert: (alertId: string) => void;
}
```

## 4.3 TanStack Query Configuration

```typescript
// lib/query-client.ts

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,        // 5 minutes — feed data is fresh for 5 min
      gcTime: 30 * 60 * 1000,          // 30 minutes in garbage collection
      retry: 2,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10000),
      refetchOnWindowFocus: false,      // WebSocket handles live updates
      refetchOnReconnect: true,
    },
    mutations: {
      retry: 0,                         // Mutations do not auto-retry
    }
  }
});

// Key factory pattern — all query keys centralized
export const queryKeys = {
  signals: {
    all: ['signals'] as const,
    list: (filters: FeedFilters) => ['signals', 'list', filters] as const,
    detail: (id: string) => ['signals', 'detail', id] as const,
  },
  entities: {
    all: ['entities'] as const,
    detail: (id: string) => ['entities', 'detail', id] as const,
    signals: (id: string) => ['entities', 'signals', id] as const,
  },
  alerts: {
    all: ['alerts'] as const,
    preferences: ['alerts', 'preferences'] as const,
  },
  cil: {
    sessions: ['cil', 'sessions'] as const,
    session: (id: string) => ['cil', 'session', id] as const,
  },
  analytics: {
    volume: (params: AnalyticsParams) => ['analytics', 'volume', params] as const,
    trends: ['analytics', 'trends'] as const,
  }
};
```

---

---

# SECTION 5 — REAL-TIME SIGNAL STREAMING (WEBSOCKET INTEGRATION)

---

## 5.1 WebSocket Connection Lifecycle

```typescript
// hooks/useSignalStream.ts

export function useSignalStream() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const reconnectAttempts = useRef(0);
  const MAX_RECONNECT_ATTEMPTS = 10;
  const RECONNECT_BASE_DELAY_MS = 1000;

  const { user } = useStemCogentStore();
  const {
    wsStatus,
    addPendingSignal,
    alertQueue,
  } = useStemCogentStore();

  const setWsStatus = useStemCogentStore(s => s.setWsStatus);
  const addAlert = useStemCogentStore(s => s.addAlert);

  const connect = useCallback(() => {
    if (!user?.accessToken) return;

    setWsStatus('connecting');

    // Access token passed as query param (WebSocket cannot send headers)
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/ws/feed?token=${user.accessToken}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsStatus('connected');
      reconnectAttempts.current = 0;

      // Send subscription preferences
      ws.send(JSON.stringify({
        type: 'SUBSCRIBE',
        domains: user.preferences.subscribedDomains,
        min_urgency: user.preferences.minUrgencyThreshold
      }));

      // Start heartbeat
      startHeartbeat(ws);
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data) as WsMessage;
      handleMessage(message);
    };

    ws.onclose = (event) => {
      setWsStatus('disconnected');
      stopHeartbeat();

      // Do not reconnect on intentional close (code 1000) or auth failure (4001)
      if (event.code === 1000 || event.code === 4001) return;

      scheduleReconnect();
    };

    ws.onerror = () => {
      setWsStatus('error');
    };
  }, [user?.accessToken]);

  const handleMessage = useCallback((message: WsMessage) => {
    switch (message.type) {

      case 'SIGNAL_UPDATE': {
        // New signal arrived — add to pending queue (not directly into feed)
        // User sees "N new signals" banner; clicks to flush into feed
        // This prevents the feed from jumping while user is reading
        addPendingSignal(message.data as SignalCard);
        break;
      }

      case 'ALERT': {
        // CRITICAL/HIGH alert — show toast notification immediately
        addAlert(message.data as AlertNotification);
        showAlertToast(message.data as AlertNotification);
        break;
      }

      case 'CLUSTER_UPDATE': {
        // An existing cluster has been updated (new signal added, status changed)
        // Invalidate the specific cluster query cache
        queryClient.invalidateQueries({
          queryKey: queryKeys.signals.detail(message.data.clusterId)
        });
        break;
      }

      case 'PONG': {
        useStemCogentStore.getState().setWsLastHeartbeat(new Date());
        break;
      }
    }
  }, []);

  const scheduleReconnect = useCallback(() => {
    if (reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS) {
      setWsStatus('error');
      return;
    }
    // Exponential backoff: 1s, 2s, 4s, 8s... capped at 30s
    const delay = Math.min(
      RECONNECT_BASE_DELAY_MS * Math.pow(2, reconnectAttempts.current),
      30000
    );
    reconnectAttempts.current++;
    reconnectTimeoutRef.current = setTimeout(connect, delay);
  }, [connect]);

  const startHeartbeat = (ws: WebSocket) => {
    const interval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'PING' }));
      }
    }, 25000); // Ping every 25 seconds
    heartbeatRef.current = interval;
  };

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close(1000, 'Component unmounted');
      clearTimeout(reconnectTimeoutRef.current);
      stopHeartbeat();
    };
  }, [connect]);

  return { wsStatus };
}
```

## 5.2 Pending Signal Banner

When new signals arrive via WebSocket, they are held in the `pendingSignals` queue rather than injected directly into the feed. This prevents the feed from shifting while the user is reading.

```typescript
// components/feed/PendingSignalsBanner.tsx

export function PendingSignalsBanner() {
  const { pendingSignalCount, flushPendingSignals } = useStemCogentStore();

  if (pendingSignalCount === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      className="sticky top-0 z-10 flex items-center justify-between
                 bg-amber-950/90 backdrop-blur-sm border border-amber-800/50
                 rounded-lg px-4 py-2 mb-3 cursor-pointer"
      onClick={flushPendingSignals}
    >
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
        <span className="text-sm font-medium text-amber-200">
          {pendingSignalCount} new signal{pendingSignalCount > 1 ? 's' : ''} available
        </span>
      </div>
      <span className="text-xs text-amber-400">
        Click to load
      </span>
    </motion.div>
  );
}
```

## 5.3 Alert Toast System

CRITICAL and HIGH urgency alerts dispatched via WebSocket render as persistent toast notifications that require explicit dismissal:

```typescript
// components/alerts/AlertToast.tsx

export function AlertToast({ alert }: { alert: AlertNotification }) {
  const urgencyConfig = {
    CRITICAL: {
      bg: 'bg-red-950 border-red-800',
      badge: 'bg-red-600 text-white',
      icon: AlertTriangle,
    },
    HIGH: {
      bg: 'bg-amber-950 border-amber-800',
      badge: 'bg-amber-600 text-white',
      icon: AlertCircle,
    },
  }[alert.alertType];

  return (
    <motion.div
      initial={{ opacity: 0, x: 80 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 80 }}
      className={`w-[380px] rounded-xl border p-4 shadow-2xl ${urgencyConfig.bg}`}
    >
      {/* Urgency badge */}
      <div className="flex items-start justify-between mb-2">
        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${urgencyConfig.badge}`}>
          {alert.alertType}
        </span>
        <DomainTag domain={alert.primaryDomain} size="sm" />
      </div>

      {/* Alert title — truncated to 2 lines */}
      <p className="text-sm font-semibold text-white leading-tight mb-1 line-clamp-2">
        {alert.alertTitle}
      </p>

      {/* Summary — 1 line */}
      <p className="text-xs text-zinc-400 line-clamp-1 mb-3">
        {alert.alertSummary}
      </p>

      {/* Confidence + actions */}
      <div className="flex items-center justify-between">
        <ConfidenceIndicator score={alert.signalConfidence} size="sm" />
        <div className="flex gap-2">
          <Button variant="ghost" size="xs"
                  onClick={() => dismissAlert(alert.alertId)}>
            Dismiss
          </Button>
          <Button variant="default" size="xs"
                  onClick={() => navigateToSignal(alert.signalId)}>
            Investigate →
          </Button>
        </div>
      </div>
    </motion.div>
  );
}
```

---

---

# SECTION 6 — COMPONENT BLUEPRINTS

---

## 6.1 Priority Alert Matrix

### Purpose

The Priority Alert Matrix is the first thing a user sees when they open the Intelligence Feed page. It is a compact, scannable summary of the highest-urgency signals active right now — before the full feed below. It answers the question: "Is there anything that requires immediate attention?"

### Layout Blueprint

```
+--------------------------------------------------------------------+
|  PRIORITY ALERT MATRIX                          [View all alerts →] |
+--------------------------------------------------------------------+
|                                                                    |
|  +-------------------------+  +-------------------------+          |
|  |  CRITICAL               |  |  HIGH                   |          |
|  |  2 signals              |  |  5 signals              |          |
|  +-------------------------+  +-------------------------+          |
|  |                         |  |                         |          |
|  |  [Red dot] REGULATORY   |  |  [Amber dot] COMPETITIVE|          |
|  |  CBN issues Tier 2      |  |  Flutterwave expansion  |          |
|  |  wallet directive        |  |  signals accelerating   |          |
|  |  Confidence: HIGH ●●●●○  |  |  Confidence: HIGH ●●●○○|          |
|  |  60 day compliance       |  |  3 sources              |          |
|  |  [Investigate →]         |  |  [Investigate →]        |          |
|  |  ─────────────────────  |  |                         |          |
|  |  [Red dot] REGULATORY   |  |  [+ 4 more HIGH alerts] |          |
|  |  SEC directive on...    |  |                         |          |
|  |  [Investigate →]         |  |                         |          |
|  +-------------------------+  +-------------------------+          |
|                                                                    |
+--------------------------------------------------------------------+
```

### Component Specification

```typescript
// components/feed/PriorityAlertMatrix.tsx

interface PriorityMatrixProps {
  criticalSignals: SignalCard[];
  highSignals: SignalCard[];
}

export function PriorityAlertMatrix({
  criticalSignals,
  highSignals
}: PriorityMatrixProps) {

  // Only render if there are CRITICAL or HIGH signals
  if (criticalSignals.length === 0 && highSignals.length === 0) {
    return null;  // Matrix is hidden entirely when nothing is urgent
  }

  return (
    <section aria-label="Priority alert matrix"
             className="mb-6 rounded-2xl border border-zinc-800 bg-zinc-950 p-5">

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          <h2 className="text-sm font-semibold text-zinc-200 tracking-wide uppercase">
            Requires Attention
          </h2>
        </div>
        <Link href="/alerts"
              className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors">
          View all alerts →
        </Link>
      </div>

      {/* Two-column grid: CRITICAL | HIGH */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

        {/* CRITICAL column */}
        {criticalSignals.length > 0 && (
          <PriorityColumn
            urgencyType="CRITICAL"
            signals={criticalSignals.slice(0, 2)}  // max 2 in matrix
            totalCount={criticalSignals.length}
          />
        )}

        {/* HIGH column */}
        {highSignals.length > 0 && (
          <PriorityColumn
            urgencyType="HIGH"
            signals={highSignals.slice(0, 1)}       // max 1 in matrix
            totalCount={highSignals.length}
          />
        )}
      </div>
    </section>
  );
}

function PriorityColumn({
  urgencyType,
  signals,
  totalCount
}: {
  urgencyType: 'CRITICAL' | 'HIGH';
  signals: SignalCard[];
  totalCount: number;
}) {
  const config = {
    CRITICAL: {
      dot: 'bg-red-500',
      border: 'border-red-900/50',
      bg: 'bg-red-950/30',
      label: 'text-red-400',
      overflowText: 'text-red-500'
    },
    HIGH: {
      dot: 'bg-amber-500',
      border: 'border-amber-900/50',
      bg: 'bg-amber-950/20',
      label: 'text-amber-400',
      overflowText: 'text-amber-500'
    }
  }[urgencyType];

  return (
    <div className={`rounded-xl border ${config.border} ${config.bg} p-4`}>
      {/* Column header */}
      <div className="flex items-center gap-1.5 mb-3">
        <div className={`w-1.5 h-1.5 rounded-full ${config.dot}`} />
        <span className={`text-xs font-bold ${config.label} tracking-widest`}>
          {urgencyType} · {totalCount}
        </span>
      </div>

      {/* Signal micro-cards */}
      <div className="space-y-3">
        {signals.map((signal, index) => (
          <PrioritySignalMicroCard key={signal.signalId} signal={signal}
                                    showDivider={index < signals.length - 1} />
        ))}
      </div>

      {/* Overflow indicator */}
      {totalCount > signals.length && (
        <p className={`text-xs mt-3 ${config.overflowText}`}>
          + {totalCount - signals.length} more {urgencyType.toLowerCase()} signal{totalCount - signals.length > 1 ? 's' : ''}
        </p>
      )}
    </div>
  );
}
```

---

## 6.2 Global Intelligence Feed

### Purpose

The main chronological (priority-sorted) intelligence feed. The primary content surface of the application. This is where users spend most of their time.

### Feed Architecture

```typescript
// components/feed/IntelligenceFeed.tsx

export function IntelligenceFeed() {
  const { feedFilters } = useStemCogentStore();
  const { pendingSignalCount, flushPendingSignals } = useStemCogentStore();

  // TanStack Query with infinite scroll
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError
  } = useInfiniteQuery({
    queryKey: queryKeys.signals.list(feedFilters),
    queryFn: ({ pageParam }) => fetchSignals({ ...feedFilters, cursor: pageParam }),
    getNextPageParam: (lastPage) => lastPage.meta.pagination.next_cursor ?? undefined,
    staleTime: 5 * 60 * 1000,
  });

  const signals = data?.pages.flatMap(p => p.data.signals) ?? [];

  // Intersection observer for infinite scroll
  const { ref: loadMoreRef } = useIntersectionObserver({
    onIntersect: () => { if (hasNextPage) fetchNextPage(); },
    threshold: 0.5
  });

  if (isLoading) return <FeedSkeleton />;
  if (isError) return <FeedErrorState />;

  return (
    <div className="space-y-1">

      {/* Filter Bar */}
      <FeedFilterBar />

      {/* Pending signals banner (WebSocket new arrivals) */}
      <PendingSignalsBanner />

      {/* Empty state */}
      {signals.length === 0 && <FeedEmptyState filters={feedFilters} />}

      {/* Signal cards */}
      {signals.map((signal) => (
        <SignalCard key={signal.signalId} signal={signal} />
      ))}

      {/* Infinite scroll trigger */}
      <div ref={loadMoreRef} className="py-4 flex justify-center">
        {isFetchingNextPage && (
          <div className="flex items-center gap-2 text-zinc-600 text-sm">
            <Spinner size="sm" /> Loading more signals...
          </div>
        )}
      </div>
    </div>
  );
}
```

### Feed Filter Bar

```typescript
// components/feed/FeedFilterBar.tsx
// Compact, horizontal filter strip above the feed
// Filters: Domain pills | Urgency toggle | Region dropdown | Sort control

export function FeedFilterBar() {
  const { feedFilters, setFeedFilters } = useStemCogentStore();

  const DOMAIN_OPTIONS = [
    { value: 'ALL', label: 'All', color: 'zinc' },
    { value: 'REGULATORY', label: 'Regulatory', color: 'blue' },
    { value: 'COMPETITIVE', label: 'Competitive', color: 'violet' },
    { value: 'CONSUMER', label: 'Consumer', color: 'emerald' },
    { value: 'FINANCIAL', label: 'Financial', color: 'amber' },
    { value: 'INFRASTRUCTURE', label: 'Infrastructure', color: 'rose' },
  ];

  return (
    <div className="flex items-center gap-2 pb-3 border-b border-zinc-800/50
                    overflow-x-auto scrollbar-hide">
      {/* Domain filter pills */}
      <div className="flex items-center gap-1.5 shrink-0">
        {DOMAIN_OPTIONS.map(domain => (
          <FilterPill
            key={domain.value}
            label={domain.label}
            color={domain.color}
            active={feedFilters.domains.includes(domain.value) ||
                    (domain.value === 'ALL' && feedFilters.domains.length === 0)}
            onClick={() => toggleDomainFilter(domain.value, setFeedFilters)}
          />
        ))}
      </div>

      <div className="w-px h-5 bg-zinc-700 shrink-0 mx-1" />

      {/* Urgency toggle */}
      <UrgencyToggle
        value={feedFilters.urgencyBands}
        onChange={(bands) => setFeedFilters({ urgencyBands: bands })}
      />

      <div className="ml-auto shrink-0">
        {/* Sort control */}
        <SortSelect
          value={feedFilters.sortBy}
          onChange={(sort) => setFeedFilters({ sortBy: sort })}
          options={[
            { value: 'priority', label: 'Priority' },
            { value: 'recency', label: 'Most Recent' },
            { value: 'confidence', label: 'Confidence' }
          ]}
        />
      </div>
    </div>
  );
}
```

---

## 6.3 Signal Card (Feed Item)

### Purpose

The atomic unit of the intelligence feed. Every signal card must communicate its operational significance without requiring a click. The card is the answer to "what is this and why should I care?" — the dossier is the answer to "what exactly happened and what should I do?"

### Layout Blueprint

```
+------------------------------------------------------------------------+
|  [CRITICAL badge]  [REGULATORY tag]    [60 days]  [Source: CBN · T1]  |
|  [Confidence: ●●●●○  HIGH]             [3 sources] [2 hr ago]         |
|                                                                        |
|  CBN issues Circular FPR/DIR/GEN/01/052 — Revised Transaction         |
|  Limits for Tier 2 Wallets                                             |
|                                                                        |
|  The Central Bank of Nigeria has issued a formal directive revising    |
|  daily transaction limits for Tier 2 mobile wallet holders, with a    |
|  60-day compliance window for all licensed mobile money operators.     |
|                                                                        |
|  [CBN] [Mobile Money Operators]  [COMPLIANCE_ACTION tag]              |
|                                                                        |
|  [Investigate →]  [Open in CIL]  [···]                                |
+------------------------------------------------------------------------+
```

### Component Specification

```typescript
// components/signal/SignalCard.tsx

interface SignalCardProps {
  signal: SignalCardData;
  variant?: 'feed' | 'matrix' | 'entity-feed';
}

export function SignalCard({ signal, variant = 'feed' }: SignalCardProps) {
  const router = useRouter();
  const openCIL = useStemCogentStore(s => s.openCIL);

  const urgencyConfig = useUrgencyConfig(signal.urgencyBand);

  return (
    <article
      role="article"
      aria-label={`Signal: ${signal.title}`}
      className={cn(
        "group relative rounded-xl border bg-zinc-950 hover:bg-zinc-900/80",
        "transition-colors duration-150 cursor-pointer",
        "border-zinc-800 hover:border-zinc-700",
        // CRITICAL signals get a left accent border
        signal.urgencyBand === 'CRITICAL' && "border-l-2 border-l-red-600",
        signal.urgencyBand === 'HIGH' && "border-l-2 border-l-amber-500",
      )}
      onClick={() => router.push(`/signals/${signal.signalId}`)}
    >
      <div className="p-5">

        {/* Row 1: Metadata strip */}
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          {/* Urgency badge — only shown for CRITICAL and HIGH */}
          {signal.urgencyBand !== 'STANDARD' && signal.urgencyBand !== 'LOW' && (
            <UrgencyBadge urgencyBand={signal.urgencyBand} />
          )}

          {/* Domain tag */}
          <DomainTag domain={signal.primaryDomain} />

          {/* Compliance deadline (if present) — HIGH INFORMATION DENSITY */}
          {signal.complianceDeadlineDays && (
            <DeadlinePill days={signal.complianceDeadlineDays} />
          )}

          {/* Spacer */}
          <div className="ml-auto flex items-center gap-3">
            {/* Source attribution */}
            <SourceAttribution
              sourceName={signal.sourceName}
              sourceTier={signal.sourceTier}
            />

            {/* Corroboration count */}
            {signal.corroborationCount > 1 && (
              <CorroborationBadge count={signal.corroborationCount} />
            )}

            {/* Time delta */}
            <TimeAgo timestamp={signal.publishedAt} />
          </div>
        </div>

        {/* Row 2: Confidence indicator */}
        <div className="mb-3">
          <ConfidenceIndicator
            score={signal.confidenceScore}
            band={signal.confidenceBand}
          />
        </div>

        {/* Row 3: Signal title */}
        <h3 className="text-base font-semibold text-zinc-100 leading-snug
                        mb-2 line-clamp-2 group-hover:text-white transition-colors">
          {signal.title}
        </h3>

        {/* Row 4: Summary excerpt (2-line preview) */}
        <p className="text-sm text-zinc-400 leading-relaxed line-clamp-2 mb-4">
          {signal.summaryPreview}
        </p>

        {/* Row 5: Entity tags + recommendation type */}
        <div className="flex items-center gap-2 flex-wrap mb-4">
          {signal.entities.slice(0, 3).map(entity => (
            <EntityMicroTag
              key={entity.entityId}
              entity={entity}
              onClick={(e) => {
                e.stopPropagation();
                router.push(`/entities/${entity.entitySlug}`);
              }}
            />
          ))}
          {signal.hasRecommendation && (
            <RecommendationTag type={signal.recommendationType} />
          )}
          {signal.clusterStatus === 'ACCELERATING' && (
            <ClusterAcceleratingTag />
          )}
        </div>

        {/* Row 6: Action strip */}
        <div className="flex items-center gap-2"
             onClick={(e) => e.stopPropagation()}>
          <Button
            variant="default"
            size="sm"
            onClick={() => router.push(`/signals/${signal.signalId}`)}
            className="text-xs"
          >
            Investigate →
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => openCIL('SIGNAL', signal.signalId)}
            className="text-xs"
          >
            Ask CIL
          </Button>
          <SignalCardMenu signalId={signal.signalId} />
        </div>
      </div>
    </article>
  );
}
```

### Sub-component Specifications

**UrgencyBadge:**
```typescript
// CRITICAL: bg-red-600, text-white, font-bold, "CRITICAL" label
// HIGH:     bg-amber-500, text-white, font-semibold, "HIGH" label
// No badge for STANDARD or LOW — those are conveyed through positioning in feed
```

**DomainTag:**
```typescript
// Pill shape, 6-color palette:
// REGULATORY:     bg-blue-950,   text-blue-400,   border-blue-900
// COMPETITIVE:    bg-violet-950, text-violet-400, border-violet-900
// CONSUMER:       bg-emerald-950, text-emerald-400, border-emerald-900
// FINANCIAL:      bg-amber-950,  text-amber-400,  border-amber-900
// INFRASTRUCTURE: bg-rose-950,   text-rose-400,   border-rose-900
// DEFAULT:        bg-zinc-900,   text-zinc-400,   border-zinc-700
```

**ConfidenceIndicator:**
```typescript
// 5-dot visual scale (●●●●○ = 4/5 = HIGH_CONFIDENCE)
// HIGH_CONFIDENCE:     4-5 green dots
// MODERATE_CONFIDENCE: 3 amber dots
// LOW_CONFIDENCE:      2 orange dots
// UNVERIFIED:          1 grey dot
// Label: "CONF: HIGH" in small caps beside dots
```

**SourceAttribution:**
```typescript
// "Source: {name} · T{tier}" (e.g., "CBN Circulars · T1")
// Tier 1: text-zinc-300 (authoritative — shown prominently)
// Tier 2-3: text-zinc-400
// Tier 4+: text-zinc-500
```

**DeadlinePill:**
```typescript
// Only shown when compliance_deadline_days is present
// "60 days" in red-tinted pill when < 30 days
// "60 days" in amber-tinted pill when 30-90 days
// Not shown when > 90 days (not immediately urgent)
```

---

## 6.4 Signal Dossier (Expanded Detail View)

### Purpose

The full intelligence brief for a single signal. Opened when user clicks "Investigate →" on a signal card. This is the deepest level of detail in the system. Every element answers one of three questions: What happened? Why does it matter? What should I do?

### Layout Blueprint

```
/signals/{signal_id}

+------------------------------------------------------------------+
|  ← Back to Intelligence Feed                                     |
+------------------------------------------------------------------+

LEFT COLUMN (60% width)                   RIGHT PANEL (40% width)
───────────────────────────────────────   ────────────────────────
[CRITICAL] [REGULATORY] [60 days]         CONFIDENCE BREAKDOWN
[CBN · T1] [3 sources] [30 May 2026]      ●●●●○  0.94  HIGH
                                          Source:   97%
SIGNAL TITLE (full, no truncation)        Corroboration: 85%
                                          Recency:  96%
EXECUTIVE SUMMARY                         Entity resolution: 94%
(Full 3-5 sentence synthesis)
                                          ─────────────────────
KEY DEVELOPMENTS                          AFFECTED ENTITIES
• Development 1                           [CBN logo] Central Bank...
• Development 2                           [Icon] Mobile Money Ops...
• Development 3
                                          ─────────────────────
OPERATIONAL IMPLICATION                   RELATED SIGNALS
(2 sentences)                             [Mini card] Similar 2023...
                                          [Mini card] See also...
RECOMMENDED ACTION
[Compliance Action Required]              ─────────────────────
  Audit Tier 2 wallet transaction         CLUSTER CONTEXT
  limit configurations...                 CBN Regulatory Activity
                                          Status: ACTIVE · 3 signals
──────────────────────────────────────    Velocity: ↑ Accelerating
EVIDENCE & SOURCES
[Source 1: CBN Circulars (T1)] ↗          ─────────────────────
[Source 2: TechCabal (T4)] ↗              ACTIONS
[Source 3: BusinessDay (T4)] ↗            [Open in CIL →]
                                          [Export PDF]
──────────────────────────────────────    [Share]
HISTORICAL CONTEXT                        [Mark Strategic]
[Historical signal card - 2023]
[Historical signal card - 2022]
```

### Component Specification

```typescript
// app/signals/[signalId]/page.tsx

export default function SignalDossierPage({
  params
}: {
  params: { signalId: string }
}) {
  const { data: signal, isLoading } = useQuery({
    queryKey: queryKeys.signals.detail(params.signalId),
    queryFn: () => fetchSignalDetail(params.signalId),
  });

  const openCIL = useStemCogentStore(s => s.openCIL);

  if (isLoading) return <DossierSkeleton />;
  if (!signal) return <SignalNotFound />;

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">

      {/* Breadcrumb */}
      <DossierBreadcrumb domain={signal.primaryDomain} />

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-8 mt-6">

        {/* LEFT: Main content */}
        <main className="space-y-8">

          {/* Signal header */}
          <DossierHeader signal={signal} />

          {/* Intelligence output */}
          <IntelligenceOutput
            summary={signal.intelligenceOutput.summary}
            keyDevelopments={signal.intelligenceOutput.keyDevelopments}
            operationalImplication={signal.intelligenceOutput.operationalImplication}
            confidenceNote={signal.intelligenceOutput.confidenceNote}
          />

          {/* Recommendation block */}
          <RecommendationBlock recommendation={signal.recommendation} />

          {/* Evidence & Sources */}
          <EvidencePanel citations={signal.intelligenceOutput.citations} />

          {/* Historical context */}
          {signal.historicalSimilarSignals.length > 0 && (
            <HistoricalContextPanel signals={signal.historicalSimilarSignals} />
          )}
        </main>

        {/* RIGHT: Intelligence sidebar */}
        <aside className="space-y-5">
          <ConfidenceBreakdownPanel scoreBreakdown={signal.scoreBreakdown}
                                     confidenceScore={signal.confidenceScore} />
          <AffectedEntitiesPanel entities={signal.entities} />
          <RelatedSignalsPanel signals={signal.relatedSignals} />
          {signal.cluster && (
            <ClusterContextPanel cluster={signal.cluster} />
          )}
          <DossierActionPanel
            signalId={signal.signalId}
            onOpenCIL={() => openCIL('SIGNAL', signal.signalId)}
          />
        </aside>
      </div>
    </div>
  );
}
```

### Recommendation Block Design

```typescript
// components/signal/RecommendationBlock.tsx
// Visual treatment distinguishes this as the primary action takeaway

const RECOMMENDATION_CONFIG = {
  COMPLIANCE_ACTION_REQUIRED: {
    icon: Shield,
    bg: 'bg-red-950/40 border-red-900/50',
    iconColor: 'text-red-400',
    label: 'Compliance Action Required',
    priority: 'HIGH'
  },
  COMPETITIVE_MONITORING_ESCALATE: {
    icon: TrendingUp,
    bg: 'bg-violet-950/40 border-violet-900/50',
    iconColor: 'text-violet-400',
    label: 'Competitive Monitoring — Escalate',
    priority: 'MEDIUM'
  },
  OPERATIONAL_RISK_ALERT: {
    icon: AlertTriangle,
    bg: 'bg-amber-950/40 border-amber-900/50',
    iconColor: 'text-amber-400',
    label: 'Operational Risk Alert',
    priority: 'HIGH'
  },
  INTELLIGENCE_BRIEF: {
    icon: FileText,
    bg: 'bg-zinc-900 border-zinc-800',
    iconColor: 'text-zinc-400',
    label: 'Intelligence Brief',
    priority: 'LOW'
  }
};
```

---

## 6.5 Entity Intelligence Profile

### Purpose

Provides a complete intelligence picture for a specific entity (company, regulator, infrastructure provider). Used for competitor monitoring and relationship investigation.

### Layout Blueprint

```
/entities/flutterwave

+------------------------------------------------------------------+
|  [COMPANY] [FINTECH] [NG · KE · GH]    Activity: HIGH (0.82)    |
|  Flutterwave                                                      |
|  Licensed MMO · Founded 2016 · ~4,000 employees                  |
+------------------------------------------------------------------+

SIGNAL ACTIVITY (last 30 days)      RELATIONSHIP GRAPH
[Timeline chart - weekly bars]       [Mini force-directed graph]
47 signals  ↑ +23% vs prior month    [Open full graph →]

DOMAIN BREAKDOWN                     RELATED ENTITIES
Competitive:    18  ████████         → CBN (LICENSED_BY)
Regulatory:     12  █████            → Paystack (COMPETES_WITH)
Talent/Org:      9  ████             → MTN (PARTNERS_WITH)
Capital:         5  ██

RECENT SIGNALS FOR THIS ENTITY
[Signal card 1]
[Signal card 2]
[Signal card 3]
[Load more →]
```

### Component Specification

```typescript
// app/entities/[entitySlug]/page.tsx

export default function EntityProfilePage({
  params
}: {
  params: { entitySlug: string }
}) {
  const { data: entity } = useQuery({
    queryKey: queryKeys.entities.detail(params.entitySlug),
    queryFn: () => fetchEntityDetail(params.entitySlug),
  });

  const openCIL = useStemCogentStore(s => s.openCIL);

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">

      {/* Entity header */}
      <EntityProfileHeader entity={entity} />

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-8 mt-8">

        <main className="space-y-8">
          {/* Signal activity timeline */}
          <EntitySignalTimeline
            activityTimeline={entity.activityTimelineWeekly}
            signalCount30d={entity.signalCount30d}
          />

          {/* Domain breakdown */}
          <DomainBreakdownBar breakdown={entity.domainActivityBreakdown} />

          {/* Recent signals feed (filtered to this entity) */}
          <EntitySignalFeed entityId={entity.entityId} />
        </main>

        <aside className="space-y-5">
          {/* Mini relationship graph */}
          <EntityRelationshipMiniGraph
            entityId={entity.entityId}
            relationships={entity.relationships}
          />

          {/* Related entities list */}
          <RelatedEntitiesList relationships={entity.relationships} />

          {/* CIL entry point anchored to entity */}
          <EntityCILEntryCard
            entity={entity}
            onOpen={() => openCIL('ENTITY', entity.entityId)}
            suggestedQueries={[
              `What strategic direction does ${entity.entityName} appear to be pursuing?`,
              `What operational risks are increasing for ${entity.entityName}?`,
              `What markets is ${entity.entityName} expanding into?`
            ]}
          />
        </aside>
      </div>
    </div>
  );
}
```

---

## 6.6 Market Relationship Graph View

### Purpose

Force-directed graph visualization of entity relationships within the intelligence graph. Accessible from entity profiles and as a standalone view. Used for mapping competitive landscapes, regulatory relationships, and infrastructure dependencies.

### Technical Specification

```typescript
// components/graph/MarketRelationshipGraph.tsx

interface GraphNode {
  id: string;
  name: string;
  entityType: string;
  activityScore: number;   // determines node size
  sector: string;
  signalCount30d: number;
}

interface GraphLink {
  source: string;
  target: string;
  relationshipType: string;
  strength: number;
}

export function MarketRelationshipGraph({
  centerEntityId,
  depth = 2           // relationship depth: 1 = direct, 2 = second-degree
}: {
  centerEntityId: string;
  depth?: 1 | 2;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const { data: graphData } = useQuery({
    queryKey: ['graph', centerEntityId, depth],
    queryFn: () => fetchEntityGraph(centerEntityId, depth)
  });

  useEffect(() => {
    if (!svgRef.current || !graphData) return;
    renderD3Graph(svgRef.current, graphData);
  }, [graphData]);

  return (
    <div className="relative w-full rounded-2xl border border-zinc-800
                    bg-zinc-950 overflow-hidden" style={{ height: '520px' }}>

      {/* Graph controls */}
      <div className="absolute top-4 right-4 z-10 flex flex-col gap-2">
        <ZoomInButton />
        <ZoomOutButton />
        <FitToScreenButton />
        <FilterRelationshipTypeButton />
      </div>

      {/* Legend */}
      <GraphLegend />

      {/* D3 SVG canvas */}
      <svg ref={svgRef} className="w-full h-full" />

      {/* Hover tooltip */}
      <GraphTooltip />
    </div>
  );
}

// D3 rendering logic
function renderD3Graph(svg: SVGSVGElement, data: GraphData) {
  const { nodes, links } = data;

  const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links)
      .id((d: GraphNode) => d.id)
      .distance(120)
      .strength((d: GraphLink) => d.strength * 0.8))
    .force("charge", d3.forceManyBody().strength(-400))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide(nodeRadius));

  // Node visual encoding:
  // Size:  proportional to activityScore (range: 8px–24px radius)
  // Color: by entity_type (COMPANY=violet, REGULATORY_BODY=blue, INFRASTRUCTURE=rose)
  // Ring:  concentric ring on center entity (anchor node)

  // Link visual encoding:
  // Thickness: proportional to relationship_strength
  // Color:     by relationship_type
  // Label:     shown on hover only (prevents clutter)

  // RELATIONSHIP_TYPE color map:
  // REGULATES:               stroke: #3b82f6 (blue)
  // COMPETES_WITH:           stroke: #8b5cf6 (violet)
  // PARTNERS_WITH:           stroke: #10b981 (emerald)
  // PROVIDES_SERVICE_TO:     stroke: #f59e0b (amber)
  // LICENSED_BY:             stroke: #6366f1 (indigo)
  // ACQUIRED:                stroke: #ef4444 (red)

  // On node click: navigate to entity profile
  // On node hover: show tooltip with entity name, type, signal_count_30d
}
```

### Graph Interaction Model

```
HOVER NODE:    Show tooltip: name, entity_type, signal_count_30d, activity_score
CLICK NODE:    Navigate to entity profile page
HOVER LINK:    Show relationship_type label + strength percentage
RIGHT-CLICK:   Context menu: "Open Profile", "Investigate in CIL", "Pin Node"
DRAG NODE:     Reposition node (local state only)
SCROLL:        Zoom in/out
DOUBLE-CLICK:  Expand node (load second-degree relationships)
```

---

## 6.7 Conversational Intelligence Layer Panel

### Purpose

The CIL panel is an investigation interface, not a chat product. It slides in from the right side over the main content. It is always anchored to a specific signal or entity — it never opens as a blank empty chat screen.

### Layout Blueprint

```
RIGHT DRAWER (420px, slides over main content)
+--------------------------------------------+
|  [← Close]  Investigating Signal           |
|  CBN Circular on Tier 2 Wallets            |
|  [REGULATORY] [CRITICAL] [CBN · T1]        |
+--------------------------------------------+
|  ANCHOR CONTEXT (collapsible)              |
|  Confidence: 0.94 · Urgency: 0.91          |
|  Published: 30 May 2025 · 3 sources        |
+--------------------------------------------+
|                                            |
|  SUGGESTED STARTING QUESTIONS:             |
|  [How does this compare to the 2023 CBN   |
|   circular on transaction limits?]         |
|  [Which operators are in scope?]           |
|  [What was the enforcement pattern in     |
|   2023 after a similar directive?]         |
|                                            |
|  ─────────────────────────────────────    |
|                                            |
|  (Chat history renders here as            |
|   user asks questions)                     |
|                                            |
|  ─────────────────────────────────────    |
|                                            |
|  +--------------------------------------+ |
|  | Ask about this signal...             | |
|  |                                 [→]  | |
|  +--------------------------------------+ |
+--------------------------------------------+
```

### Component Specification

```typescript
// components/cil/CILPanel.tsx

export function CILPanel() {
  const {
    cilPanelOpen,
    cilAnchorType,
    cilAnchorId,
    cilSessionId,
    closeCIL
  } = useStemCogentStore();

  const [messages, setMessages] = useState<CILMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch anchor context (signal or entity)
  const { data: anchorContext } = useQuery({
    queryKey: ['cil-anchor', cilAnchorType, cilAnchorId],
    queryFn: () => fetchCILAnchorContext(cilAnchorType!, cilAnchorId!),
    enabled: !!cilAnchorId && cilPanelOpen,
  });

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const submitQuery = async (queryText: string) => {
    if (!queryText.trim() || isLoading) return;

    const userMessage: CILMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: queryText,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await apiClient.post('/cil/query', {
        query_text: queryText,
        context_anchor: {
          anchor_type: cilAnchorType,
          anchor_id: cilAnchorId
        },
        session_id: cilSessionId
      });

      const assistantMessage: CILMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response.data.data.answer_text,
        citations: response.data.data.citations,
        confidenceIndicator: response.data.data.confidence_indicator,
        followUpSuggestions: response.data.data.follow_up_suggestions,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'error',
        content: 'Unable to retrieve intelligence. Please try again.',
        timestamp: new Date()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {cilPanelOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
            onClick={closeCIL}
          />

          {/* Panel */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="fixed right-0 top-0 bottom-0 z-50 w-[420px]
                       bg-zinc-950 border-l border-zinc-800 flex flex-col
                       shadow-2xl"
          >
            {/* Panel header */}
            <CILPanelHeader
              anchorContext={anchorContext}
              anchorType={cilAnchorType}
              onClose={closeCIL}
            />

            {/* Anchor context summary (collapsible) */}
            {anchorContext && (
              <CILAnchorSummary context={anchorContext} />
            )}

            {/* Message thread */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">

              {/* Suggested queries (shown only when no messages yet) */}
              {messages.length === 0 && anchorContext && (
                <CILSuggestedQueries
                  anchorType={cilAnchorType!}
                  anchorContext={anchorContext}
                  onSelect={submitQuery}
                />
              )}

              {/* Message history */}
              {messages.map(message => (
                <CILMessage key={message.id} message={message} />
              ))}

              {/* Loading indicator */}
              {isLoading && <CILThinkingIndicator />}

              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <CILInputBar
              value={inputValue}
              onChange={setInputValue}
              onSubmit={submitQuery}
              isLoading={isLoading}
              placeholder={`Ask about this ${cilAnchorType?.toLowerCase()}...`}
            />
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
```

### CIL Message Component

```typescript
// components/cil/CILMessage.tsx

function CILAssistantMessage({ message }: { message: CILMessage }) {
  return (
    <div className="space-y-3">
      {/* Answer text */}
      <div className="bg-zinc-900 rounded-xl p-4 border border-zinc-800">
        <p className="text-sm text-zinc-200 leading-relaxed">
          {message.content}
        </p>
      </div>

      {/* Citations (collapsed by default, expandable) */}
      {message.citations && message.citations.length > 0 && (
        <CILCitationsPanel citations={message.citations} />
      )}

      {/* Confidence indicator */}
      {message.confidenceIndicator && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-500">Grounded on:</span>
          <ConfidenceIndicator
            band={message.confidenceIndicator}
            size="sm"
          />
        </div>
      )}

      {/* Follow-up suggestions */}
      {message.followUpSuggestions && message.followUpSuggestions.length > 0 && (
        <div className="space-y-1.5">
          {message.followUpSuggestions.map((suggestion, i) => (
            <button
              key={i}
              className="w-full text-left text-xs text-zinc-500 bg-zinc-900/50
                         rounded-lg px-3 py-2 hover:bg-zinc-900 hover:text-zinc-300
                         transition-colors border border-zinc-800/50"
              onClick={() => submitQuery(suggestion)}
            >
              ↳ {suggestion}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

### CIL Suggested Queries

These are NOT LLM-generated at render time. They are deterministically generated from the anchor signal's domain, entities, and urgency band:

```typescript
function generateSuggestedQueries(
  anchorType: 'SIGNAL' | 'ENTITY',
  anchorContext: SignalContext | EntityContext
): string[] {
  if (anchorType === 'SIGNAL') {
    const { title, primaryDomain, entities, urgencyBand } = anchorContext as SignalContext;
    const primaryEntity = entities[0]?.entityName ?? 'the issuing authority';

    const templates: Record<string, string[]> = {
      REGULATORY: [
        `How does this compare to similar ${primaryEntity} directives in the past 3 years?`,
        `Which operators are specifically in scope for this directive?`,
        `What enforcement actions followed similar directives historically?`
      ],
      COMPETITIVE: [
        `What other strategic signals have emerged from ${primaryEntity} recently?`,
        `What competitive response patterns have been observed in similar situations?`,
        `Is this part of a broader market movement or an isolated signal?`
      ],
      INFRASTRUCTURE: [
        `Has ${primaryEntity} experienced similar incidents before?`,
        `Which payment operators are most exposed to this infrastructure signal?`,
        `How quickly was service restored in historical comparable incidents?`
      ]
    };

    return templates[primaryDomain] ?? [
      `Why is this signal important?`,
      `What should operators pay attention to here?`,
      `Are there historical precedents for this pattern?`
    ];
  }

  // Entity-anchored queries
  const { entityName } = anchorContext as EntityContext;
  return [
    `What strategic direction does ${entityName} appear to be pursuing?`,
    `What operational risks are increasing for ${entityName}?`,
    `What markets is ${entityName} expanding into most aggressively?`
  ];
}
```

---

## 6.8 Alert Center

```typescript
// app/alerts/page.tsx — Full alert management page

// Layout: split view
// Left (40%): Alert list with filter tabs (ALL | CRITICAL | HIGH | UNREAD)
// Right (60%): Selected alert detail (signal dossier lite)

// Alert list item:
// [Red/Amber urgency line] [Title 2 lines] [Domain] [Time]
// [Mark read button] [Investigate →]

// Unread alerts: white text + brighter background
// Read alerts: muted zinc-400 text + standard background
// CRITICAL alerts: persistent red left border (never muted)
```

---

## 6.9 Digest View

```typescript
// app/digests/page.tsx

// Layout:
// - Digest list (left, past digests)
// - Selected digest (right, full content)

// Digest content sections:
// 1. Executive summary (synthesis paragraph)
// 2. Top 5 priority signals (signal cards, compact variant)
// 3. Regulatory watch section
// 4. Competitor movement section
// 5. Infrastructure status (if any signals)

// Actions: Download PDF | Forward via email | Open in new tab
```

---

## 6.10 Settings & Preferences

```typescript
// app/settings/page.tsx
// Tabbed layout: Profile | Alerts | Digest | Team | API Keys

// Alert Preferences tab:
// - Domain subscriptions (checkbox group)
// - Region subscriptions (checkbox group)
// - Entity watchlist (searchable multi-select)
// - Minimum urgency threshold (slider 0.0–1.0)
// - Delivery channels (toggle: Email, Push, In-App)
// - Alert suppression window (time pickers)

// Digest Preferences tab:
// - Frequency (Daily/Weekly/None)
// - Day of week (for weekly)
// - Delivery time (timezone-aware)
```

---

---

# SECTION 7 — DESIGN SYSTEM SPECIFICATION

---

## 7.1 Color Tokens

```css
/* design-tokens.css */

:root {
  /* Background layers */
  --bg-app:       #eeeef2;   /* zinc-950 — main app background */
  --bg-surface:   #f9f9ff;   /* zinc-900 — card/panel background */
  --bg-elevated:  #525253;   /* zinc-800 — dropdown/tooltip/input */
  --bg-hover:     #3f3f46;   /* zinc-700 — hover states */

  /* Content */
  --text-primary:   #000000;  /* zinc-50 — headlines, important labels */
  --text-secondary: #a1a1aa;  /* zinc-400 — body text, descriptions */
  --text-muted:     #2e2d2d;  /* zinc-500 — metadata, timestamps */
  --text-disabled:  #52525b;  /* zinc-600 — disabled states */

  /* Borders */
  --border-subtle:  #27272a;  /* zinc-800 */
  --border-default: #3f3f46;  /* zinc-700 */
  --border-strong:  #52525b;  /* zinc-600 — focused/active borders */

  /* Urgency bands */
  --urgency-critical-bg:    #450a0a;  /* red-950 */
  --urgency-critical-text:  #fca5a5;  /* red-300 */
  --urgency-critical-border:#991b1b;  /* red-800 */
  --urgency-critical-dot:   #ef4444;  /* red-500 */

  --urgency-high-bg:        #451a03;  /* amber-950 */
  --urgency-high-text:      #fcd34d;  /* amber-300 */
  --urgency-high-border:    #92400e;  /* amber-800 */
  --urgency-high-dot:       #f59e0b;  /* amber-500 */

  /* Domain taxonomy colors */
  --domain-regulatory-text:     #93c5fd;  /* blue-300 */
  --domain-regulatory-bg:       #172554;  /* blue-950 */
  --domain-competitive-text:    #c4b5fd;  /* violet-300 */
  --domain-competitive-bg:      #2e1065;  /* violet-950 */
  --domain-consumer-text:       #6ee7b7;  /* emerald-300 */
  --domain-consumer-bg:         #022c22;  /* emerald-950 */
  --domain-financial-text:      #fcd34d;  /* amber-300 */
  --domain-financial-bg:        #451a03;  /* amber-950 */
  --domain-infrastructure-text: #fda4af;  /* rose-300 */
  --domain-infrastructure-bg:   #4c0519;  /* rose-950 */
  --domain-default-text:        #a1a1aa;  /* zinc-400 */
  --domain-default-bg:          #18181b;  /* zinc-900 */

  /* Confidence scale */
  --conf-high:     #22c55e;  /* green-500 */
  --conf-moderate: #f59e0b;  /* amber-500 */
  --conf-low:      #f97316;  /* orange-500 */
  --conf-unknown:  #52525b;  /* zinc-600 */

  /* Interactive */
  --accent-primary: #6366f1;   /* indigo-500 — primary buttons, links */
  --accent-hover:   #818cf8;   /* indigo-400 */

  /* Typography */
  --font-display: 'Playfair Display', Georgia, serif;   /* signal titles */
  --font-body:    'Inter', system-ui, sans-serif;        /* UI chrome, body */
}
```

## 7.2 Typography Scale

```css
/* Only 4 text sizes used across the entire application */

.text-signal-title  { font-size: 1rem;    line-height: 1.4; font-family: var(--font-display); font-weight: 600; }
.text-body          { font-size: 0.875rem; line-height: 1.6; font-family: var(--font-body); font-weight: 400; }
.text-label         { font-size: 0.75rem;  line-height: 1.4; font-family: var(--font-body); font-weight: 500; }
.text-meta          { font-size: 0.6875rem; line-height: 1.4; font-family: var(--font-body); font-weight: 400; }
```

## 7.3 Spacing Scale

Based on 4px base unit. Major spacing values: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64px. Only these values used — no arbitrary spacing.

## 7.4 Component Radius Scale

```
--radius-sm: 8px    (badges, pills, small chips)
--radius-md: 12px   (cards, inputs, buttons)
--radius-lg: 16px   (panels, modals, drawers)
--radius-xl: 20px   (page containers, major sections)
```

---

---

# SECTION 8 — ROUTING & PAGE ARCHITECTURE

---

## 8.1 Route Map

```
app/
├── (auth)/
│   ├── login/page.tsx              → /login
│   └── invite/[token]/page.tsx     → /invite/{token}
│
├── (app)/                          → Protected layout (requires auth)
│   ├── layout.tsx                  → Shell: sidebar + nav + CIL panel
│   ├── dashboard/page.tsx          → /dashboard (Intelligence Feed + Priority Matrix)
│   │
│   ├── signals/
│   │   └── [signalId]/page.tsx     → /signals/{id} (Signal Dossier)
│   │
│   ├── entities/
│   │   ├── page.tsx                → /entities (Entity list + search)
│   │   ├── [entitySlug]/page.tsx   → /entities/{slug} (Entity Profile)
│   │   └── graph/page.tsx          → /entities/graph (Full relationship graph)
│   │
│   ├── alerts/
│   │   └── page.tsx                → /alerts (Alert Center)
│   │
│   ├── digests/
│   │   ├── page.tsx                → /digests (Digest list)
│   │   └── [digestId]/page.tsx     → /digests/{id} (Digest detail)
│   │
│   ├── settings/
│   │   └── page.tsx                → /settings (tabbed: Profile/Alerts/Digest/Team/API)
│   │
│   └── admin/                      → ADMIN role required
│       ├── sources/page.tsx        → /admin/sources
│       ├── taxonomy/page.tsx       → /admin/taxonomy
│       └── audit/page.tsx          → /admin/audit
│
└── api/                            → Next.js API routes (minimal — mostly proxies)
    └── auth/[...nextauth]/         → Auth callback handlers
```

## 8.2 Loading States

Every page and data-fetching component must implement:

1. **Skeleton loading** (not spinner) for content areas — skeletons match the shape of the actual content to prevent layout shift
2. **Optimistic updates** for read/mark-as-read operations — no refetch required
3. **Stale-while-revalidate** via TanStack Query — show cached data immediately, update in background

```typescript
// Skeleton pattern for signal cards
function FeedSkeleton() {
  return (
    <div className="space-y-1">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="rounded-xl border border-zinc-800 bg-zinc-950 p-5 animate-pulse">
          <div className="flex gap-2 mb-3">
            <div className="h-5 w-16 bg-zinc-800 rounded-full" />
            <div className="h-5 w-24 bg-zinc-800 rounded-full" />
          </div>
          <div className="h-4 w-24 bg-zinc-800 rounded mb-3" />
          <div className="h-5 w-3/4 bg-zinc-800 rounded mb-2" />
          <div className="h-4 w-full bg-zinc-800 rounded mb-1" />
          <div className="h-4 w-5/6 bg-zinc-800 rounded mb-4" />
          <div className="flex gap-2">
            <div className="h-7 w-20 bg-zinc-800 rounded-lg" />
            <div className="h-7 w-20 bg-zinc-800 rounded-lg" />
          </div>
        </div>
      ))}
    </div>
  );
}
```

---

---

# SECTION 9 — RESPONSIVE BEHAVIOR & BREAKPOINTS

---

## 9.1 Breakpoints

```
mobile:  < 768px    (sm)
tablet:  768–1023px (md)
desktop: ≥ 1024px   (lg)
wide:    ≥ 1280px   (xl)
```

## 9.2 Responsive Adaptations Per View

| View | Desktop (lg+) | Tablet (md) | Mobile (sm) |
|---|---|---|---|
| App shell | Sidebar (240px) + Main | Sidebar icon-rail (64px) + Main | Bottom nav bar |
| Intelligence Feed | Single column, max 800px centered | Single column, full width | Single column, full width |
| Signal Dossier | 2-column (60/40) | Stacked single column | Stacked single column |
| Entity Profile | 2-column (65/35) | Stacked single column | Stacked single column |
| CIL Panel | Right drawer (420px) | Right drawer (full 100vw overlay) | Full screen sheet |
| Priority Matrix | 2-column cards | 2-column cards | Single column stack |
| Relationship Graph | Full canvas (520px height) | Reduced canvas (360px) | Horizontal scroll |
| Alert Center | Split view (40/60) | Single column, back-nav | Single column, back-nav |

## 9.3 Touch Interactions (Mobile)

- Signal cards: tap to open dossier; swipe left for quick actions (mark read, open CIL)
- CIL panel: swipe down to close
- Entity graph: pinch to zoom; double-tap to expand node
- Navigation: native-feel bottom tab bar with haptic feedback on alert badge

---

---

# SECTION 10 — PERFORMANCE ARCHITECTURE

---

## 10.1 Performance Budgets

| Metric | Target | Measurement |
|---|---|---|
| First Contentful Paint (FCP) | < 1.5s | Lighthouse / Core Web Vitals |
| Largest Contentful Paint (LCP) | < 2.5s | Core Web Vitals |
| Time to Interactive (TTI) | < 3.5s | Lighthouse |
| Cumulative Layout Shift (CLS) | < 0.05 | Core Web Vitals |
| Initial JS bundle (gzipped) | < 200KB | Next.js bundle analyzer |
| API response (feed query) | < 500ms P95 | CloudWatch |
| WebSocket message delivery | < 200ms | Custom metric |
| CIL query P95 response | < 8s | CloudWatch |

## 10.2 Optimization Strategies

**Code splitting:**
- Every page is code-split automatically by Next.js App Router
- D3 graph library loaded dynamically (only on entity/graph pages)
- CIL panel component loaded dynamically (only when first opened)

**Image strategy:**
- No decorative images anywhere in the application
- Entity logos (where available): fetched lazily, displayed with placeholder ring
- All images served via CloudFront with WebP encoding

**Feed virtualization:**
- Signal feed uses windowed rendering via `@tanstack/react-virtual` for feeds > 50 items
- Only visible cards are rendered in DOM; off-screen cards are unmounted

**Cache strategy:**
- API responses cached by TanStack Query (5-minute stale time)
- Feed page pre-fetched on sidebar hover (prefetchQuery)
- Signal dossier pre-fetched on signal card hover (300ms delay threshold)

---

---

# SECTION 11 — ACCESSIBILITY REQUIREMENTS

---

## 11.1 Baseline Requirements

- **WCAG 2.1 Level AA** compliance required for all interactive components
- All color combinations must meet 4.5:1 contrast ratio minimum
- All urgency information must not rely on color alone (must have text label)
- All interactive elements must be keyboard navigable (tab order: logical DOM order)
- All images must have meaningful alt text or be marked `aria-hidden` if decorative
- Focus rings must be visible on all interactive elements (no `outline: none` without replacement)

## 11.2 Screen Reader Considerations

```typescript
// Signal cards use semantic article elements with aria-labels
<article aria-label={`${signal.urgencyBand} urgency signal: ${signal.title}`}>

// Priority matrix communicates urgency semantically
<section aria-label="Priority alert matrix">
  <h2>Requires Attention</h2>
  <div role="list" aria-label="Critical urgency signals">

// CIL chat follows ARIA chat pattern
<div role="log" aria-live="polite" aria-label="Intelligence conversation">

// Confidence indicators use aria-label for screen reader description
<div aria-label={`Confidence: ${band}, ${Math.round(score * 100)}%`}>
```

---

---

# SECTION 12 — ERROR & EMPTY STATE DESIGN

---

## 12.1 Error States

```typescript
// API error: network failure or 5xx
function FeedErrorState() {
  return (
    <div className="rounded-xl border border-red-900/50 bg-red-950/20 p-8 text-center">
      <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-3" />
      <h3 className="text-sm font-semibold text-zinc-200 mb-1">
        Unable to load intelligence feed
      </h3>
      <p className="text-xs text-zinc-500 mb-4">
        The intelligence service is temporarily unavailable.
        Your alerts will continue to be processed in the background.
      </p>
      <Button variant="outline" size="sm" onClick={() => queryClient.refetchQueries()}>
        Retry
      </Button>
    </div>
  );
}

// CIL synthesis failure (LLM unavailable)
// The response itself should explain the degraded state:
// "Intelligence retrieval is operating in reduced mode.
//  This response is based on structured signal data without full synthesis."
```

## 12.2 Empty States

```typescript
// Empty feed (no signals match current filters)
function FeedEmptyState({ filters }: { filters: FeedFilters }) {
  const hasActiveFilters = filters.domains.length > 0 || filters.urgencyBands.length > 0;

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-10 text-center">
      <Inbox className="w-8 h-8 text-zinc-600 mx-auto mb-3" />
      <h3 className="text-sm font-semibold text-zinc-300 mb-1">
        {hasActiveFilters
          ? "No signals match your current filters"
          : "No signals in your feed yet"
        }
      </h3>
      <p className="text-xs text-zinc-600">
        {hasActiveFilters
          ? "Try broadening your domain or urgency filters."
          : "Intelligence signals will appear here as they are processed."
        }
      </p>
      {hasActiveFilters && (
        <Button variant="ghost" size="sm" className="mt-4"
                onClick={() => clearFeedFilters()}>
          Clear filters
        </Button>
      )}
    </div>
  );
}

// Empty CIL (no session yet, signal anchor present)
// Handled by CILSuggestedQueries component — never shows a blank empty state
```

---

---

*Document End — SC-DOC-007 Frontend UX Specification v1.0.0*
*Next Document: SC-DOC-008 Security & Compliance Specification*
