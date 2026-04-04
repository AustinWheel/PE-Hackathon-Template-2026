import logging

from flask import Blueprint, jsonify
from playhouse.shortcuts import model_to_dict

from app.models.product import Product

logger = logging.getLogger(__name__)
products_bp = Blueprint("products", __name__)


@products_bp.route("/products")
def list_products():
    try:
        from app.cache import cache_get, cache_set
        cached = cache_get("products:all")
        if cached is not None:
            logger.info("Products listed (cache hit)", extra={"component": "products", "count": len(cached)})
            return jsonify(cached)

        products = Product.select()
        result = [model_to_dict(p) for p in products]
        cache_set("products:all", result, ttl=60)
        logger.info("Products listed (cache miss)", extra={"component": "products", "count": len(result)})
        return jsonify(result)
    except Exception as e:
        logger.error("Failed to list products", extra={"component": "products", "error": str(e)})
        return jsonify({"error": "Internal server error"}), 500