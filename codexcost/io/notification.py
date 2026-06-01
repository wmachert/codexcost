from codexcost.core import TokenCount
import logging
from typing import Iterable
try:
    from windows_toasts import Toast, WindowsToaster
except ModuleNotFoundError as e:
    logging.error('Unable to find windows-toast. Please install windows-toast>=1.3.1', exc_info=e)
    raise


class WindowsToastTokenCountHandler:
    def __init__(self, title="codex"):
        self.toaster = WindowsToaster(title)
        self.credits = 0

    def __call__(self, token_counts: Iterable[TokenCount]) -> None:
        counts = list(token_counts)
        if len(counts) == 0:
            return
        
        add_credits = sum(count.credits for count in counts)
        self.credits += add_credits
        newest = max(counts, key=lambda x: x.timestamp)

        print(self.credits)
        self.toaster.show_toast(Toast([f'{self.credits:.3f} credits used.', f'+{add_credits:.3f} credits in session: {newest.project} with model: {newest.model}']))
