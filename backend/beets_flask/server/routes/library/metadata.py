"""Get metadata for a library item.

TODO: Or modify metadata for a library item.
"""

import os
from typing import TYPE_CHECKING

from beets import util as beets_util
from quart import Blueprint, g, request
from tinytag import TinyTag

from beets_flask.invoker.enqueue import enqueue_analyze_attributes
from beets_flask.server.exceptions import (
    IntegrityException,
    InvalidUsageException,
    NotFoundException,
)

if TYPE_CHECKING:
    # For type hinting the global g object
    from . import g


metadata_bp = Blueprint("metadata", __name__)


__all__ = ["metadata_bp"]


@metadata_bp.route("/item/<int:item_id>/metadata", methods=["GET"])
async def item_metadata(item_id: int):
    # Item from beets library
    # FIXME: The following should be made into a common function
    # it is also used in artwork.py
    item = g.lib.get_item(item_id)
    if not item:
        raise NotFoundException(
            f"Item with beets_id:'{item_id}' not found in beets db."
        )

    # File
    item_path = beets_util.syspath(item.path)
    if not os.path.exists(item_path):
        raise IntegrityException(
            f"Item file '{item_path}' does not exist for item beets_id:'{item_id}'."
        )

    # Get metadata
    tag = TinyTag.get(item_path)
    return tag.as_dict()


@metadata_bp.route("/analyze", methods=["POST"])
async def analyze_items():
    """Analyze BPM and Key for a list of items.

    Expects a JSON body with:
    - item_ids: list[int]
    - analyze_bpm: bool (optional, default True)
    - analyze_key: bool (optional, default True)
    """
    data = await request.get_json()
    if not data:
        raise InvalidUsageException("No data provided")

    item_ids = data.get("item_ids")
    if not item_ids or not isinstance(item_ids, list):
        raise InvalidUsageException("item_ids must be a list of integers")

    analyze_bpm = data.get("analyze_bpm", True)
    analyze_key = data.get("analyze_key", True)

    job = enqueue_analyze_attributes(item_ids, analyze_bpm, analyze_key)

    return {"job_id": job.id, "status": "queued"}, 202
