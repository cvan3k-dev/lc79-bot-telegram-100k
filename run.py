import asyncio
from index import main

if __name__ == "__main__":
    # Tạo event loop mới hoàn toàn
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
