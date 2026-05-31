from dataclasses import dataclass
from datetime import datetime
import json
import logging
import os
from pathlib import Path
from typing import Generator, Callable, Iterable


# default fallback model used for cost calculation when rates for used model are unknown
DEFAULT_MODEL = 'gpt-5.5'

# 1 million token unit
MT = 1_000_000

# chatgpt enterprise credit rates per token
# see: https://help.openai.com/en/articles/20001106-codex-rate-card#codex-rate-card-token-based-pricing
MODEL_RATES: dict[str,dict[str,float]] = {
    'gpt-5.5': {'input': 125 / MT, 'cached': 12.5 / MT, 'output': 750 / MT},
    'gpt-5.4': {'input': 62.5 / MT, 'cached': 6.25 / MT, 'output': 375 / MT},
    'gpt-5.4-mini': {'input': 18.75 / MT, 'cached': 1.875 / MT, 'output': 113 / MT},
    # 'gpt-5.3-codex-spark': {'input': None, 'cached': None, 'output': None},
    'gpt-5.3-codex': {'input': 43.75 / MT, 'cached': 4.375 / MT, 'output': 350 / MT},
    'gpt-5.2': {'input': 43.75 / MT, 'cached': 4.375 / MT, 'output': 350 / MT},
    'gpt-image-2.0-image': {'input': 200 / MT, 'cached': 50 / MT, 'output': 750 / MT},
    'gpt-image-2.0-text': {'input': 125 / MT, 'cached': 31.25 / MT, 'output': 250 / MT},
}


@dataclass
class TokenCount:
    id: str | None
    project: str | None
    timestamp: datetime
    model: str | None
    
    uncached_input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_output_tokens: int
    credits: float = 0.0

@dataclass
class SessionContext:
    path: Path
    file_size = 0
    last_line = 0
    total_tokens = 0.0
    id:str|None = None
    project:str|None = None
    model:str|None = None

def find_sessions(base_path: Path|None=None) -> Generator[Path, None, None]:
    if base_path is None:
        base_path = session_path()

    '''Get all codex session files.'''
    # read codex sessions from saved jsonl files
    for file in base_path.rglob('*.jsonl'):
        if file.is_file():
            yield file

def parse_session(context:SessionContext|Path) -> Generator[TokenCount, None, SessionContext]:
    '''Extract all token count informations from a codex session file.
    '''
    # parse from the beginning
    if isinstance(context, Path):
        skip_lines, context = 0, SessionContext(context)
    # parse from the last parsed line
    else:
        skip_lines, context.last_line = context.last_line, 0

    with context.path.open('r', encoding='utf-8') as file:
        for line in file:
            context.last_line += 1

            # skip processing lines until a new line
            if context.last_line <= skip_lines:
                continue

            data = json.loads(line)

            match data['type']:
                # metadata
                case 'session_meta':
                    context.id = data['payload']['id']
                    context.project = Path(data['payload']['cwd']).name

                    logging.debug('Session identified. id=%s project=%s', context.id, context.project)

                # model switch
                case 'turn_context':
                    context.model = data['payload']['model']
                    
                    logging.debug('Session switched model. id=%s model=%s', context.id, context.model)

                # token usage, skip event with empty $.payload.info (rate limit messages)
                case 'event_msg' if data['payload']['type'] == 'token_count' and data['payload']['info'] is not None:
                    info = data['payload']['info']
                    ttu_total_token = info['total_token_usage']['total_tokens']

                    # suppress token_count messages that do not advance the total_tokens (token_count refresh messages)
                    if context.total_tokens < ttu_total_token:
                        context.total_tokens = ttu_total_token
                        ltu = info['last_token_usage']
                        cached_input_tokens = ltu['cached_input_tokens']

                        count = TokenCount(context.id, context.project, datetime.fromisoformat(data['timestamp']), context.model,
                            uncached_input_tokens=ltu['input_tokens'] - cached_input_tokens, cached_input_tokens=cached_input_tokens,
                            output_tokens=ltu['output_tokens'], reasoning_output_tokens=ltu['reasoning_output_tokens'])
                        count.credits = _calculate_credits(count)
                        
                        logging.debug('Token usage in Session. id=%s, timestamp=%s, model=%s total_tokens=%s credits=%s',
                            count.id, count.timestamp.strftime('%Y-%m-%d'), count.model,
                            count.uncached_input_tokens + count.cached_input_tokens + count.output_tokens, count.credits)
                        yield count
    
    return context

def parse_session_incremental(context:SessionContext, output_handler:Callable[[Iterable[TokenCount]],None], filter:Callable[[TokenCount], bool]|None=None) -> SessionContext:
    '''Incrementally parse a session context, calling an output filter with TokenCount events that are optionally filtered.
    '''
    # check file size for changes
    size = context.path.stat().st_size

    # changes since last parse
    if size > context.file_size:
        context.file_size = size

        try:
            gen = parse_session(context)
            
            while True:
                count = next(gen)
                # only output relevant token_counts
                if filter is None or filter(count):
                    output_handler([count])
        except StopIteration as e:
            return e.value
    return context

def session_path() -> Path:
    codex_home = os.getenv('CODEX_HOME')
    return ((Path.home() / '.codex') if codex_home is None else Path(codex_home)) / 'sessions'

def _calculate_credits(count: TokenCount) -> float:
    '''Calculate accumulated credits for used uncached input, cached input, and output tokens.
    
    Credits are assumed to be derived from a shared credit pool, enabling per-token usage rather than fixed million-token blocks.
    '''
    if count.model not in MODEL_RATES:
        logging.warning('Missing model cost; using default model to calculate cost. id=%s model=%s default_model=%s', count.id, count.model, DEFAULT_MODEL)

    cost = MODEL_RATES[count.model if count.model in MODEL_RATES else DEFAULT_MODEL]

    return count.uncached_input_tokens * cost['input'] \
        + count.cached_input_tokens * cost['cached'] \
        + count.output_tokens * cost['output']
