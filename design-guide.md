# Design System & UI/UX Guidelines: SEVAK

SEVAK adopts a WhatsApp-inspired design system. This eliminates technical anxiety for first-time digital users and rural audiences by using recognizable visual patterns.

---

## 1. Color Palette

| Token | Hex Value | Semantic Purpose |
| :--- | :--- | :--- |
| `--app-header` | `#075E54` | Primary WhatsApp deep teal green (App bar) |
| `--app-accent` | `#128C7E` | Secondary emerald green (Active states, icons) |
| `--chat-bg` | `#EFEAE2` | Textured warm beige canvas |
| `--bubble-user` | `#D9FDD3` | Soft light green for user chat bubbles |
| `--bubble-system`| `#FFFFFF` | Pure white for system explanations |
| `--severity-red` | `#DC2626` | Urgent legal alert (15-day notice, court date) |
| `--severity-yellow`| `#D97706` | Warning/Compliance (KYC, fee revision) |
| `--severity-green` | `#16A34A` | Informational (General notice) |
| `--text-primary` | `#111827` | High contrast dark slate for readability |
| `--text-muted` | `#6B7280` | Subtitle and timestamp text |

---

## 2. Typography Rules
- **Font Family:** `Inter`, `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, sans-serif.
- **Hierarchy:**
  - App Bar Title: `16px` (`font-semibold`)
  - Section Headers ("WHAT / WHY / NEXT"): `11px` (`font-bold`, uppercase, tracking-wide)
  - Card Body Text: `13px` (`font-normal`, `leading-snug`)
  - Timestamp & Disclaimers: `10px` (`font-normal`, italicized)

---

## 3. UI Component Constraints
- **Mic Button Behavior:**
  - Normal State: 48px circle, `#075E54` background, white mic icon.
  - Recording State: Expands to 52px circle, `#DC2626` background, surrounded by an animated pulsing ring (`ring-4 ring-red-200`).
- **Do This Today Container:**
  - Background: Amber-50 (`#FFFBEB`).
  - Border: 1px solid Amber-200 (`#FDE68A`).
  - Corner Radius: 6px (`rounded-md`).
- **Citations / Grounding Tag:**
  - Must display an external link icon alongside the text: `Verified Source: Page X, Para Y`.

---

## 4. Icons & Imagery
- **Icon Set:** Exclusively `lucide-react`.
- **Approved Icons:** `Mic`, `Square`, `Paperclip`, `FileText`, `X`, `Play`, `Pause`, `Volume2`, `CheckCheck`, `Send`, `AlertTriangle`, `ExternalLink`.
- **Prohibited:** Custom SVGs, external web fonts, heavy raster assets, or unrelated emoji sets.
