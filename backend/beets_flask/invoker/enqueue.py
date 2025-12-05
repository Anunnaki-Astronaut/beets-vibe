from __future__ import annotations

import asyncio
import gc
import shutil
import subprocess
from contextlib import suppress
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    ParamSpec,
    TypeVar,
)

from beets.ui import _open_library
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from beets_flask.config import get_config
from beets_flask.database import db_session_factory
from beets_flask.database.models.states import (
    FolderInDb,
    SessionState,
    SessionStateInDb,
)
from beets_flask.importer.progress import FolderStatus
from beets_flask.importer.session import (
    AddCandidatesSession,
    AutoImportSession,
    BootlegImportSession,
    CandidateChoice,
    ImportSession,
    PreviewSession,
    Search,
    TaskIdMappingArg,
    UndoSession,
    delete_from_beets,
)
from beets_flask.importer.types import DuplicateAction
from beets_flask.logger import log
from beets_flask.redis import import_queue, preview_queue
from beets_flask.server.exceptions import (
    InvalidUsageException,
    exception_as_return_value,
)
from beets_flask.server.websocket.status import (
    JobStatusUpdate,
    emit_folder_status,
    send_status_update,
)

from .job import ExtraJobMeta, _set_job_meta

if TYPE_CHECKING:
    from beets.library import Library
    from rq.job import Job
    from rq.queue import Queue


def emit_update_on_job_change(job, connection, result, *args, **kwargs):
    """
    Callback for rq enqueue functions to emit a job status update via websocket.

    See https://python-rq.org/docs/#success-callback
    """
    log.debug(f"job update for socket {job=} {connection=} {result=} {args=} {kwargs=}")

    def _is_serialized_exception(d: Any):
        # I wish we could to instance checks on our SerializedException TypedDict
        if not isinstance(result, dict):
            return False
        if "type" in d and "message" in d.keys():
            # the other keys are optional
            return True
        return False

    try:
        asyncio.run(
            send_status_update(
                JobStatusUpdate(
                    message="Job status update",
                    num_jobs=1,
                    job_metas=[job.get_meta()],
                    exc=result if _is_serialized_exception(result) else None,
                )
            )
        )
    except Exception as e:
        log.error(f"Failed to emit job update: {e}", exc_info=True)


P = ParamSpec("P")  # Parameters
R = TypeVar("R")  # Return


def _enqueue(
    queue: Queue,
    f: Callable[P, Any | Awaitable[Any]],
    *args: P.args,
    **kwargs: P.kwargs,
) -> Job:
    """Enqueue a job in redis.

    Helper that sets some shared behavior and allows
    to for proper type hinting.
    """

    job = queue.enqueue(
        f,
        *args,
        **kwargs,
        on_success=emit_update_on_job_change,
    )
    return job


class EnqueueKind(Enum):
    """Enum for the different kinds of sessions we can enqueue."""

    PREVIEW = "preview"
    PREVIEW_ADD_CANDIDATES = "preview_add_candidates"
    IMPORT_CANDIDATE = "import_candidate"
    IMPORT_AUTO = "import_auto"
    IMPORT_UNDO = "import_undo"
    IMPORT_BOOTLEG = "import_bootleg"
    # Bootlegs are essentially asis, but does not mean to just import the asis candidate,
    # it has its own session that also groups albums, and skips previews.

    _AUTO_IMPORT = "_auto_import"
    _AUTO_PREVIEW = "_auto_preview"

    # DJ metadata analysis (BPM, Key detection)
    ANALYZE_ATTRIBUTES = "analyze_attributes"

    @classmethod
    def from_str(cls, kind: str) -> EnqueueKind:
        """Convert a string to an EnqueueKind enum.

        Parameters
        ----------
        kind : str
            The string to convert.
        """
        try:
            return cls[kind.upper()]
        except KeyError:
            raise ValueError(f"Unknown kind {kind}")


