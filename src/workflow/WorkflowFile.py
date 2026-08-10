"""Pure-Python read/write for LaME workflow files (serialized Blockly workspaces).

A workflow file is JSON: ``{"lame_workflow_version": 1, "blockly_state": {...}}``,
where ``blockly_state`` is exactly what Blockly's ``Blockly.serialization.workspaces.save()``
produces in the browser (see ``blockly/src/app.js``'s ``getWorkspaceStateJSON``/
``loadWorkspaceStateJSON``).

These helpers let Python append to and read a workflow file directly on disk,
with no live Blockly workspace (a ``QWebEngineView``) involved. That's what lets
action capture (see ``ActionRecorder``, ``MainWindow._record_to_active_workflow``)
work even while the Workflow dock is closed. When the dock *is* open,
``Workflow.reload_active_file`` re-reads the same file into the live JS workspace
so the visible workspace and the file stay in sync.
"""
import json
import uuid
from datetime import datetime
from pathlib import Path

WORKFLOW_FORMAT_VERSION = 1


def new_workflow_payload():
    """Return an empty, valid workflow file payload.

    Returns
    -------
    dict
        ``{'lame_workflow_version': 1, 'blockly_state': {...empty workspace...}, 'snapshots': []}``
    """
    return {
        'lame_workflow_version': WORKFLOW_FORMAT_VERSION,
        'blockly_state': {'blocks': {'languageVersion': 0, 'blocks': []}},
        'snapshots': [],
    }


def load_workflow_file(path):
    """Load a workflow file, returning an empty payload if it doesn't exist yet.

    Parameters
    ----------
    path : str or Path
        Workflow file location.

    Returns
    -------
    dict
        Payload with ``lame_workflow_version`` and ``blockly_state`` keys.
    """
    path = Path(path)
    if not path.exists():
        return new_workflow_payload()

    with open(path, 'r') as f:
        payload = json.load(f)

    payload.setdefault('lame_workflow_version', WORKFLOW_FORMAT_VERSION)
    payload.setdefault('blockly_state', {})
    payload['blockly_state'].setdefault('blocks', {'languageVersion': 0, 'blocks': []})
    payload['blockly_state']['blocks'].setdefault('blocks', [])
    payload.setdefault('snapshots', [])
    return payload


def save_workflow_file(path, payload):
    """Write a workflow payload to disk as JSON, creating parent directories as needed.

    Parameters
    ----------
    path : str or Path
        Destination file.
    payload : dict
        Payload as returned by `load_workflow_file`/`new_workflow_payload`.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        # default=str is a deliberately blunt fallback for values that don't round-trip
        # cleanly through JSON (e.g. numpy scalars in style settings) - snapshots are a
        # documentation/journal record, not something that needs exact reload fidelity.
        json.dump(payload, f, indent=2, default=str)


def append_block(payload, block_type, fields):
    """Append a top-level block to a workflow payload's Blockly state, in place.

    Parameters
    ----------
    payload : dict
        A payload as returned by `load_workflow_file`/`new_workflow_payload`.
    block_type : str
        Blockly block type name (e.g. 'select_samples').
    fields : dict
        Field name/value pairs for the new block.

    Returns
    -------
    dict
        The same `payload`, for chaining.
    """
    blocks = payload['blockly_state']['blocks']['blocks']
    blocks.append({
        'type': block_type,
        'id': uuid.uuid4().hex,
        'x': 20,
        'y': 20 + 60 * len(blocks),
        'fields': dict(fields),
    })
    return payload


def append_snapshot(payload, snapshot):
    """Append a snapshot (plot settings/data-state, no matching Blockly block) to a payload, in place.

    Used for actions that don't have a Blockly block to represent them yet
    (see `ActionRecorder.build_block_state`) - e.g. `MainWindow.snapshot_workflow`
    - so they're still captured in the workflow file even though they won't
    appear as a block in the live Blockly workspace.

    Parameters
    ----------
    payload : dict
        A payload as returned by `load_workflow_file`/`new_workflow_payload`.
    snapshot : dict
        Arbitrary snapshot data (e.g. plot type, style settings, fields used).

    Returns
    -------
    dict
        The same `payload`, for chaining.
    """
    entry = dict(snapshot)
    entry['timestamp'] = datetime.now().isoformat()
    payload.setdefault('snapshots', []).append(entry)
    return payload
