import Link from "next/link";

export default function Footer() {
  return (
    <footer className="bg-stone-900 text-stone-300 mt-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-8">
          <div>
            <p className="text-xl font-bold text-white mb-1">zUdyog Fashion</p>
            <p className="text-sm text-stone-400">
              Celebrating the art of Indian textiles. Handcrafted, ethical, and timeless.
            </p>
          </div>
          <div>
            <p className="font-semibold text-white mb-3">Shop</p>
            <ul className="space-y-2 text-sm">
              {["Kurtas", "Sarees", "Suits", "Lehengas", "Co-ord Sets"].map((c) => (
                <li key={c}>
                  <Link
                    href={`/products?category=${c.toLowerCase().replace(" ", "-")}`}
                    className="hover:text-[#C9A84C] transition-colors"
                  >
                    {c}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="font-semibold text-white mb-3">Help</p>
            <ul className="space-y-2 text-sm">
              <li>Returns &amp; Exchanges</li>
              <li>Size Guide</li>
              <li>
                <a href="mailto:support@zudyog.com" className="hover:text-[#C9A84C] transition-colors">
                  support@zudyog.com
                </a>
              </li>
            </ul>
          </div>
        </div>
        <div className="border-t border-stone-700 mt-8 pt-6 text-xs text-stone-500 text-center">
          © {new Date().getFullYear()} zUdyog Fashion. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
