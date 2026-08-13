import Link from "next/link";
import { getFeaturedProducts, CATEGORY_LABELS, CATEGORY_COLORS, PRODUCTS } from "@/lib/products";
import ProductCard from "@/components/ProductCard";
import OpenChatButton from "@/components/OpenChatButton";

export default function HomePage() {
  const featured = getFeaturedProducts(8);

  return (
    <div>
      {/* Hero */}
      <section className="bg-linear-to-br from-[#8B1A1A] via-[#6B1414] to-[#3D0B0B] text-white py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-[#C9A84C] uppercase tracking-[0.3em] text-xs font-semibold mb-4">
            Handcrafted Indian Ethnic Wear
          </p>
          <h1 className="text-4xl sm:text-5xl font-bold leading-tight mb-6">
            Wear the Art of India
          </h1>
          <p className="text-red-200 text-lg mb-8 max-w-2xl mx-auto">
            50+ curated outfits — from everyday cotton kurtas to bridal Banarasi silk.
            Each piece tells a story of craft, heritage, and tradition.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              href="/products"
              className="bg-[#C9A84C] text-stone-900 font-semibold px-8 py-3 rounded-full hover:bg-[#B8973B] transition-colors"
            >
              Shop the Collection
            </Link>
            <OpenChatButton />
          </div>
          <p className="text-red-300 text-sm mt-4">
            {PRODUCTS.length} products across {Object.keys(CATEGORY_LABELS).length} categories
          </p>
        </div>
      </section>

      {/* Category Grid */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-14">
        <h2 className="text-2xl font-bold text-stone-800 mb-2">Browse by Category</h2>
        <p className="text-stone-500 mb-8">From casual cotton to bridal silk — find your style.</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {Object.entries(CATEGORY_LABELS).map(([slug, label]) => {
            const colors = CATEGORY_COLORS[slug] ?? { bg: "bg-stone-100", text: "text-stone-700", accent: "bg-stone-400" };
            const count = PRODUCTS.filter((p) => p.category === slug).length;
            return (
              <Link
                key={slug}
                href={`/products?category=${slug}`}
                className={`${colors.bg} rounded-2xl p-5 group hover:shadow-md transition-all`}
              >
                <span className="text-3xl block mb-2">{categoryEmoji(slug)}</span>
                <p className={`font-semibold text-sm ${colors.text}`}>{label}</p>
                <p className="text-xs text-stone-400 mt-0.5">{count} items</p>
              </Link>
            );
          })}
        </div>
      </section>

      {/* Featured Products */}
      <section className="bg-white py-14">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-end justify-between mb-8">
            <div>
              <h2 className="text-2xl font-bold text-stone-800 mb-1">Featured Picks</h2>
              <p className="text-stone-500">Our most-loved styles this season.</p>
            </div>
            <Link
              href="/products"
              className="text-sm text-[#8B1A1A] font-medium hover:underline hidden sm:block"
            >
              View all →
            </Link>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {featured.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
          <div className="text-center mt-8 sm:hidden">
            <Link
              href="/products"
              className="inline-block text-sm text-[#8B1A1A] font-medium border border-[#8B1A1A] px-6 py-2 rounded-full hover:bg-[#8B1A1A] hover:text-white transition-colors"
            >
              View all products →
            </Link>
          </div>
        </div>
      </section>

      {/* AI Stylist CTA */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-14">
        <div className="bg-linear-to-r from-[#FDF6EC] to-amber-50 border border-[#C9A84C]/30 rounded-3xl p-8 sm:p-12 text-center">
          <span className="text-5xl mb-4 block">🛍️</span>
          <h2 className="text-2xl sm:text-3xl font-bold text-stone-800 mb-3">
            Not sure what to pick?
          </h2>
          <p className="text-stone-500 mb-6 max-w-xl mx-auto">
            Our AI stylist knows every fabric, occasion, and size in our collection.
            Ask anything — from "what to wear for a mehendi" to "best cotton kurta under ₹1,000".
          </p>
          <p className="text-sm text-stone-400 mt-4">
            Click the 💬 button in the bottom-right corner to chat.
          </p>
        </div>
      </section>
    </div>
  );
}

function categoryEmoji(category: string): string {
  const map: Record<string, string> = {
    kurta: "👘",
    saree: "🥻",
    suit: "✨",
    "coord-set": "👗",
    shawl: "🧣",
    lehenga: "💃",
    dupatta: "🌸",
    sharara: "🎊",
  };
  return map[category] ?? "👗";
}
