import { useState, useMemo } from 'react';
import store from '../data/store.json';

const CATEGORIES = [
  'All',
  'Precision Parts',
  'Electronics',
  'Hardware Kits',
  'Complete Modules',
  'Full Camera',
  'Accessories',
];

const SORT_OPTIONS = [
  { value: 'category', label: 'By Category' },
  { value: 'price-asc', label: 'Price: Low to High' },
  { value: 'price-desc', label: 'Price: High to Low' },
  { value: 'name', label: 'By Name' },
];

function ProductCard({ product }) {
  return (
    <div className="group bg-zinc-800/50 border border-zinc-700 rounded-lg p-5 hover:border-amber-500/50 hover:bg-zinc-800 transition-all duration-200 flex flex-col">
      {/* Header with SKU and stock indicator */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider">
          {product.sku}
        </span>
        <span
          className={`flex items-center gap-1.5 text-[10px] font-medium ${
            product.inStock ? 'text-green-400' : 'text-red-400'
          }`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              product.inStock ? 'bg-green-400' : 'bg-red-400'
            }`}
          />
          {product.inStock ? 'In Stock' : 'Out of Stock'}
        </span>
      </div>

      {/* Product name */}
      <h3 className="text-base font-semibold text-zinc-100 group-hover:text-amber-400 transition-colors leading-tight mb-2">
        {product.name}
      </h3>

      {/* Description */}
      <p className="text-sm text-zinc-400 leading-relaxed mb-3 flex-1">
        {product.description}
      </p>

      {/* Tags */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {product.tags.slice(0, 4).map((tag) => (
          <span
            key={tag}
            className="px-2 py-0.5 bg-zinc-700/60 text-zinc-400 text-[10px] rounded-full font-medium"
          >
            {tag}
          </span>
        ))}
        {product.tags.length > 4 && (
          <span className="px-2 py-0.5 text-zinc-500 text-[10px] font-medium">
            +{product.tags.length - 4}
          </span>
        )}
      </div>

      {/* Bottom row: price, compatibility badge, lead time */}
      <div className="flex items-end justify-between mt-auto pt-3 border-t border-zinc-700/50">
        <div>
          <div className="text-xl font-bold text-amber-500 font-mono">
            ${product.price.toFixed(2)}
          </div>
          <div className="text-[10px] text-zinc-500 mt-0.5">
            {product.leadTime} day lead time
          </div>
        </div>
        <span className="px-2 py-0.5 bg-amber-600/15 text-amber-500 text-[10px] font-mono font-bold rounded border border-amber-600/30">
          v1.0
        </span>
      </div>
    </div>
  );
}

export default function Store() {
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [sortBy, setSortBy] = useState('category');

  const filteredAndSorted = useMemo(() => {
    let items = [...store];

    // Filter
    if (selectedCategory !== 'All') {
      items = items.filter((item) => item.category === selectedCategory);
    }

    // Sort
    switch (sortBy) {
      case 'price-asc':
        items.sort((a, b) => a.price - b.price);
        break;
      case 'price-desc':
        items.sort((a, b) => b.price - a.price);
        break;
      case 'name':
        items.sort((a, b) => a.name.localeCompare(b.name));
        break;
      case 'category':
      default:
        items.sort((a, b) => {
          const catOrder = CATEGORIES.indexOf(a.category) - CATEGORIES.indexOf(b.category);
          if (catOrder !== 0) return catOrder;
          return a.price - b.price;
        });
        break;
    }

    return items;
  }, [selectedCategory, sortBy]);

  const totalItems = store.length;
  const displayCount = filteredAndSorted.length;

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-3xl font-bold text-zinc-100">Store</h1>
        <p className="text-zinc-400 mt-1">
          Individual parts, pre-assembled modules, and complete camera kits.
          Every part is replaceable.
        </p>
      </div>

      {/* Filter tabs + sort */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* Category tabs */}
        <div className="flex flex-wrap gap-1.5">
          {CATEGORIES.map((cat) => {
            const isActive = selectedCategory === cat;
            const count = cat === 'All'
              ? totalItems
              : store.filter((p) => p.category === cat).length;
            return (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-amber-600/20 text-amber-400 border border-amber-600/40'
                    : 'bg-zinc-800/60 text-zinc-400 border border-zinc-700 hover:text-zinc-100 hover:border-zinc-600'
                }`}
              >
                {cat}
                <span className={`ml-1.5 text-xs ${isActive ? 'text-amber-500/70' : 'text-zinc-600'}`}>
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Sort dropdown */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <label htmlFor="sort" className="text-xs text-zinc-500 uppercase tracking-wider">
            Sort
          </label>
          <select
            id="sort"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded-md px-3 py-1.5 focus:outline-none focus:border-amber-500/50 cursor-pointer"
          >
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Results count */}
      <div className="text-sm text-zinc-500">
        Showing {displayCount} of {totalItems} products
      </div>

      {/* Product grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {filteredAndSorted.map((product) => (
          <ProductCard key={product.sku} product={product} />
        ))}
      </div>

      {/* Empty state */}
      {displayCount === 0 && (
        <div className="text-center py-16">
          <p className="text-zinc-500 text-lg">No products in this category.</p>
          <button
            onClick={() => setSelectedCategory('All')}
            className="mt-3 text-amber-500 hover:text-amber-400 text-sm font-medium transition-colors"
          >
            Show all products
          </button>
        </div>
      )}
    </div>
  );
}
