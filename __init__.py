from aiohttp import web
from server import PromptServer

from .video_resolution_node import VideoResolutionNode, preview_resolution


@PromptServer.instance.routes.post("/video_resolution/preview")
async def video_resolution_preview(request):
    try:
        result = preview_resolution(await request.json())
    except (ValueError, TypeError, OverflowError):
        return web.json_response({"error": "Invalid resolution settings."}, status=400)
    return web.json_response(result)

NODE_CLASS_MAPPINGS = {
    "VideoResolutionNode": VideoResolutionNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "VideoResolutionNode": "Video Resolution",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
