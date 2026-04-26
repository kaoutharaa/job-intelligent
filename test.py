import asyncio
from scrapers.embed_pipeline import EmbedPipeline

async def main():
    pipeline = EmbedPipeline()
    count = await pipeline.embed_task()
    print(f'✅ Embedded {count} jobs')

asyncio.run(main())