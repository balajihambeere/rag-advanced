import { getProductById, type Product } from "@/lib/products";

// ── Colour name → hex ────────────────────────────────────────────────────────

const COLOR_HEX: Record<string, string> = {
  white: "#FFFFFF", "off white": "#FAF7F0", ivory: "#FFFFF0",
  cream: "#FFFDD0", beige: "#F5F5DC", "natural white": "#FAF9F6",
  "light grey": "#D3D3D3", "charcoal grey": "#36454F", "slate grey": "#708090",
  black: "#1C1C1C", "midnight black": "#0A0A0A",
  red: "#CC0000", "bridal red": "#990000", "deep red": "#8B0000",
  maroon: "#800000", "royal maroon": "#6B0000", "deep maroon": "#5C0000",
  pink: "#FFC0CB", "blush pink": "#FFB6C1", "deep pink": "#FF1493",
  fuchsia: "#FF00FF", "fuchsia pink": "#FF69B4", "dusty rose": "#DCAE96",
  coral: "#FF6B6B", peach: "#FFCBA4", "rose gold": "#B76E79",
  orange: "#FFA500", "rust orange": "#B55A30", "saffron orange": "#FF8C00",
  "burnt orange": "#CC5500", mustard: "#FFDB58", "mustard yellow": "#FFDB58",
  gold: "#FFD700", champagne: "#FAD6A5", "champagne gold": "#C8A96E",
  "sky blue": "#87CEEB", navy: "#000080", "midnight navy": "#191970",
  "royal blue": "#4169E1", "electric blue": "#007FFF",
  "powder blue": "#B0E0E6", "steel blue": "#4682B4",
  "slate blue": "#6A5ACD", "peacock blue": "#005F6B",
  indigo: "#4B0082", "indigo blue": "#4B0082",
  purple: "#800080", "royal purple": "#7851A9", "deep purple": "#673AB7",
  lavender: "#E6E6FA", lilac: "#C8A2C8", magenta: "#FF00FF",
  "magenta pink": "#FF00B4",
  teal: "#008080", "bottle green": "#006A4E", "forest green": "#228B22",
  "sage green": "#B2AC88", emerald: "#50C878", "emerald green": "#50C878",
  turquoise: "#40E0D0", sage: "#77815C", "light olive": "#A8A97F",
  "mint green": "#98FF98", "lime green": "#32CD32", "parrot green": "#4DB800",
  wine: "#722F37", burgundy: "#800020",
  "tropical print": "#20B2AA", "floral print": "#FF69B4",
  "geometric print": "#6A5ACD", "blue watercolour": "#6495ED",
  "pink abstract": "#FFB6C1", "green botanical": "#90EE90",
  "coral floral": "#FF6B6B", "teal abstract": "#008080",
  "lavender paisley": "#E6E6FA", "rose pink": "#FF66CC",
};

function colorHex(name: string): string {
  const key = name.toLowerCase().split(" with ")[0].trim();
  return COLOR_HEX[key] ?? COLOR_HEX[name.toLowerCase()] ?? "#9CA3AF";
}

// ── Per-category design tokens ────────────────────────────────────────────────

interface Design {
  bg1: string; bg2: string; mid: string; accent: string; label: string;
}

const DESIGNS: Record<string, Design> = {
  kurta:      { bg1: "#FFFBEB", bg2: "#FBBF24", mid: "#FCD34D", accent: "#92400E", label: "KURTA"      },
  saree:      { bg1: "#F5F3FF", bg2: "#7C3AED", mid: "#A78BFA", accent: "#4C1D95", label: "SAREE"      },
  suit:       { bg1: "#F0FDFA", bg2: "#0F766E", mid: "#5EEAD4", accent: "#134E4A", label: "SUIT"       },
  "coord-set":{ bg1: "#FFF1F2", bg2: "#E11D48", mid: "#FDA4AF", accent: "#9F1239", label: "CO-ORD SET" },
  shawl:      { bg1: "#F1F5F9", bg2: "#475569", mid: "#94A3B8", accent: "#1E293B", label: "SHAWL"      },
  lehenga:    { bg1: "#FEF2F2", bg2: "#9F1239", mid: "#FCA5A5", accent: "#7F1D1D", label: "LEHENGA"    },
  dupatta:    { bg1: "#EFF6FF", bg2: "#1D4ED8", mid: "#93C5FD", accent: "#1E3A8A", label: "DUPATTA"    },
  sharara:    { bg1: "#ECFDF5", bg2: "#065F46", mid: "#6EE7B7", accent: "#022C22", label: "SHARARA"    },
};

