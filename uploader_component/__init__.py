from pathlib import Path
import streamlit.components.v1 as components

_COMPONENT_DIR = Path(__file__).parent
_batch_uploader = components.declare_component(
    "batch_uploader",
    path=str(_COMPONENT_DIR),
)


def batch_uploader(
    *,
    key,
    batch_size=18,
    max_file_mb=12,
    accepted_types=None,
    ack_id=None,
    advance_token=0,
    reset_token=0,
    max_queue_files=500,
):
    """Batch uploader. The browser keeps the full selection and uploads only
    one file at a time, in batches of ``batch_size``.
    """
    return _batch_uploader(
        key=key,
        batch_size=batch_size,
        max_file_mb=max_file_mb,
        accepted_types=accepted_types or ["jpg", "jpeg", "png"],
        ack_id=ack_id or "",
        advance_token=advance_token,
        reset_token=reset_token,
        max_queue_files=max_queue_files,
        default=None,
    )
