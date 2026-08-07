"""Shared fixtures for mandate tests.

CI installs the api+gateway locks only — the three service locks are not
jointly resolvable, so the mandate lock (and with it motor/pymongo) is
absent there. These tests deliberately never touch MongoDB, but importing
a router module pulls in mandate.app.database, whose top-level driver
imports would fail. Stub the driver modules when they're not installed;
when they are (local dev with the mandate lock), the real ones are used.
"""

import sys
import types

try:
    import motor.motor_asyncio  # noqa: F401
except ModuleNotFoundError:
    motor_mod = types.ModuleType("motor")
    motor_asyncio_mod = types.ModuleType("motor.motor_asyncio")
    motor_asyncio_mod.AsyncIOMotorClient = type("AsyncIOMotorClient", (), {})
    motor_asyncio_mod.AsyncIOMotorDatabase = type("AsyncIOMotorDatabase", (), {})
    motor_mod.motor_asyncio = motor_asyncio_mod
    sys.modules["motor"] = motor_mod
    sys.modules["motor.motor_asyncio"] = motor_asyncio_mod

try:
    import pymongo  # noqa: F401
except ModuleNotFoundError:
    pymongo_mod = types.ModuleType("pymongo")
    pymongo_mod.ASCENDING = 1
    pymongo_mod.DESCENDING = -1
    pymongo_mod.IndexModel = type("IndexModel", (), {})
    sys.modules["pymongo"] = pymongo_mod
