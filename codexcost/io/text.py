from codexcost.core import TokenCount
from dataclasses import asdict
import json
import logging
from pathlib import Path
import sys
from typing import Iterable, IO


class CreditsTokenCountHandler:
    def __init__(self, file:IO|Path|None=None, extended_info=False, datetime_format='%m-%d %H:%M'):
        self.file = file
        self.extended_info = extended_info
        self.datetime_format = datetime_format
        self.credits = 0

    def __call__(self, token_counts: Iterable[TokenCount]):
        '''Append credits for a list of TokenCount'''
        counts = list(token_counts)
        if len(counts) == 0:
            return

        add_credits = sum(count.credits for count in counts)
        self.credits += add_credits
        newest = max(counts, key=lambda x: x.timestamp)

        if self.file is None:
            io = sys.stdout
        elif isinstance(self.file, Path):
            io = self.file.open('a', encoding='utf-8', newline='\n')
        else:
            io = self.file

        if self.extended_info:
            print(f'{self.credits:.3f}\t+{add_credits:.3f} {newest.timestamp.strftime(self.datetime_format)} {newest.project} {newest.model}', file=io)
        else:
            print(f'{self.credits:.3f}', file=io)
    
        if isinstance(self.file, Path):
            io.close()


def write_csv(token_counts: Iterable[TokenCount], file:IO|Path|None=None, incremental=False):
    '''Export s list of TokenCount as csv'''
    if not incremental:
        logging.info('Output token counts as csv.')

    if file is None:
        io = sys.stdout
    elif isinstance(file, Path):
        io = file.open('w' if not incremental else 'a', encoding='utf-8', newline='\n')
    else:
        io = file

    try:
        if not incremental:
            print('session,project,timestamp,model,uncached_input_tokens,cached_input_tokens,output_tokens,reasoning_output_tokens,credits', file=io)

        for count in token_counts:
            print(count.id, count.project, count.timestamp.isoformat(), count.model,
                count.uncached_input_tokens, count.cached_input_tokens,
                count.output_tokens, count.reasoning_output_tokens, count.credits,
                sep=',', file=io)
    finally:
        if isinstance(file, Path):
            io.close()

def write_json(token_counts: Iterable[TokenCount], file:IO|Path|None=None):
    '''Export list of TokenCount as json'''
    logging.info('Output token counts as json.')

    if file is None:
        io = sys.stdout
    elif isinstance(file, Path):
        io = file.open('w', encoding='utf-8', newline='\n')
    else:
        io = file

    try:
        print('[', file=io)

        first = True
        for count in token_counts:
            if not first:
                print(',', file=io)
            else:
                first = False
            
            data = asdict(count)
            data['timestamp'] = data['timestamp'].isoformat()
            data['credits'] = count.credits

            print(json.dumps(data, separators=(',', ':')), end='', file=io)
        
        if not first:
            print(file=io)
        print(']', file=io)
    finally:
        if isinstance(file, Path):
            io.close()

def write_jsonl(token_counts: Iterable[TokenCount], file:IO|Path|None=None, incremental=False):
    '''Export list of TokenCount as jsonl'''
    if not incremental:
        logging.info('Output token counts as jsonl.')

    if file is None:
        io = sys.stdout
    elif isinstance(file, Path):
        io = file.open('w' if not incremental else 'a', encoding='utf-8', newline='\n')
    else:
        io = file

    try:
        for count in token_counts:
            data = asdict(count)
            data['timestamp'] = data['timestamp'].isoformat()
            data['credits'] = count.credits
            
            print(json.dumps(data, separators=(',', ':')), file=io)
    finally:
        if isinstance(file, Path):
            io.close()