@emit_folder_status(before=FolderStatus.PENDING)
async def enqueue(
    hash: str,
    path: str,
    kind: EnqueueKind,
    extra_meta: ExtraJobMeta | None = None,
    **kwargs,
) -> Job:
    """Delegate a preview or import to a redis worker, depending on its kind.

    Parameters
    ----------
    hash : str
        The hash of the folder to enqueue.
    path : str
        The path of the folder to enqueue.
    kind : EnqueueKind
        The kind of the folder to enqueue.
    extra_meta: ExtraJobMeta, optional
        Extra meta data to pass to the job. E.g. use this to assign a reference
        for the frontend to the job, so we can track it via the websocket.
    kwargs : dict
        Additional arguments to pass to the worker functions. Depend on the kind,
        use with care.
    """
    if extra_meta is None:
        extra_meta = ExtraJobMeta()

    match kind:
        case EnqueueKind.PREVIEW:
            job = enqueue_preview(hash, path, extra_meta, **kwargs)
        case EnqueueKind.PREVIEW_ADD_CANDIDATES:
            job = enqueue_preview_add_candidates(hash, path, extra_meta, **kwargs)
        case EnqueueKind.IMPORT_AUTO:
            job = enqueue_import_auto(hash, path, extra_meta, **kwargs)
        case EnqueueKind.IMPORT_CANDIDATE:
            job = enqueue_import_candidate(hash, path, extra_meta, **kwargs)
        case EnqueueKind.IMPORT_BOOTLEG:
            job = enqueue_import_bootleg(hash, path, extra_meta, **kwargs)
        case EnqueueKind.IMPORT_UNDO:
            job = enqueue_import_undo(hash, path, extra_meta, **kwargs)
        case _:
            raise InvalidUsageException(f"Unknown kind {kind}")

    log.debug(f"Enqueued {job.id=} {job.meta=}")

    return job


# --------------------------- Enqueue entry points --------------------------- #
# Mainly input validation and submitting to the redis queue


def enqueue_preview(hash: str, path: str, extra_meta: ExtraJobMeta, **kwargs) -> Job:
    group_albums: bool | None = kwargs.pop("group_albums", None)
    autotag: bool | None = kwargs.pop("autotag", None)

    if len(kwargs.keys()) > 0:
        raise InvalidUsageException("EnqueueKind.PREVIEW does not accept any kwargs.")
    job = _enqueue(preview_queue, run_preview, hash, path, group_albums, autotag)
    _set_job_meta(job, hash, path, EnqueueKind.PREVIEW, extra_meta)
    return job


def enqueue_preview_add_candidates(
    hash: str, path: str, extra_meta: ExtraJobMeta, **kwargs
) -> Job:
    # May contain search_ids, search_artist, search_album
    # As always to allow task mapping

    search: TaskIdMappingArg[Search | Literal["skip"]] = kwargs.pop("search", None)
    if len(kwargs.keys()) > 0:
        raise InvalidUsageException(
            "EnqueueKind.PREVIEW_ADD_CANDIDATES only accepts the following kwargs: "
            + "search"
        )

    if search is None:
        raise InvalidUsageException(
            "EnqueueKind.PREVIEW_ADD_CANDIDATES requires a search kwarg."
        )

    # kwargs are mixed between our own function and redis enqueue -.-
    # if we accidentally define a redis kwarg for our function, it will be ignored.
    # https://python-rq.org/docs/#enqueueing-jobs
    job = _enqueue(
        preview_queue,
        run_preview_add_candidates,
        hash,
        path,
        search=search,
    )
    _set_job_meta(job, hash, path, EnqueueKind.PREVIEW_ADD_CANDIDATES, extra_meta)
    return job


