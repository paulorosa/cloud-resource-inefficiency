"""AWS Rules package."""

from .ebs_inactive_detached import InactiveDetachedEBSVolumeRule

__all__ = ["InactiveDetachedEBSVolumeRule"]
