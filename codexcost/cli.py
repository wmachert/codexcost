from codexcost.__version__ import __version__
from codexcost.core import find_sessions, parse_token_counts
from codexcost.io.text import CreditsLogWriter, write_csv, write_json, write_jsonl
import functools
import logging
from pathlib import Path
from argparse import ArgumentParser
from datetime import datetime, timezone
from typing import Iterable
import sys


def build_argparser() -> ArgumentParser:
    '''Build argparse based parser for the codexinfo cli'''
    argparser = ArgumentParser(prog='codexcost', description='Collect and output codex usage information.')
    argparser.add_argument('-a', '--all-history', action='store_true',
        help='consider all available token counts, instead of only the current month (default: %(default)s)')
    argparser.add_argument('-f', '--follow', action='store_true',
        help='follow session updates and continously refresh credit count')
    argparser.add_argument('-o', '--output', type=Path, metavar='OUTPUT_FILE', help='write output to file %(metavar)s')
    argparser.add_argument('-t', '--type', default='compact', choices='compact|csv|ext|json|jsonl|xlsx'.split('|'),
        help='format of the codex information (default: %(default)s)')
    argparser.add_argument('-v', '--verbose', action='count', default=0, help='verbose output; repeat to increase verbosity')
    argparser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    return argparser

def main(args: Iterable[str] | None = None) -> int:
    '''Collect and output codex usage information'''
    argp = build_argparser().parse_args(args if args is not None else sys.argv[1:])

    # configure log level from verbosity
    match argp.verbose:
        case 0:
            level = logging.ERROR
        case 1:
            level = logging.INFO
        case _:
            level = logging.DEBUG

    logging.basicConfig(level=level, stream=sys.stderr,
        format='%(asctime)s %(filename)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # start information collection either at start of current month...
    if not argp.all_history:
        start_timestamp = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # ...or collect all sessions - assuming unixtime predates ai agent logs
    else:
        start_timestamp = datetime(1970, 1, 1, tzinfo=timezone.utc)

    # setup output target
    match argp.type:
        case 'compact':
            write = CreditsLogWriter(file=argp.output, extended_info=False)
        case 'csv':
            write = functools.partial(write_csv, file=argp.output, log_mode=argp.follow)
        case 'ext':
            write = CreditsLogWriter(file=argp.output, extended_info=True)
        case 'json':
            if argp.follow:
                logging.error('Json format is unsuitable for follow mode. Choose another format.')
                return 1
            write = functools.partial(write_json, file=argp.output)
        case 'jsonl':
            write = functools.partial(write_jsonl, file=argp.output, log_mode=argp.follow)
        case 'xlsx':
            if argp.follow:
                logging.error('Xlsx format is unsuitable for follow mode. Choose another format.')
                return 1
            if argp.output is None:
                logging.error('Empty parameter output. Xlsx format requires OUTPUT_FILE.')
                return 1

            from codexcost.io.excel import write_xlsx
            write = functools.partial(write_xlsx, file=argp.output)

    try:
        # follow mode
        if argp.follow:
            from codexcost.watcher import watch
            watch(start_timestamp, output=write)

        # output mode
        else:
            counts = sorted((count
                    for session in find_sessions()
                    for count in parse_token_counts(session)
                    if count.timestamp >= start_timestamp),
                key=lambda x: x.timestamp)

            write(counts)
    except (BrokenPipeError, OSError) as e:
        logging.error('Encountered piping error while writing output', exc_info=e)
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