def enqueue_import_candidate(
    hash: str, path: str, extra_meta: ExtraJobMeta, **kwargs
) -> Job:
    """
    Imports a candidate that has been fetched in a preview session.

    Kwargs
    ------
    candidate_id : CandidateChoice | dict[str, CandidateChoice] | None
        A valid candidate id for a candidate that has been fetched in a preview
        session.
        None stands for best, is resolved in the session.
        additionally, if a dict is provided, it maps from task_id to candidate, and dupicate action, respectively.
    duplicate_actions
        See candidate_id.
    TODO: Also allowed: "asis" (no exact match needed, there is only one
        asis-candidate).
    """

    candidate_ids: TaskIdMappingArg[CandidateChoice] = kwargs.pop("candidate_ids", None)
    duplicate_actions: TaskIdMappingArg[DuplicateAction] = kwargs.pop(
        "duplicate_actions", None
    )

    if len(kwargs.keys()) > 0:
        raise InvalidUsageException(
            "EnqueueKind.IMPORT only accepts the following kwargs: "
            + "candidate_ids, duplicate_actions."
        )

    # TODO: Validation: lookup candidates exits

    # For convenience: if the user calls this but no preview was generated before,
    # use the auto-import instead (which also fetches previews).
    try:
        # TODO: along with validation:
        # we need a special flag as task_id that stands for "do this for all tasks"
        # used along with candidate_ids length == 1.
        # then, only run the fallback auto-import for the args coming from gui import button

        # If the user did not specify a candidate_id, we assume they want the best
        # candidate.
        with db_session_factory() as db_session:
            _get_live_state_by_folder(hash, path, db_session)
            # raises if no state found
    except:
        log.info(
            f"No previous session state fround for {hash=} {path=} "
            + "switching to auto-import"
        )
        return enqueue_import_auto(hash, path, extra_meta)

    job = _enqueue(
        import_queue,
        run_import_candidate,
        hash,
        path,
        candidate_ids=candidate_ids,
        duplicate_actions=duplicate_actions,
    )
    _set_job_meta(job, hash, path, EnqueueKind.IMPORT_CANDIDATE, extra_meta)
    return job


def enqueue_import_auto(hash: str, path: str, extra_meta: ExtraJobMeta, **kwargs):
    """
    Enqueue an automatic import.

    Auto jobs first generate a preview (if needed) and then run an import, which always
    imports the best candidate - but only if the preview is good enough (as specified
    in the users beets config)

    This is a two step process, and previews run in another queue (thread) than imports.

    See AutoImportSession for more details.
    """

    group_albums: bool | None = kwargs.pop("group_albums", None)
    autotag: bool | None = kwargs.pop("autotag", None)
    import_threshold: float | None = kwargs.pop("import_threshold", None)
    duplicate_actions: TaskIdMappingArg[DuplicateAction] = kwargs.pop(
        "duplicate_actions", None
    )

    if len(kwargs.keys()) > 0:
        raise InvalidUsageException(
            "EnqueueKind.IMPORT_AUTO only accepts the following kwargs: "
            + "group_albums, autotag, import_threshold, duplicate_actions."
        )

    # We only assign the on_success callback (likely coming
    # via a kwarg) to the second job!
    job1 = preview_queue.enqueue(
        run_preview, hash, path, group_albums=group_albums, autotag=autotag, **kwargs
    )
    _set_job_meta(job1, hash, path, EnqueueKind._AUTO_PREVIEW, extra_meta)
    job2 = _enqueue(
        import_queue,
        run_import_auto,
        hash,
        path,
        import_threshold=import_threshold,
        duplicate_actions=duplicate_actions,
        **kwargs,
        # rq has no proper typing therefore our kwargs are not type checked properly
        depends_on=job1,  # type: ignore
    )
    _set_job_meta(job2, hash, path, EnqueueKind._AUTO_IMPORT, extra_meta)

    return job2


def enqueue_import_bootleg(hash: str, path: str, extra_meta: ExtraJobMeta, **kwargs):
    job = _enqueue(import_queue, run_import_bootleg, hash, path, **kwargs)
    _set_job_meta(job, hash, path, EnqueueKind.IMPORT_BOOTLEG, extra_meta)
    return job


def enqueue_import_undo(hash: str, path: str, extra_meta: ExtraJobMeta, **kwargs):
    delete_files: bool = kwargs.pop("delete_files", True)

    if len(kwargs.keys()) > 0:
        raise InvalidUsageException(
            "EnqueueKind.IMPORT_UNDO only accepts the following kwargs: "
            + "delete_files."
        )

    job = _enqueue(
        import_queue,
        run_import_undo,
        hash,
        path,
        delete_files=delete_files,
    )
    _set_job_meta(job, hash, path, EnqueueKind.IMPORT_UNDO, extra_meta)
    return job


def enqueue_delete_items(task_ids: list[str]) -> Job:
    """Enqueue to delete items from the beets library.

    A bit of a special case as this does not use the normal
    hash and path based enqueueing.
    """
    job = _enqueue(
        import_queue,
        delete_items,
        task_ids,
        True,
        # rq has no proper typing therefore our kwargs are not type checked properly
        at_front=True,  # type: ignore
    )
    return job


