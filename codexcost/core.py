import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Generator


# codex sessions base path
CODEX_SESSION_PATH = Path.home() / '.codex' / 'sessions'

# date format used in output
DATE_FORMAT = '%Y-%m-%d'

# date time format used in output
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

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
    session: str
    timestamp: datetime
    model: str | None
    uncached_input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_output_tokens: int
    credits: float

@dataclass
class SessionState:
    line_no = 0
    total_tokens = 0.0
    model:str|None = None


def find_sessions(base_path: Path|None=None) -> Generator[Path, None, None]:
    if base_path is None:
        base_path = CODEX_SESSION_PATH

    '''Get all codex session files.'''
    # read codex sessions from saved jsonl files
    for file in base_path.rglob('*.jsonl'):
        if file.is_file():
            yield file

def parse_token_counts(session: Path, id: str | None = None, session_state:SessionState|None=None) -> Generator[TokenCount, None, SessionState]:
    '''Extract all token count informations from a codex session file.
    '''
    if id is None:
        id = _session_id(session, CODEX_SESSION_PATH)

    if session_state is None:
        skip_lines, session_state = 0, SessionState()
    else:
        skip_lines, session_state.line_no = session_state.line_no, 0

    with session.open('r', encoding='utf-8') as file:
        for line in file:
            session_state.line_no += 1
            
            # skip lines until the next new line
            if session_state.line_no <= skip_lines:
                continue

            data = json.loads(line)

            match data['type']:
                # model switched
                case 'turn_context':
                    session_state.model = data['payload']['model']
                    logging.debug('Session %s switched to model: %s', id, session_state.model)

                # token count infos, skip token_count events with empty info (rate_limits reminder messages)
                case 'event_msg' if data['payload']['type'] == 'token_count' and data['payload']['info'] is not None:
                    info = data['payload']['info']
                    total_total_token = info['total_token_usage']['total_tokens']

                    # suppress token_count messages that do not advance the total_tokens (token_count refresh messages)
                    if session_state.total_tokens < total_total_token:
                        session_state.total_tokens = total_total_token
                        last_token_usage = info['last_token_usage']
                        cached_input_tokens = last_token_usage['cached_input_tokens']

                        count = TokenCount(session=id, timestamp=datetime.fromisoformat(data['timestamp']), model=session_state.model,
                            uncached_input_tokens=last_token_usage['input_tokens'] - cached_input_tokens, cached_input_tokens=cached_input_tokens,
                            output_tokens=last_token_usage['output_tokens'], reasoning_output_tokens=last_token_usage['reasoning_output_tokens'],
                            credits=0)
                        count.credits = _calculate_credits(count)
                        
                        logging.debug('Token count in Session. session=%s, datetime=%s, model=%s total_tokens=%s credits=%s',
                            count.session, count.timestamp.strftime(DATE_FORMAT), count.model,
                            count.uncached_input_tokens + count.cached_input_tokens + count.output_tokens, count.credits)
                        yield count
    
    return session_state

def _calculate_credits(count: TokenCount) -> float:
    '''Calculate accumulated credits for used uncached input, cached input, and output tokens.
    
    Credits are assumed to be derived from a shared credit pool, enabling per-token usage rather than fixed million-token blocks.
    '''
    if count.model not in MODEL_RATES:
        logging.warning('Missing model cost; using default model to calculate cost. session=%s model=%s default=%s', count.session, count.model, DEFAULT_MODEL)

    cost = MODEL_RATES[count.model if count.model in MODEL_RATES else DEFAULT_MODEL]

    return count.uncached_input_tokens * cost['input'] \
        + count.cached_input_tokens * cost['cached'] \
        + count.output_tokens * cost['output']

def _session_id(session:Path, base:Path):
    '''Calculate session id as unix path relative to a base path.
    
    This is usually the session filename path without the codex base session path prefix.
    '''
    return str(session.relative_to(base)).replace('\\', '/')
