# AI Identity - Brand Assets Guide

## 🎨 Logo Components

### AIIdentityLogo (Full Logo)
The main logo with icon, text, and tagline.

```tsx
import { AIIdentityLogo } from './components/AIIdentityLogo';

// Primary version (recommended for dark backgrounds)
<AIIdentityLogo variant="primary" className="w-[400px]" />

// Light version (alternative)
<AIIdentityLogo variant="light" className="w-[400px]" />

// Dark version (for light backgrounds)
<AIIdentityLogo variant="dark" className="w-[400px]" />
```

**Props:**
- `variant`: `'primary'` | `'light'` | `'dark'`
- `className`: Standard className for styling

### AIIdentityLogoCompact (Icon Only)
Compact version for small spaces like favicons, mobile headers, etc.

```tsx
import { AIIdentityLogoCompact } from './components/AIIdentityLogo';

<AIIdentityLogoCompact variant="primary" className="w-12 h-12" />
```

## 🔲 Background Patterns

### GridBackground (Static Patterns)

**Dot Grid** - Subtle minimal dots
```tsx
import { GridBackground } from './components/GridBackground';

<div className="relative">
  <GridBackground variant="dots" opacity={0.15} />
  {/* Your content */}
</div>
```

**Line Grid** - Clean geometric grid
```tsx
<GridBackground variant="lines" opacity={0.12} />
```

**Circuit Grid** - Technical pattern with circuit nodes
```tsx
<GridBackground variant="circuit" opacity={0.2} />
```

**Props:**
- `variant`: `'dots'` | `'lines'` | `'circuit'`
- `opacity`: Number (0-1), recommended: 0.1-0.2
- `className`: Optional className

### AnimatedGridBackground (Animated Pattern)

Subtle pulse animation with glowing nodes - perfect for hero sections.

```tsx
import { AnimatedGridBackground } from './components/GridBackground';

<div className="relative min-h-screen">
  <AnimatedGridBackground opacity={0.1} />
  {/* Hero content */}
</div>
```

## 📋 Usage Examples

### Hero Section with Background
```tsx
function HeroSection() {
  return (
    <div className="relative min-h-screen bg-[#0A0A0B] overflow-hidden">
      {/* Animated grid background */}
      <AnimatedGridBackground opacity={0.08} />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-8">
        <AIIdentityLogo variant="primary" className="w-[500px] mb-8" />
        <h1 className="text-6xl font-bold text-white text-center">
          Okta for AI agents, not humans
        </h1>
      </div>
    </div>
  );
}
```

### Card with Background Pattern
```tsx
function FeatureCard() {
  return (
    <div className="relative bg-[#0A0A0B] rounded-lg border border-[#00FFC2]/20 p-8 overflow-hidden">
      {/* Subtle circuit pattern */}
      <GridBackground variant="circuit" opacity={0.1} />

      {/* Card content */}
      <div className="relative z-10">
        <h3 className="text-2xl font-bold text-white mb-4">
          SOC 2 Ready
        </h3>
        <p className="text-gray-300">
          Built-in compliance from day one
        </p>
      </div>
    </div>
  );
}
```

### Navigation Header with Logo
```tsx
function Header() {
  return (
    <header className="bg-[#0A0A0B] border-b border-[#00FFC2]/10 px-8 py-4">
      <div className="flex items-center justify-between max-w-7xl mx-auto">
        <AIIdentityLogo variant="primary" className="h-10" />
        <nav className="flex gap-6">
          {/* Navigation items */}
        </nav>
      </div>
    </header>
  );
}
```

## 🎨 Color Palette

```css
/* Primary Colors */
--bg-dark: #0A0A0B;      /* Main background */
--primary: #00FFC2;      /* Primary brand color */
--text-light: #F7F1E3;   /* Light text */

/* Usage */
background: #0A0A0B
color: #00FFC2
border: rgba(0, 255, 194, 0.2)  /* 20% opacity */
```

## 📏 Spacing & Sizing Guidelines

**Logo Sizes:**
- Large hero: `w-[400px]` - `w-[500px]`
- Medium header: `w-[200px]` - `w-[300px]`
- Small header: `h-10` or `h-12`
- Compact icon: `w-12 h-12` to `w-16 h-16`

**Background Opacity:**
- Hero sections: 0.08 - 0.12
- Cards/panels: 0.1 - 0.15
- Subtle accents: 0.05 - 0.1

**Grid Sizes:**
- Dots: 40px spacing
- Lines: 60px spacing
- Circuit: 100px spacing

## ✅ Best Practices

**Do:**
- Use primary (#00FFC2) logo on dark backgrounds
- Keep background patterns subtle (opacity 0.1-0.2)
- Maintain clear space around logo
- Use compact logo for small spaces
- Layer content with `relative z-10` over backgrounds

**Don't:**
- Don't rotate or distort the logo
- Don't use low contrast combinations
- Don't make background patterns too prominent
- Don't alter logo proportions or colors
- Don't stack multiple backgrounds

## 🔗 Quick Access

Visit `/brand` in your app to see a live showcase of all logo variations and background patterns with interactive examples.

## 🎯 Logo Concept

The logo features:
- **Shield shape**: Represents security and protection
- **Circuit nodes**: Connected nodes symbolize AI agent networks
- **Technical aesthetic**: Clean, modern design for developer audience
- **"Okta for AI agents"**: Clear positioning tagline

The design balances security (shield) with technology (circuit connections) to communicate both the protective nature of the product and its AI-focused purpose.
