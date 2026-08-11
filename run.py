import asyncio
import sys
from index import main

if __name__ == '__main__':
    # Dành riêng cho Render.com
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot đã dừng")
        sys.exit(0)