# -------------------- Functions that run in redis workers ------------------- #
# TODO: We might want to move these to their own file, for a bit better separation of
# concerns.


# redis preview queue
@exception_as_return_value
@emit_folder_status(before=FolderStatus.PREVIEWING, after=FolderStatus.PREVIEWED)
async def run_preview(
    hash: str,
    path: str,
    group_albums: bool | None,
    autotag: bool | None,
):
    """Fetch candidates for a folder using beets.

    Will refetch candidates if this is rerun even if candidates exist
    in the db.

    Current convention is we have one session for one folder *has*, but
    We might have multiple sessions for the same folder **path**.
    Previews will **reset** any previous session state in the database, if they
    exist for the same folder hash.

    Parameters
    ----------
    hash : str
        The hash of the folder for which to run the preview.
    path : str
        The path of the folder for which to run the preview.
    group_albums : bool | None
        Whether to create multple tasks, one for each album found in the metadata
        of the files. Set to true if you have multiple albums in a single folder.
        If None: get value from beets config.
    autotag : bool | None
        Whether to look up metadata online. If None: get value from beets config.
    """

    log.info(f"Preview task on {hash=} {path=}")

    with db_session_factory() as db_session:
        f_on_disk = FolderInDb.get_current_on_disk(hash, path)
        if hash != f_on_disk.hash:
            log.warning(
                f"Folder content has changed since the job was scheduled for {path}. "
                + f"Using new content ({f_on_disk.hash}) instead of {hash}"
            )

        # here, in preview, we always want to start from a fresh state
        # an existing state would skip the candidate lookup.
        # otherwise, the retag action would not work, as preview starting from
        s_state_live = SessionState(f_on_disk)
        p_session = PreviewSession(
            s_state_live, group_albums=group_albums, autotag=autotag
        )

        try:
            await p_session.run_async()
        finally:
            # Get max revision for this folder hash
            stmt = select(func.max(SessionStateInDb.folder_revision)).where(
                SessionStateInDb.folder_hash == hash,
            )
            max_rev = db_session.execute(stmt).scalar_one_or_none()
            new_rev = 0 if max_rev is None else max_rev + 1
            s_state_indb = SessionStateInDb.from_live_state(p_session.state)
            s_state_indb.folder_revision = new_rev

            db_session.merge(s_state_indb)
            db_session.commit()

    log.info(f"Preview done. {hash=} {path=}")
    return


# redis preview queue
@exception_as_return_value
@emit_folder_status(before=FolderStatus.PREVIEWING, after=FolderStatus.PREVIEWED)
async def run_preview_add_candidates(
    hash: str, path: str, search: TaskIdMappingArg[Search | Literal["skip"]]
):
    """Adds a candidate to an session which is already in the status tagged.

    This only works if all session tasks are tagged. I.e. preview completed.

    Parameters
    ----------
    search : dict[str, Search]
        A dictionary of task ids to search dicts. No value or none skips the search
        for this task.
    """
    log.info(f"Add preview candidates task on {hash=}")

    with db_session_factory() as db_session:
        s_state_live = _get_live_state_by_folder(hash, path, db_session)

        a_session = AddCandidatesSession(
            s_state_live,
            search=search,
        )
        try:
            await a_session.run_async()
        finally:
            s_state_indb = SessionStateInDb.from_live_state(a_session.state)
            db_session.merge(instance=s_state_indb)
            db_session.commit()

    log.info(f"Add candidates done. {hash=} {path=}")


# redis import queue
@exception_as_return_value
@emit_folder_status(before=FolderStatus.IMPORTING, after=FolderStatus.IMPORTED)
async def run_import_candidate(
    hash: str,
    path: str,
    candidate_ids: TaskIdMappingArg[CandidateChoice],
    duplicate_actions: TaskIdMappingArg[DuplicateAction],
):
    """Imports a candidate that has been fetched in a preview session.

    Parameters
    ----------
    candidate_id : optional
        If candidate_id is none the best candidate is used.
    duplicate_action : optional
        If duplicate_action is none, the default action from the config is used.
    """
    log.info(f"Import task on {hash=} {path=}")

    with db_session_factory() as db_session:
        s_state_live = _get_live_state_by_folder(hash, path, db_session)

        i_session = ImportSession(
            s_state_live,
            candidate_ids=candidate_ids,
            duplicate_actions=duplicate_actions,
        )

        try:
            await i_session.run_async()
        finally:
            s_state_indb = SessionStateInDb.from_live_state(i_session.state)
            db_session.merge(instance=s_state_indb)
            db_session.commit()

    log.info(f"Import candidate done. {hash=} {path=}")


