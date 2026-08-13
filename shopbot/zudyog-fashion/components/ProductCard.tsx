import Link from "next/link";
import { Product } from "@/lib/products";
import { getProductImage } from "@/lib/product-images";

export default function ProductCard({ product }: { product: Product }) {
  const imgSrc = getProductImage(product.id, product.category);
  return (
    <Link href={`/products/${product.id}`} className="group block">
      <div className="rounded-xl overflow-hidden border border-stone-200 hover:border-[#8B1A1A] hover:shadow-lg transition-all duration-200 bg-white">
        <div className="relative overflow-hidden">
          <img
            src={imgSrc}
            alt={product.name}
            width={400}
            height={420}
            className="w-full object-cover group-hover:scale-[1.02] transition-transform duration-300"
            loading="lazy"
          />
        </div>

        <div className="p-3">
          <h3 className="font-semibold text-stone-800 group-hover:text-[#8B1A1A] transition-colors leading-snug line-clamp-2 text-sm">
            {product.name}
          </h3>
          <div className="flex items-center justify-between mt-2">
            <span className="text-base font-bold text-[#8B1A1A]">
              ₹{product.price.toLocaleString("en-IN")}
            </span>
            <span className="text-[10px] text-stone-400 uppercase tracking-wide">
              {product.category}
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}
