from __future__ import annotations

from dataclasses import dataclass
from functools import partial
import os
from typing import ClassVar, Literal
import atexit
import pyautogui
import applescript
import keyboard
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.Devices.StreamDeckPedal import StreamDeckPedal

def _exec_applescript(cmd: str):
    script = [
        'tell application "System Events"',
        cmd,
        'end tell'
    ]
    cmd = " -e ".join(map(repr, script))
    print(cmd)
    os.system(f"osascript -e {cmd}")

@dataclass
class Modifier:
    idx: int
    key: str

    _registry: ClassVar[dict[int, Modifier]] = {}

    @classmethod
    def streamdeck_callback(cls, deck: StreamDeckPedal, pedal_idx: int, is_depressed: bool):
        if not (modifier := cls._registry.get(pedal_idx)):
            return
        modifier(is_depressed)

    def __post_init__(self):
        Modifier._registry[self.idx] = self
        atexit.register(partial(self._execute, "up"))

    def __call__(self, is_depressed: bool):
        self._execute("down" if is_depressed else "up")

    def _execute(self, up_or_down: Literal["up", "down"]) -> None:
        start = time.perf_counter()
        my_as_cmd = f"key {up_or_down} {self.key}"
        _exec_applescript(my_as_cmd)

        # applescript.tell.app("System Events", f"key {up_or_down} {self.key}")
        # fn_name = f"key{up_or_down.title()}"
        fn_name = 'press' if up_or_down == 'down' else 'release'
        # print(keyboard.parse_hotkey(self.key))
        # getattr(keyboard, fn_name)(self.key)
        # keyboard.press(self.key)
        # getattr(pyautogui, fn_name)(self.key)
        print(fn_name, self.key, time.perf_counter() - start)



Modifier(0, "option")
Modifier(1, "shift")
Modifier(2, "control")


deck: StreamDeckPedal = DeviceManager().enumerate()[0]
deck.open()
print(deck)
deck.set_key_callback(Modifier.streamdeck_callback)
import time
time.sleep(40)