# redis import queue
@exception_as_return_value
@emit_folder_status(before=FolderStatus.IMPORTING, after=FolderStatus.IMPORTED)
async def run_import_auto(
    hash: str,
    path: str,
    import_threshold: float | None,
    duplicate_actions: TaskIdMappingArg[DuplicateAction],
):
    log.info(f"Auto Import task on {hash=} {path=}")

    with db_session_factory() as db_session:
        s_state_live = _get_live_state_by_folder(hash, path, db_session)
        i_session = AutoImportSession(
            s_state_live,
            import_threshold=import_threshold,
            duplicate_actions=duplicate_actions,
        )

        try:
            await i_session.run_async()
        finally:
            s_state_indb = SessionStateInDb.from_live_state(i_session.state)
            db_session.merge(instance=s_state_indb)
            db_session.commit()

    log.info(f"Auto Import done. {hash=} {path=}")


# redis import queue
@exception_as_return_value
@emit_folder_status(before=FolderStatus.IMPORTING, after=FolderStatus.IMPORTED)
async def run_import_bootleg(hash: str, path: str):
    log.info(f"Bootleg Import task on {hash=} {path=}")

    with db_session_factory() as db_session:
        # TODO: add duplicate action
        # TODO: sort out how to generate previews for asis candidates
        s_state_live = _get_live_state_by_folder(
            hash, path, create_if_not_exists=True, db_session=db_session
        )
        i_session = BootlegImportSession(s_state_live)

        try:
            await i_session.run_async()
        finally:
            s_state_indb = SessionStateInDb.from_live_state(i_session.state)
            db_session.merge(instance=s_state_indb)
            db_session.commit()

    log.info(f"Bootleg Import done. {hash=} {path=}")


@exception_as_return_value
@emit_folder_status(before=FolderStatus.DELETING, after=FolderStatus.DELETED)
async def run_import_undo(hash: str, path: str, delete_files: bool):
    log.info(f"Import Undo task on {hash=} {path=}")

    with db_session_factory() as db_session:
        s_state_live = _get_live_state_by_folder(hash, path, db_session)
        i_session = UndoSession(s_state_live, delete_files=delete_files)

        try:
            await i_session.run_async()
        finally:
            s_state_indb = SessionStateInDb.from_live_state(i_session.state)
            db_session.merge(instance=s_state_indb)
            db_session.commit()

    log.info(f"Import Undo done. {hash=} {path=}")


def _get_live_state_by_folder(
    hash: str, path: str, db_session: Session, create_if_not_exists=False
) -> SessionState:
    f_on_disk = FolderInDb.get_current_on_disk(hash, path)
    if hash != f_on_disk.hash:
        log.warning(
            f"Folder content has changed since the job was scheduled for {path}. "
            + f"Using new content ({f_on_disk.hash}) instead of {hash}"
        )

    s_state_indb = SessionStateInDb.get_by_hash_and_path(
        # we warn about hash change, and want the import to still run
        # but on the old hash.
        hash=hash,
        path=path,
        db_session=db_session,
    )

    if s_state_indb is None and create_if_not_exists:
        s_state_live = SessionState(f_on_disk)
        return s_state_live

    if s_state_indb is None:
        # TODO: rq error handling
        raise InvalidUsageException(
            f"No session state found for {path=} {hash=} "
            + f"fresh_hash_on_disk={f_on_disk}, this should not happen."
        )

    log.debug(f"Using existing session state for {path=}")
    s_state_live = s_state_indb.to_live_state()

    # we need this expunge, otherwise we cannot overwrite session states:
    # If object id is in session we cant add a new object to the session with the
    # same id this will raise (see below session.merge)
    db_session.expunge_all()

    return s_state_live