// ── SVG helpers ───────────────────────────────────────────────────────────────

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

// Repeating diamond lattice pattern
function diamondPattern(stroke: string): string {
  return `<defs>
    <pattern id="pat" x="0" y="0" width="28" height="28" patternUnits="userSpaceOnUse">
      <polygon points="14,2 26,14 14,26 2,14" fill="none" stroke="${stroke}" stroke-width="0.6" opacity="0.35"/>
    </pattern>
  </defs>`;
}

// Paisley scatter pattern
function paisleyPattern(stroke: string): string {
  const p = `M0,0 C-4,-12 4,-16 8,-8 C12,0 8,12 0,16 C-4,8 -4,4 0,0Z`;
  return `<defs>
    <pattern id="pat" x="0" y="0" width="36" height="36" patternUnits="userSpaceOnUse">
      <path d="${p}" transform="translate(10,10) rotate(30)" fill="none" stroke="${stroke}" stroke-width="0.7" opacity="0.3"/>
      <path d="${p}" transform="translate(28,25) rotate(-20)" fill="none" stroke="${stroke}" stroke-width="0.7" opacity="0.3"/>
    </pattern>
  </defs>`;
}

// Floral petal pattern
function floralPattern(stroke: string): string {
  const petals = [0,45,90,135,180,225,270,315].map(a =>
    `<ellipse cx="0" cy="-7" rx="2.5" ry="6" transform="rotate(${a})" fill="none" stroke="${stroke}" stroke-width="0.6" opacity="0.35"/>`
  ).join("");
  return `<defs>
    <pattern id="pat" x="0" y="0" width="32" height="32" patternUnits="userSpaceOnUse">
      <g transform="translate(16,16)">${petals}</g>
    </pattern>
  </defs>`;
}

// Wave pattern
function wavePattern(stroke: string): string {
  return `<defs>
    <pattern id="pat" x="0" y="0" width="40" height="20" patternUnits="userSpaceOnUse">
      <path d="M0,10 C10,0 20,0 20,10 C20,20 30,20 40,10" fill="none" stroke="${stroke}" stroke-width="0.8" opacity="0.3"/>
    </pattern>
  </defs>`;
}

function getPattern(category: string, accent: string): string {
  switch (category) {
    case "saree":
    case "suit":
    case "sharara":   return paisleyPattern(accent);
    case "lehenga":
    case "dupatta":   return floralPattern(accent);
    case "shawl":     return wavePattern(accent);
    default:          return diamondPattern(accent);
  }
}

// ── Garment silhouettes ───────────────────────────────────────────────────────

function kurta(fill: string, stroke: string): string {
  return `
  <!-- Kurta body -->
  <path d="M155,108 L148,290 L252,290 L245,108 L228,92 Q200,84 172,92 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5" stroke-linejoin="round"/>
  <!-- Left sleeve -->
  <path d="M155,108 L172,92 L145,96 L112,120 L112,188 L148,178 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5" stroke-linejoin="round"/>
  <!-- Right sleeve -->
  <path d="M245,108 L228,92 L255,96 L288,120 L288,188 L252,178 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5" stroke-linejoin="round"/>
  <!-- V-neckline -->
  <path d="M172,92 Q200,124 228,92" fill="none" stroke="${stroke}" stroke-width="2"/>
  <!-- Hem border lines -->
  <line x1="148" y1="280" x2="252" y2="280" stroke="${stroke}" stroke-width="1.5"/>
  <line x1="150" y1="284" x2="250" y2="284" stroke="${stroke}" stroke-width="0.8" stroke-dasharray="4,3"/>
  <!-- Placket -->
  <line x1="200" y1="108" x2="200" y2="200" stroke="${stroke}" stroke-width="0.8" opacity="0.5"/>`;
}

