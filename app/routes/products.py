import logging

from flask import Blueprint, jsonify
from playhouse.shortcuts import model_to_dict

from app.models.product import Product

logger = logging.getLogger(__name__)
products_bp = Blueprint("products", __name__)


@products_bp.route("/products")
def list_products():
    try:
        products = Product.select()
        result = [model_to_dict(p) for p in products]
        logger.info("Products listed", extra={"component": "products", "count": len(result)})
        return jsonify(result)
    except Exception as e:
        logger.error("Failed to list products", extra={"component": "products", "error": str(e)})
        return jsonify({"error": "Internal server error"}), 500