from codexcost.core import TokenCount, parse_token_counts, SessionState, CODEX_SESSION_PATH, find_sessions
from typing import Generator, Iterable, Callable
from datetime import datetime
import logging
from pathlib import Path
from queue import Queue, Empty

try:
    from watchdog.events import FileSystemEventHandler, FileSystemEvent, FileModifiedEvent, FileCreatedEvent
    from watchdog.observers import Observer
except ModuleNotFoundError as e:
    logging.error('Unable to find watchdog. Please install watchdog>=6.0.0', exc_info=e)
    raise


def watch(start_timestamp:datetime, output:Callable[[Iterable[TokenCount]],None], base_path: Path|None=None):
    '''Show and continuously update session credit information.'''
    if base_path is None:
        base_path = CODEX_SESSION_PATH
    
    sessions:dict[Path,tuple[int,SessionState]] = {}

    try:
        # seed with current sessions to build initial sessions state index
        for session in _watch_session_changes(base_path, seed=find_sessions(base_path)):
            size, state = sessions.get(session, (0, SessionState()))
            new_size = session.stat().st_size

            # modifications flushed changed to file so parse new tokens
            if new_size > size:
                try:
                    gen = parse_token_counts(session, session_state=state)
                    
                    while True:
                        count = next(gen)
                        # only output relevant token_counts
                        if count.timestamp >= start_timestamp:
                            output([count])
                except StopIteration as e:
                    state = e.value
                
                # store changed session infos
                sessions[session] = (new_size, state)
    except KeyboardInterrupt:
        pass

def _watch_session_changes(path:Path, seed:Iterable[Path|str]|None=None) -> Generator[Path,None,None]:
    '''Watch a directory recusively for new files and file modifications.
    '''
    queue:Queue[FileSystemEvent] = Queue()

    if seed is not None:
        for src in seed:
            queue.put(FileSystemEvent(str(src)))

    class EnqueueEventHandler(FileSystemEventHandler):
        def on_any_event(self, event:FileSystemEvent):
            if str(event.src_path).endswith('.jsonl'):
                queue.put(event)
    
    observer = Observer()
    observer.schedule(EnqueueEventHandler(), str(path), recursive=True, event_filter=[FileModifiedEvent, FileCreatedEvent])
    observer.start()

    try:
        while True:
            try:
                yield Path(str(queue.get(timeout=0.2).src_path))
            except Empty:
                pass
    finally:
        observer.stop()
        observer.join()