def delete_items(task_ids: list[str], delete_files: bool = True):
    lib = _open_library(get_config())
    for task_id in task_ids:
        delete_from_beets(task_id, delete_files=delete_files, lib=lib)


# -------------------- DJ Metadata Analysis Functions ------------------- #


def enqueue_analyze_attributes(
    item_ids: list[int],
    analyze_bpm: bool = True,
    analyze_key: bool = True,
) -> Job:
    """Enqueue a job to analyze BPM and Key attributes for library items.

    Parameters
    ----------
    item_ids : list[int]
        List of beets item IDs to analyze.
    analyze_bpm : bool
        Whether to analyze BPM (default: True).
    analyze_key : bool
        Whether to analyze musical key (default: True).

    Returns
    -------
    Job
        The enqueued RQ job.
    """
    job = _enqueue(
        import_queue,  # Use import queue to avoid blocking previews
        run_analyze_attributes,
        item_ids,
        analyze_bpm,
        analyze_key,
    )
    return job


@exception_as_return_value
async def run_analyze_attributes(
    item_ids: list[int],
    analyze_bpm: bool = True,
    analyze_key: bool = True,
    *,
    lib: "Library" | None = None,
    close_library: bool = True,
) -> dict[str, Any]:
    """Analyze BPM and Key attributes for library items.

    Parameters
    ----------
    item_ids : list[int]
        Beets item IDs to analyze.
    analyze_bpm : bool
        Whether to run BPM analysis via aubio.
    analyze_key : bool
        Whether to run key detection via keyfinder-cli.
    lib : Library | None
        Optional pre-opened beets library instance. When provided, the caller
        is responsible for managing its lifecycle.
    close_library : bool
        Whether to close the provided library at the end of the run. This value
        is ignored unless ``lib`` is ``None`` (i.e., the function opened the
        library itself) or the caller explicitly wants the helper to close a
        supplied library instance.
    """
    log.info(f"Starting attribute analysis for {len(item_ids)} items")

    managed_library = lib is None
    if managed_library:
        lib = _open_library(get_config())

    assert lib is not None  # for type-checkers
    results: dict[str, Any] = {
        "analyzed": [],
        "errors": [],
        "skipped": [],
    }

    try:
        for item_id in item_ids:
            item = lib.get_item(item_id)
            if item is None:
                log.warning(f"Item {item_id} not found in library")
                results["errors"].append(
                    {
                        "item_id": item_id,
                        "error": "Item not found in library",
                    }
                )
                continue

            item_path = (
                item.path.decode("utf-8", errors="ignore")
                if isinstance(item.path, (bytes, bytearray))
                else str(item.path)
            )
            log.debug(f"Analyzing item {item_id}: {item_path}")

            item_result = {
                "item_id": item_id,
                "path": item_path,
                "bpm": None,
                "initial_key": None,
            }

            try:
                if analyze_bpm:
                    bpm = _analyze_bpm(item_path)
                    if bpm is not None:
                        item.bpm = int(round(bpm))
                        item_result["bpm"] = item.bpm
                        log.debug(f"Item {item_id}: BPM = {item.bpm}")

                if analyze_key:
                    key = _analyze_key(item_path)
                    if key is not None:
                        item.initial_key = key
                        item_result["initial_key"] = key
                        log.debug(f"Item {item_id}: Key = {key}")

                item.store()
                item.try_write()

                results["analyzed"].append(item_result)
                log.info(f"Successfully analyzed item {item_id}")

            except Exception as exc:
                log.error(f"Error analyzing item {item_id}: {exc}", exc_info=True)
                results["errors"].append(
                    {
                        "item_id": item_id,
                        "path": item_path,
                        "error": str(exc),
                    }
                )

        log.info(
            f"Analysis complete: {len(results['analyzed'])} analyzed, "
            f"{len(results['errors'])} errors, {len(results['skipped'])} skipped"
        )
        return results
    finally:
        if managed_library and close_library:
            with suppress(Exception):
                internal_close = getattr(lib, "_close", None)
                if callable(internal_close):
                    internal_close()
            with suppress(Exception):
                close_method = getattr(lib, "close", None)
                if callable(close_method):
                    close_method()
            with suppress(Exception):
                conn = getattr(lib, "conn", None)
                if conn is not None:
                    conn.close()
            with suppress(Exception):
                raw_conn = getattr(lib, "_connection", None)
                if raw_conn is not None:
                    raw_conn.close()
                    setattr(lib, "_connection", None)
            with suppress(Exception):
                del lib
                gc.collect()