function saree(fill: string, stroke: string): string {
  return `
  <!-- Saree body drape -->
  <path d="M130,100 L120,290 L210,290 L220,100 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5" opacity="0.9"/>
  <!-- Pallu cascade -->
  <path d="M195,95 C230,110 270,130 280,160 C290,190 280,240 260,270 L260,290 L200,290 L210,260 C225,230 240,190 235,155 C230,120 215,100 195,95 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5" opacity="0.75"/>
  <!-- Saree border (gold line) -->
  <line x1="120" y1="100" x2="120" y2="290" stroke="${stroke}" stroke-width="3"/>
  <path d="M260,270 L260,290" stroke="${stroke}" stroke-width="3"/>
  <!-- Pleats -->
  <line x1="145" y1="105" x2="142" y2="285" stroke="${stroke}" stroke-width="0.6" opacity="0.4"/>
  <line x1="160" y1="102" x2="157" y2="285" stroke="${stroke}" stroke-width="0.6" opacity="0.4"/>
  <line x1="175" y1="100" x2="172" y2="285" stroke="${stroke}" stroke-width="0.6" opacity="0.4"/>
  <!-- Zari border motif hints -->
  <path d="M120,130 Q130,125 140,130 Q130,135 120,130Z" fill="${stroke}" opacity="0.5"/>
  <path d="M120,160 Q130,155 140,160 Q130,165 120,160Z" fill="${stroke}" opacity="0.5"/>
  <path d="M120,190 Q130,185 140,190 Q130,195 120,190Z" fill="${stroke}" opacity="0.5"/>`;
}

function suit(fill: string, stroke: string): string {
  return `
  <!-- Anarkali flared body -->
  <path d="M168,90 L100,290 L300,290 L232,90 Q200,80 168,90 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5" stroke-linejoin="round"/>
  <!-- Left sleeve -->
  <path d="M168,90 L180,82 L148,86 L116,108 L120,168 L152,158 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5"/>
  <!-- Right sleeve -->
  <path d="M232,90 L220,82 L252,86 L284,108 L280,168 L248,158 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5"/>
  <!-- Neckline -->
  <path d="M180,82 Q200,110 220,82" fill="none" stroke="${stroke}" stroke-width="2"/>
  <!-- Yoke embroidery line -->
  <path d="M155,120 Q200,132 245,120" fill="none" stroke="${stroke}" stroke-width="1.2" stroke-dasharray="5,3"/>
  <!-- Hem embroidery -->
  <line x1="100" y1="282" x2="300" y2="282" stroke="${stroke}" stroke-width="1.5"/>
  <line x1="104" y1="286" x2="296" y2="286" stroke="${stroke}" stroke-width="0.8" stroke-dasharray="4,3"/>`;
}

function coordSet(fill: string, stroke: string): string {
  return `
  <!-- Top (crop/boxy) -->
  <path d="M162,92 L158,180 L242,180 L238,92 L224,84 Q200,78 176,84 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5" stroke-linejoin="round"/>
  <!-- Left sleeve (short) -->
  <path d="M162,92 L176,84 L148,88 L126,100 L128,148 L158,142 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5"/>
  <!-- Right sleeve (short) -->
  <path d="M238,92 L224,84 L252,88 L274,100 L272,148 L242,142 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5"/>
  <!-- Neckline -->
  <path d="M176,84 Q200,106 224,84" fill="none" stroke="${stroke}" stroke-width="1.8"/>
  <!-- Gap -->
  <line x1="158" y1="186" x2="242" y2="186" stroke="${stroke}" stroke-width="0.6" stroke-dasharray="4,4" opacity="0.5"/>
  <!-- Straight trousers -->
  <path d="M158,192 L148,290 L196,290 L200,240 L204,290 L252,290 L242,192 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5" stroke-linejoin="round"/>
  <!-- Trouser crease -->
  <line x1="196" y1="192" x2="196" y2="290" stroke="${stroke}" stroke-width="0.8" opacity="0.4"/>`;
}

