from .video_resolution_node import VideoResolutionNode

NODE_CLASS_MAPPINGS = {
    "VideoResolutionNode": VideoResolutionNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "VideoResolutionNode": "Video Resolution",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
