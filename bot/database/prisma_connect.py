"""Shared Prisma client. Connect once at startup (see main.py)."""
from prisma import Prisma

db = Prisma()
