"""Lanzador del backend OilMine Analytics.

Uso:
    python run_api.py

Documentación interactiva en http://localhost:8000/docs
"""
import logging

import uvicorn

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )
    uvicorn.run(
        "src.interfaces.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
