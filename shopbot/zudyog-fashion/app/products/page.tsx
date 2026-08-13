import { PRODUCTS } from "@/lib/products";
import ProductCard from "@/components/ProductCard";
import CategoryFilter from "@/components/CategoryFilter";

export default async function ProductsPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await searchParams;
  const category = typeof params.category === "string" ? params.category : "";
  const occasion = typeof params.occasion === "string" ? params.occasion : "";
  const maxPrice = typeof params.maxPrice === "string" ? params.maxPrice : "";

  let products = PRODUCTS;

  if (category) {
    products = products.filter((p) => p.category === category);
  }
  if (occasion) {
    products = products.filter((p) =>
      p.occasion.toLowerCase().includes(occasion.toLowerCase())
    );
  }
  if (maxPrice) {
    const max = parseInt(maxPrice, 10);
    if (!isNaN(max)) {
      products = products.filter((p) => p.price <= max);
    }
  }

  const heading = category
    ? `${CATEGORY_MAP[category] ?? category} (${products.length})`
    : `All Products (${products.length})`;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-2xl font-bold text-stone-800 mb-6">{heading}</h1>

      <div className="flex flex-col lg:flex-row gap-8">
        {/* Sidebar */}
        <div className="lg:w-52 flex-shrink-0">
          <CategoryFilter
            currentCategory={category}
            currentOccasion={occasion}
            currentMaxPrice={maxPrice}
          />
        </div>

        {/* Grid */}
        <div className="flex-1">
          {products.length === 0 ? (
            <div className="text-center py-20 text-stone-400">
              <p className="text-4xl mb-3">🔍</p>
              <p className="font-medium">No products match your filters.</p>
              <p className="text-sm mt-1">Try removing some filters.</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-4">
              {products.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const CATEGORY_MAP: Record<string, string> = {
  kurta: "Kurtas",
  saree: "Sarees",
  suit: "Suits",
  "coord-set": "Co-ord Sets",
  shawl: "Shawls & Stoles",
  lehenga: "Lehengas",
  dupatta: "Dupattas",
  sharara: "Sharara Sets",
};
