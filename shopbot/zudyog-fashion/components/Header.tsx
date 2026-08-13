import Link from "next/link";
import { CATEGORY_LABELS } from "@/lib/products";

export default function Header() {
  return (
    <header className="sticky top-0 z-40 bg-white border-b border-stone-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl font-bold text-[#8B1A1A] tracking-tight">
              zUdyog
            </span>
            <span className="text-sm font-medium text-[#C9A84C] uppercase tracking-widest hidden sm:block">
              Fashion
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-1">
            {Object.entries(CATEGORY_LABELS).map(([slug, label]) => (
              <Link
                key={slug}
                href={`/products?category=${slug}`}
                className="px-3 py-1.5 text-sm text-stone-600 hover:text-[#8B1A1A] hover:bg-[#FDF6EC] rounded-md transition-colors"
              >
                {label}
              </Link>
            ))}
          </nav>

          <Link
            href="/products"
            className="bg-[#8B1A1A] text-white text-sm font-medium px-4 py-2 rounded-full hover:bg-[#6B1414] transition-colors"
          >
            Shop All
          </Link>
        </div>

        {/* Mobile category scroll */}
        <div className="md:hidden flex gap-2 pb-2 overflow-x-auto scrollbar-hide">
          {Object.entries(CATEGORY_LABELS).map(([slug, label]) => (
            <Link
              key={slug}
              href={`/products?category=${slug}`}
              className="whitespace-nowrap text-xs px-3 py-1 border border-stone-300 rounded-full text-stone-600 hover:border-[#8B1A1A] hover:text-[#8B1A1A] transition-colors"
            >
              {label}
            </Link>
          ))}
        </div>
      </div>
    </header>
  );
}
