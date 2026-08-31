import sys
import os
import io
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from alembic.migration import MigrationContext
from alembic.autogenerate import compare_metadata
from alembic.autogenerate.api import AutogenContext
from alembic.autogenerate.render import _render_cmd_body

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.models import Base

async def main():
    engine = create_async_engine("postgresql+asyncpg://postgres:fake@localhost/postgres")
    async with engine.connect() as conn:
        def do_compare(sync_conn):
            mc = MigrationContext.configure(sync_conn)
            ctx = AutogenContext(mc)
            metadata = Base.metadata
            diffs = compare_metadata(mc, metadata)
            code = _render_cmd_body(diffs, ctx)
            print("--- UPGRADE ---")
            print(code)
        
        await conn.run_sync(do_compare)

asyncio.run(main())
