import { notFound } from "next/navigation";
import Link from "next/link";
import { getProductById, CATEGORY_COLORS, CATEGORY_LABELS, PRODUCTS } from "@/lib/products";
import { getProductImage } from "@/lib/product-images";
import AskAIButton from "./AskAIButton";

export async function generateStaticParams() {
  return PRODUCTS.map((p) => ({ id: p.id }));
}

export default async function ProductPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const product = getProductById(id);

  if (!product) notFound();

  const colors = CATEGORY_COLORS[product.category] ?? {
    bg: "bg-stone-100",
    text: "text-stone-700",
    accent: "bg-stone-500",
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Breadcrumb */}
      <nav className="text-sm text-stone-400 mb-6 flex items-center gap-2">
        <Link href="/" className="hover:text-[#8B1A1A] transition-colors">
          Home
        </Link>
        <span>/</span>
        <Link
          href={`/products?category=${product.category}`}
          className="hover:text-[#8B1A1A] transition-colors"
        >
          {CATEGORY_LABELS[product.category] ?? product.category}
        </Link>
        <span>/</span>
        <span className="text-stone-600">{product.name}</span>
      </nav>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-10">
        {/* Unique product image from Unsplash */}
        <div className="rounded-2xl overflow-hidden border border-stone-200">
          <img
            src={getProductImage(product.id, product.category)}
            alt={product.name}
            width={800}
            height={900}
            className="w-full object-cover"
          />
        </div>

        {/* Details */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span
              className={`${colors.accent} text-white text-xs font-bold px-2 py-0.5 rounded-full uppercase tracking-wide`}
            >
              {product.stock_status}
            </span>
            <span className="text-xs text-stone-400">{product.id}</span>
          </div>

          <h1 className="text-2xl font-bold text-stone-800 mb-1">{product.name}</h1>
          <p className="text-stone-500 text-sm mb-4">{product.fabric}</p>
          <p className="text-3xl font-bold text-[#8B1A1A] mb-4">
            ₹{product.price.toLocaleString("en-IN")}
          </p>

          <p className="text-stone-600 leading-relaxed mb-5">{product.description}</p>

          {/* Occasion */}
          <div className="mb-4">
            <p className="text-xs font-semibold text-stone-400 uppercase tracking-wide mb-1">
              Occasion
            </p>
            <div className="flex flex-wrap gap-2">
              {product.occasion.split(",").map((o) => (
                <span
                  key={o}
                  className="text-xs border border-stone-300 rounded-full px-3 py-1 text-stone-600"
                >
                  {o.trim()}
                </span>
              ))}
            </div>
          </div>

          {/* Colours */}
          <div className="mb-4">
            <p className="text-xs font-semibold text-stone-400 uppercase tracking-wide mb-1">
              Available Colours
            </p>
            <div className="flex flex-wrap gap-2">
              {product.colors.map((c) => (
                <span
                  key={c}
                  className="text-xs bg-stone-100 rounded-full px-3 py-1 text-stone-700"
                >
                  {c}
                </span>
              ))}
            </div>
          </div>

          {/* Sizes */}
          <div className="mb-6">
            <p className="text-xs font-semibold text-stone-400 uppercase tracking-wide mb-1">
              Sizes
            </p>
            <div className="flex flex-wrap gap-2">
              {product.sizes.map((s) => (
                <span
                  key={s}
                  className="text-xs border border-stone-300 rounded-md px-3 py-1 text-stone-700 font-medium"
                >
                  {s}
                </span>
              ))}
            </div>
          </div>

          {/* Ask AI */}
          <AskAIButton productName={product.name} />
        </div>
      </div>

      {/* Info accordion */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
        <InfoBox title="Return Policy" content={product.return_policy} />
        <InfoBox title="Exchange Policy" content={product.exchange_policy} />
        <InfoBox title="Care Instructions" content={product.care_instructions} />
      </div>

      {/* FAQs */}
      {product.faqs.length > 0 && (
        <div className="mb-10">
          <h2 className="text-lg font-bold text-stone-800 mb-4">
            Frequently Asked Questions
          </h2>
          <div className="space-y-4">
            {product.faqs.map((faq, i) => (
              <div key={i} className="border border-stone-200 rounded-xl p-5">
                <p className="font-semibold text-stone-800 mb-2">{faq.question}</p>
                <p className="text-stone-500 text-sm leading-relaxed">{faq.answer}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function InfoBox({ title, content }: { title: string; content: string }) {
  return (
    <div className="bg-white border border-stone-200 rounded-xl p-5">
      <p className="text-xs font-semibold text-stone-400 uppercase tracking-wide mb-2">
        {title}
      </p>
      <p className="text-sm text-stone-600 leading-relaxed">{content}</p>
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