def _analyze_bpm(file_path: str) -> float | None:
    """Analyze BPM of an audio file using aubio.

    Parameters
    ----------
    file_path : str
        Path to the audio file.

    Returns
    -------
    float | None
        The detected BPM, or None if analysis failed.
    """
    try:
        import aubio
    except ImportError:
        log.warning("aubio library not available, skipping BPM analysis")
        return None

    try:
        win_s = 1024  # FFT window size
        hop_s = 512  # hop size
        samplerate = 0  # Use file's native sample rate

        source = aubio.source(file_path, samplerate, hop_s)
        samplerate = source.samplerate
        tempo = aubio.tempo("default", win_s, hop_s, samplerate)

        total_frames = 0
        beats = []

        while True:
            samples, read = source()
            is_beat = tempo(samples)
            if is_beat:
                beats.append(tempo.get_last_s())
            total_frames += read
            if read < hop_s:
                break

        # Calculate BPM from detected beats
        if len(beats) >= 2:
            # Calculate intervals between beats
            intervals = [beats[i + 1] - beats[i] for i in range(len(beats) - 1)]
            if intervals:
                avg_interval = sum(intervals) / len(intervals)
                if avg_interval > 0:
                    bpm = 60.0 / avg_interval
                    # Sanity check: BPM should be in reasonable range
                    if 40 <= bpm <= 250:
                        return bpm
                    elif 20 <= bpm < 40:
                        return bpm * 2  # Double if too slow
                    elif 250 < bpm <= 500:
                        return bpm / 2  # Halve if too fast

        # Fallback: use aubio's confidence-weighted BPM
        bpm = tempo.get_bpm()
        if 40 <= bpm <= 250:
            return bpm

        return None

    except Exception as e:
        log.warning(f"BPM analysis failed for {file_path}: {e}")
        return None


def _analyze_key(file_path: str) -> str | None:
    """Analyze musical key of an audio file using keyfinder-cli.

    Parameters
    ----------
    file_path : str
        Path to the audio file.

    Returns
    -------
    str | None
        The detected key in standard notation (e.g., "Cm", "G"),
        or None if analysis failed.
    """
    # Check if keyfinder-cli is available
    keyfinder_bin = shutil.which("keyfinder-cli")
    if keyfinder_bin is None:
        log.warning("keyfinder-cli not found in PATH, skipping key analysis")
        return None

    try:
        result = subprocess.run(
            [keyfinder_bin, file_path],
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout
        )

        if result.returncode != 0:
            log.warning(f"keyfinder-cli failed for {file_path}: {result.stderr}")
            return None

        # Parse the output - keyfinder-cli outputs the key on stdout
        key_output = result.stdout.strip()

        # keyfinder-cli outputs in format: "filename\tkey"
        # or just "key" depending on version
        if "\t" in key_output:
            key = key_output.split("\t")[-1].strip()
        else:
            key = key_output.strip()

        # Validate the key is in a recognized format
        valid_keys = [
            "C", "Cm", "C#", "C#m", "Db", "Dbm",
            "D", "Dm", "D#", "D#m", "Eb", "Ebm",
            "E", "Em",
            "F", "Fm", "F#", "F#m", "Gb", "Gbm",
            "G", "Gm", "G#", "G#m", "Ab", "Abm",
            "A", "Am", "A#", "A#m", "Bb", "Bbm",
            "B", "Bm",
        ]

        if key in valid_keys:
            return key

        # Try to normalize the key format
        key_normalized = key.replace(" minor", "m").replace(" major", "")
        if key_normalized in valid_keys:
            return key_normalized

        log.warning(f"Unrecognized key format '{key}' for {file_path}")
        return key  # Return as-is even if not in standard format

    except subprocess.TimeoutExpired:
        log.warning(f"Key analysis timed out for {file_path}")
        return None
    except Exception as e:
        log.warning(f"Key analysis failed for {file_path}: {e}")
        return None
