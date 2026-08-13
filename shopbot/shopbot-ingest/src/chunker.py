# src/chunker.py
# Source: Book 1, Chapter 5 (Appendix A — Code Wiring)
# Attribute-level chunking: each chunk answers one category of customer question.
# A product with five field types produces five or more focused chunks.


def product_to_chunks(product: dict) -> list[dict]:
    """
    Convert a product dictionary into focused retrieval chunks.
    Each chunk covers one type of customer question.

    Returns a list of chunk dicts, each with:
      - id:       unique identifier (product_id + chunk type)
      - text:     the text that will be embedded and stored
      - metadata: filtering and display fields
    """
    pid  = product["id"]
    name = product["name"]
    chunks = []

    # Chunk 1 — Identity
    # Answers: what is this? what fabric? what occasion? what category?
    # Also includes colours, sizes, and price so a single retrieved chunk gives the
    # LLM enough to produce a complete product recommendation answer.
    colors_text = ", ".join(product.get("colors", [])) or "not specified"
    sizes_text  = ", ".join(product.get("sizes",  [])) or "one size"
    price_text  = f"₹{product['price']}" if product.get("price") else "not listed"
    identity_text = (
        f"{name}. {product['description']} "
        f"Category: {product['category']}. "
        f"Fabric: {product.get('fabric', 'not specified')}. "
        f"Occasion: {product.get('occasion', 'general')}. "
        f"Available in: {colors_text}. Sizes: {sizes_text}. Price: {price_text}."
    )
    chunks.append({
        "id":   f"{pid}_identity",
        "text": identity_text,
        "metadata": {
            "product_id": pid,
            "chunk_type": "identity",
            "category":   product["category"],
            "price":      product.get("price", 0),
        },
    })

    # Chunk 2 — Variants
    # Answers: what colours? what sizes? what price? is it in stock?
    variant_text = (
        f"{name} is available in colours: {', '.join(product.get('colors', []))}. "
        f"Available sizes: {', '.join(product.get('sizes', ['one size']))}. "
        f"Price: ₹{product.get('price', 'not listed')}. "
        f"Stock status: {product.get('stock_status', 'in stock')}."
    )
    chunks.append({
        "id":   f"{pid}_variants",
        "text": variant_text,
        "metadata": {
            "product_id": pid,
            "chunk_type": "variants",
            "category":   product["category"],
            "price":      product.get("price", 0),
        },
    })

    # Chunk 3 — Policy
    # Answers: can I return it? what is the exchange window?
    if product.get("return_policy"):
        policy_text = (
            f"Return and exchange policy for {name}: {product['return_policy']} "
            f"Exchange policy: "
            f"{product.get('exchange_policy', 'contact support for exchanges')}."
        )
        chunks.append({
            "id":   f"{pid}_policy",
            "text": policy_text,
            "metadata": {
                "product_id": pid,
                "chunk_type": "policy",
                "category":   product["category"],
                "price":      product.get("price", 0),
            },
        })

    # Chunk 4 — Care
    # Answers: how do I wash this? machine or hand? dry clean?
    if product.get("care_instructions"):
        care_text = (
            f"Care instructions for {name}: {product['care_instructions']}"
        )
        chunks.append({
            "id":   f"{pid}_care",
            "text": care_text,
            "metadata": {
                "product_id": pid,
                "chunk_type": "care",
                "category":   product["category"],
                "price":      product.get("price", 0),
            },
        })

    # Chunk 5+ — FAQs
    # Each FAQ becomes its own chunk for maximum retrieval precision.
    for i, faq in enumerate(product.get("faqs", [])):
        faq_text = (
            f"Question about {name}: {faq['question']} "
            f"Answer: {faq['answer']}"
        )
        chunks.append({
            "id":   f"{pid}_faq_{i}",
            "text": faq_text,
            "metadata": {
                "product_id": pid,
                "chunk_type": "faq",
                "category":   product["category"],
                "price":      product.get("price", 0),
            },
        })

    return chunks
