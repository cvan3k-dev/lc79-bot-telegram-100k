import asyncio
import sys
from index import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "already running" in str(e):
            # Tạo event loop mới
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(main())
            except KeyboardInterrupt:
                pass
            finally:
                loop.close()
        else:
            raise
