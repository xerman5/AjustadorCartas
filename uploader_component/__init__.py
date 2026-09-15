from pathlib import Path
import streamlit.components.v1 as components

_COMPONENT_DIR = Path(__file__).parent
_batch_uploader = components.declare_component(
    "batch_uploader",
    path=str(_COMPONENT_DIR),
)


def batch_uploader(*, key, max_files, max_file_mb, max_total_mb=None, accepted_types=None, ack_id=None, reset_token=0):
    """Browser-side batch selector that uploads one file at a time to limit RAM use."""
    return _batch_uploader(
        key=key,
        max_files=max_files,
        max_file_mb=max_file_mb,
        max_total_mb=max_total_mb,
        accepted_types=accepted_types or ["jpg", "jpeg", "png"],
        ack_id=ack_id or "",
        reset_token=reset_token,
        default=None,
    )