function shawl(fill: string, stroke: string): string {
  return `
  <!-- Main shawl rectangle -->
  <path d="M100,100 L100,280 L300,280 L300,100 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5"/>
  <!-- Folded corner -->
  <path d="M100,100 L160,100 L100,160 Z"
        fill="${stroke}" opacity="0.2"/>
  <!-- Fringe top -->
  ${Array.from({length:16},(_,i)=>`<line x1="${108+i*12}" y1="100" x2="${108+i*12}" y2="88" stroke="${stroke}" stroke-width="1.2" opacity="0.7"/>`).join("")}
  <!-- Fringe bottom -->
  ${Array.from({length:16},(_,i)=>`<line x1="${108+i*12}" y1="280" x2="${108+i*12}" y2="292" stroke="${stroke}" stroke-width="1.2" opacity="0.7"/>`).join("")}
  <!-- Woven stripe hints -->
  <line x1="100" y1="130" x2="300" y2="130" stroke="${stroke}" stroke-width="0.8" opacity="0.3"/>
  <line x1="100" y1="155" x2="300" y2="155" stroke="${stroke}" stroke-width="0.8" opacity="0.3"/>
  <!-- Embroidery border -->
  <rect x="108" y="108" width="184" height="164" fill="none" stroke="${stroke}" stroke-width="1.2" stroke-dasharray="6,3" opacity="0.5"/>
  <!-- Center paisley motif -->
  <path d="M200,176 C194,164 196,155 200,158 C204,155 206,164 200,176 C197,170 197,166 200,176Z"
        fill="none" stroke="${stroke}" stroke-width="1.5" opacity="0.6"/>`;
}

