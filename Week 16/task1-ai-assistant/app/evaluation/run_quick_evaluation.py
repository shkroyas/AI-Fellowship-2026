"""Compatibility entry point; delegates to the corrected runner (offline by default)."""
import asyncio
from .run_evaluation import main
if __name__ == '__main__':
    asyncio.run(main())
