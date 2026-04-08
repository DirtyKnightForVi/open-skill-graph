import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

import aiofiles
from agentscope.message import TextBlock
from agentscope.tool import ToolResponse
from config.settings import Config


def write_file_sync(filename, content):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)



async def write_text_file(file_path: str, content: str, chunk_size: int = 200):
    """Create/Overwrite content in a text file.

        Args:
            file_path (`str`):
                The target file path.
            content (`str`):
                The content to be written.
            chunk_size (`int`, defaults to `300`):
                The maximum time (in seconds) allowed for the command to run.

        Returns:
            `ToolResponse`:
                The tool response containing the result of the writing operation.
        """

    loop = asyncio.get_event_loop()
    with ProcessPoolExecutor() as pool:
        task = loop.run_in_executor(pool, write_file_sync, file_path, content)
        # 流式返回
        if len(content) > Config.STREAM_CHUNK_SIZE:
            for i in range(0, len(content), Config.STREAM_CHUNK_SIZE):
                chunk = content[i:i + Config.STREAM_CHUNK_SIZE]
                yield ToolResponse(
                    content=[
                        TextBlock(
                            type="text",
                            text=chunk,
                        )
                    ]
                )
        else:
            yield ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=content,
                    )
                ]
            )
        await task
        yield ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=f'Write {file_path} success.',
                ),
            ],
        )


async def write_text_file_async(file_path: str, content: str, chunk_size=10):
    try:
        async with aiofiles.open(file_path, mode='w', encoding='utf-8') as f:
            # 分块写入，防止大文件阻塞
            if len(content) > chunk_size:
                for i in range(0, len(content), chunk_size):
                    chunk = content[i:i + chunk_size]
                    logging.info(f"Writing chunk[{i}]: {file_path}")
                    await f.write(chunk)
                    yield ToolResponse(
                        content=[
                            TextBlock(
                                type="text",
                                text=chunk,
                            )
                        ]
                    )
                    await asyncio.sleep(0)  # 让出控制权
            else:
                await f.write(content)

        yield ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=f'Write {file_path} success.',
                ),
            ],
        )
    except Exception as e:
        yield ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=f"Write {file_path} Error: {e}.",
                ),
            ],
        )