function lehenga(fill: string, stroke: string): string {
  return `
  <!-- Choli (blouse) -->
  <path d="M174,92 L170,136 L230,136 L226,92 Q200,84 174,92 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5"/>
  <!-- Left sleeve -->
  <path d="M174,92 L186,85 L154,89 L132,102 L134,138 L170,130 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5"/>
  <!-- Right sleeve -->
  <path d="M226,92 L214,85 L246,89 L268,102 L266,138 L230,130 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5"/>
  <!-- Waistband -->
  <rect x="160" y="138" width="80" height="14" rx="4" fill="${stroke}" opacity="0.6"/>
  <!-- Lehenga skirt (big flare) -->
  <path d="M160,152 L60,292 L340,292 L240,152 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5" stroke-linejoin="round"/>
  <!-- Kali (panel) lines -->
  ${Array.from({length:7},(_,i)=>{
    const x1=160+i*11.4, y1=152, x2=60+i*40, y2=290;
    return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${stroke}" stroke-width="0.6" opacity="0.35"/>`;
  }).join("")}
  <!-- Embroidered hem border -->
  <line x1="60" y1="284" x2="340" y2="284" stroke="${stroke}" stroke-width="2.5"/>
  <line x1="62" y1="289" x2="338" y2="289" stroke="${stroke}" stroke-width="1" stroke-dasharray="5,3"/>`;
}

function dupatta(fill: string, stroke: string): string {
  return `
  <!-- Dupatta body — flowing drape -->
  <path d="M80,108 Q130,96 160,108 L170,274 Q130,286 80,274 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5" opacity="0.9"/>
  <path d="M160,108 Q200,96 240,108 L250,274 Q210,286 170,274 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5" opacity="0.75"/>
  <path d="M240,108 Q270,96 320,108 L320,274 Q290,286 250,274 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5" opacity="0.6"/>
  <!-- Top border embroidery -->
  <line x1="80" y1="116" x2="320" y2="116" stroke="${stroke}" stroke-width="2"/>
  <line x1="82" y1="121" x2="318" y2="121" stroke="${stroke}" stroke-width="0.8" stroke-dasharray="5,3"/>
  <!-- Bottom border embroidery -->
  <line x1="80" y1="266" x2="320" y2="266" stroke="${stroke}" stroke-width="2"/>
  <!-- Tassels top -->
  ${Array.from({length:8},(_,i)=>`<line x1="${88+i*32}" y1="108" x2="${88+i*32}" y2="92" stroke="${stroke}" stroke-width="1.5"/>
  <circle cx="${88+i*32}" cy="90" r="2" fill="${stroke}"/>`).join("")}
  <!-- Tassels bottom -->
  ${Array.from({length:8},(_,i)=>`<line x1="${88+i*32}" y1="272" x2="${88+i*32}" y2="288" stroke="${stroke}" stroke-width="1.5"/>
  <circle cx="${88+i*32}" cy="290" r="2" fill="${stroke}"/>`).join("")}`;
}

function sharara(fill: string, stroke: string): string {
  return `
  <!-- Short kurta top -->
  <path d="M168,88 L162,172 L238,172 L232,88 Q200,80 168,88 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5" stroke-linejoin="round"/>
  <!-- Sleeves -->
  <path d="M168,88 L180,81 L148,85 L124,98 L126,150 L160,142 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5"/>
  <path d="M232,88 L220,81 L252,85 L276,98 L274,150 L240,142 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5"/>
  <!-- Neckline -->
  <path d="M180,81 Q200,106 220,81" fill="none" stroke="${stroke}" stroke-width="2"/>
  <!-- Waistband -->
  <rect x="156" y="173" width="88" height="12" rx="4" fill="${stroke}" opacity="0.5"/>
  <!-- Left wide flare sharara leg -->
  <path d="M156,185 L64,292 L172,292 L200,220 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5" stroke-linejoin="round"/>
  <!-- Right wide flare sharara leg -->
  <path d="M244,185 L336,292 L228,292 L200,220 Z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.5" stroke-linejoin="round"/>
  <!-- Kali lines on sharara -->
  <line x1="156" y1="185" x2="80" y2="288" stroke="${stroke}" stroke-width="0.6" opacity="0.35"/>
  <line x1="244" y1="185" x2="320" y2="288" stroke="${stroke}" stroke-width="0.6" opacity="0.35"/>
  <!-- Hem border -->
  <line x1="64" y1="285" x2="172" y2="285" stroke="${stroke}" stroke-width="2"/>
  <line x1="228" y1="285" x2="336" y2="285" stroke="${stroke}" stroke-width="2"/>`;
}

function garment(category: string, fill: string, stroke: string): string {
  switch (category) {
    case "saree":     return saree(fill, stroke);
    case "suit":      return suit(fill, stroke);
    case "coord-set": return coordSet(fill, stroke);
    case "shawl":     return shawl(fill, stroke);
    case "lehenga":   return lehenga(fill, stroke);
    case "dupatta":   return dupatta(fill, stroke);
    case "sharara":   return sharara(fill, stroke);
    default:          return kurta(fill, stroke);  // kurta
  }
}

// ── Corner ornament ───────────────────────────────────────────────────────────

function cornerOrnaments(stroke: string): string {
  const corner = `M0,0 L18,0 L0,18Z M2,2 L14,2 L2,14Z`;
  return `
  <path d="${corner}" transform="translate(8,8)"                fill="${stroke}" opacity="0.35"/>
  <path d="${corner}" transform="translate(392,8) scale(-1,1)"  fill="${stroke}" opacity="0.35"/>
  <path d="${corner}" transform="translate(8,392) scale(1,-1)"  fill="${stroke}" opacity="0.35"/>
  <path d="${corner}" transform="translate(392,392) scale(-1,-1)" fill="${stroke}" opacity="0.35"/>`;
}

// ── Full SVG ──────────────────────────────────────────────────────────────────

function buildSVG(product: Product): string {
  const d = DESIGNS[product.category] ?? DESIGNS.kurta;
  const primary   = colorHex(product.colors[0] ?? "");
  const secondary = colorHex(product.colors[1] ?? product.colors[0] ?? "");
  const name    = esc(truncate(product.name, 32));
  const fabric  = esc(truncate(product.fabric, 38));
  const price   = `₹${product.price.toLocaleString("en-IN")}`;
  const swatches = product.colors.slice(0, 5);

  const swatchSVG = swatches.map((c, i) => {
    const hex = colorHex(c);
    const cx = 200 + (i - (swatches.length - 1) / 2) * 24;
    return `<circle cx="${cx}" cy="345" r="10" fill="${hex}" stroke="white" stroke-width="2"/>`;
  }).join("\n  ");

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg width="400" height="420" viewBox="0 0 400 420"
     xmlns="http://www.w3.org/2000/svg" role="img" aria-label="${name}">

  ${getPattern(product.category, d.accent)}

  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1" gradientUnits="objectBoundingBox">
      <stop offset="0%"   stop-color="${d.bg1}"/>
      <stop offset="100%" stop-color="${d.mid}"/>
    </linearGradient>
    <linearGradient id="card" x1="0" y1="0" x2="0" y2="1" gradientUnits="objectBoundingBox">
      <stop offset="0%"   stop-color="#ffffff"/>
      <stop offset="100%" stop-color="#fdf8f3"/>
    </linearGradient>
    <linearGradient id="gfill" x1="0" y1="0" x2="0" y2="1" gradientUnits="objectBoundingBox">
      <stop offset="0%"   stop-color="${primary}"   stop-opacity="0.85"/>
      <stop offset="100%" stop-color="${secondary}" stop-opacity="0.75"/>
    </linearGradient>
  </defs>

  <!-- Background -->
  <rect width="400" height="420" fill="url(#bg)"/>
  <rect width="400" height="370" fill="url(#pat)" opacity="1"/>

  <!-- Garment illustration -->
  <g transform="translate(0, 10)">
    ${garment(product.category, "url(#gfill)", d.accent)}
  </g>

  <!-- Corner ornaments -->
  ${cornerOrnaments(d.accent)}

  <!-- Category badge -->
  <rect x="12" y="12" width="${d.label.length * 8 + 20}" height="26" rx="13" fill="${d.accent}" opacity="0.85"/>
  <text x="${d.label.length * 4 + 22}" y="29" text-anchor="middle"
        font-family="'Georgia',serif" font-size="10" font-weight="bold"
        letter-spacing="1.5" fill="white">${d.label}</text>

  <!-- Colour swatches strip -->
  ${swatchSVG}

  <!-- Info card -->
  <rect x="0" y="366" width="400" height="54" fill="url(#card)"/>
  <line x1="0" y1="366" x2="400" y2="366" stroke="${d.accent}" stroke-width="1.5"/>

  <!-- Product name -->
  <text x="16" y="388" font-family="'Georgia',serif" font-size="14.5"
        font-weight="bold" fill="#1C1C1C">${name}</text>

  <!-- Fabric in italics -->
  <text x="16" y="405" font-family="'Georgia',serif" font-size="10.5"
        font-style="italic" fill="#6B7280">${fabric}</text>

  <!-- Price -->
  <text x="384" y="405" text-anchor="end"
        font-family="'Georgia',serif" font-size="14" font-weight="bold"
        fill="${d.accent}">${price}</text>

  <!-- zUdyog watermark -->
  <text x="384" y="416" text-anchor="end"
        font-family="Arial,sans-serif" font-size="8" fill="#D1D5DB" opacity="0.7">zUdyog Fashion</text>

</svg>`;
}

// ── Route handler ─────────────────────────────────────────────────────────────

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const product = getProductById(id);

  if (!product) {
    return new Response("Product not found", { status: 404 });
  }

  return new Response(buildSVG(product), {
    headers: {
      "Content-Type": "image/svg+xml; charset=utf-8",
      "Cache-Control": "public, max-age=86400, stale-while-revalidate=3600",
    },
  });
}
