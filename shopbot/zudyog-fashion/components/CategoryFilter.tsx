"use client";

import { useRouter, usePathname } from "next/navigation";
import { CATEGORY_LABELS } from "@/lib/products";

interface FilterProps {
  currentCategory: string;
  currentOccasion: string;
  currentMaxPrice: string;
}

export default function CategoryFilter({
  currentCategory,
  currentOccasion,
  currentMaxPrice,
}: FilterProps) {
  const router = useRouter();
  const pathname = usePathname();

  function navigate(params: Record<string, string>) {
    const sp = new URLSearchParams();
    if (params.category) sp.set("category", params.category);
    if (params.occasion) sp.set("occasion", params.occasion);
    if (params.maxPrice) sp.set("maxPrice", params.maxPrice);
    router.push(`${pathname}?${sp.toString()}`);
  }

  function setCategory(cat: string) {
    navigate({ category: cat, occasion: currentOccasion, maxPrice: currentMaxPrice });
  }

  function setMaxPrice(price: string) {
    navigate({ category: currentCategory, occasion: currentOccasion, maxPrice: price });
  }

  function clearAll() {
    router.push(pathname);
  }

  const hasFilters = currentCategory || currentOccasion || currentMaxPrice;

  return (
    <aside className="w-full">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-stone-700">Filter</h2>
        {hasFilters && (
          <button
            onClick={clearAll}
            className="text-xs text-[#8B1A1A] hover:underline"
          >
            Clear all
          </button>
        )}
      </div>

      {/* Category */}
      <div className="mb-6">
        <p className="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-2">
          Category
        </p>
        <ul className="space-y-1">
          <li>
            <button
              onClick={() => setCategory("")}
              className={`w-full text-left text-sm px-2 py-1.5 rounded-md transition-colors ${
                !currentCategory
                  ? "bg-[#8B1A1A] text-white font-medium"
                  : "text-stone-600 hover:bg-stone-100"
              }`}
            >
              All Categories
            </button>
          </li>
          {Object.entries(CATEGORY_LABELS).map(([slug, label]) => (
            <li key={slug}>
              <button
                onClick={() => setCategory(slug)}
                className={`w-full text-left text-sm px-2 py-1.5 rounded-md transition-colors ${
                  currentCategory === slug
                    ? "bg-[#8B1A1A] text-white font-medium"
                    : "text-stone-600 hover:bg-stone-100"
                }`}
              >
                {label}
              </button>
            </li>
          ))}
        </ul>
      </div>

      {/* Price */}
      <div className="mb-6">
        <p className="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-2">
          Max Price
        </p>
        <ul className="space-y-1">
          {[
            { label: "All prices", value: "" },
            { label: "Under ₹1,000", value: "1000" },
            { label: "Under ₹2,000", value: "2000" },
            { label: "Under ₹5,000", value: "5000" },
            { label: "Under ₹10,000", value: "10000" },
          ].map(({ label, value }) => (
            <li key={value}>
              <button
                onClick={() => setMaxPrice(value)}
                className={`w-full text-left text-sm px-2 py-1.5 rounded-md transition-colors ${
                  currentMaxPrice === value
                    ? "bg-[#8B1A1A] text-white font-medium"
                    : "text-stone-600 hover:bg-stone-100"
                }`}
              >
                {label}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
