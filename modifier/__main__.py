from __future__ import annotations
import os
import time
from abc import ABC, abstractmethod

from dataclasses import dataclass
from functools import partial
from itertools import cycle
from textwrap import dedent
from typing import Any, ClassVar, Literal, Protocol
import atexit

from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.Devices.StreamDeckPedal import StreamDeckPedal
import pyautogui


class ActionHandler(Protocol):
    def __call__(self, is_depressed: bool) -> Any:
        ...


@dataclass
class Action(ABC):
    """base class for all actions

    handles registration/callbacks
    """

    idx: int

    _registry: ClassVar[dict[int, ActionHandler]] = {}

    def __post_init__(self):
        type(self)._registry[self.idx] = self

    @abstractmethod
    def __call__(self, is_depressed: bool) -> Any:
        """called on pedal down/up"""
        raise NotImplementedError

    @classmethod
    def streamdeck_callback(cls, deck: StreamDeckPedal, pedal_idx: int, is_depressed: bool):
        if not (action := cls._registry.get(pedal_idx)):
            return
        action(is_depressed)

    @classmethod
    def display_registry(cls):
        cls._registry = dict(sorted(cls._registry.items()))
        for action in cls._registry.values():
            print(action)


@dataclass
class QuickSwitch(Action):
    """switch to an app while the pedal is held down then switch back to where you came
    from on key up
    """

    app_name: str

    def __call__(self, is_depressed: bool):
        if is_depressed:
            os.system(f"open {app_path(self.app_name)}")
        else:
            pyautogui.hotkey("command", "command", "tab")


@dataclass
class Switcher(Action):
    """switch between sequence of apps in order"""

    app_names: list[str]

    def __post_init__(self):
        super().__post_init__()
        self._app_names = cycle(self.app_names)

    def __call__(self, is_depressed: bool):
        if is_depressed:
            os.system(f"open {app_path(next(self._app_names))}")


@dataclass
class Modifier(Action):
    """press/release modifier keys on key down/up"""

    key: str

    def __post_init__(self):
        super().__post_init__()
        atexit.register(partial(self._execute, "up"))
        self._compile_script()

    def _compile_script(self):
        """compile applescripts to press/release modifier keys"""
        script = """
        tell application "System Events"
            key {up_or_down} {key}
        end tell
        """
        script = dedent(script)
        for up_or_down in ("up", "down"):
            path = self._script_path(up_or_down)
            with open(path, "w") as f:
                data = script.format(up_or_down=up_or_down, key=self.key)
                f.write(data)
            os.system(f"osacompile -o {path} {path}")

    def _script_path(self, up_or_down) -> str:
        return f"/tmp/.osa_{self.key}_{up_or_down}.scpt"

    def __call__(self, is_depressed: bool):
        self._execute("down" if is_depressed else "up")

    def _execute(self, up_or_down: Literal["up", "down"]) -> None:
        os.system(f"osascript {self._script_path(up_or_down)}")


def app_path(path: str) -> str:
    if path.startswith(("/", "~")):
        return path
    return f"/Applications/{path}"


def register_actions():
    Modifier(0, "option")
    Modifier(1, "shift")
    Modifier(2, "control")
    QuickSwitch(0, r"Brave\ Browser.app")
    Switcher(
        2,
        [
            r"Visual\ Studio\ Code.app",
            r"Brave\ Browser.app",
            r"~/Applications/Brave\ Browser\ Apps.localized/Messages.app",
        ],
    )


def __main():
    register_actions()
    Action.display_registry()
    deck: StreamDeckPedal = DeviceManager().enumerate()[0]
    deck.open()
    deck.set_key_callback(Action.streamdeck_callback)
    time.sleep(40)


if __name__ == "__main__":
    __main()
