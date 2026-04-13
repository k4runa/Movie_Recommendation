"""
routers/__init__.py — Router Package
======================================
Exposes all API router modules so that main.py can import them with:
    from routers import auth, users, movies
"""

from . import auth, users, movies
