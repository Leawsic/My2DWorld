"""Minecraft-style chat input and the small command set supported in-game."""

import pygame


class Chat:
    COMMANDS = ("gamemode", "speed", "movespeed", "debug")
    ARGUMENTS = {
        "gamemode": ("creative", "spectator"),
        "debug": ("on", "off", "true", "false"),
    }
    MAX_HISTORY = 200
    MAX_VISIBLE_MESSAGES = 9
    MESSAGE_HOLD_SECONDS = 4.0
    MESSAGE_FADE_SECONDS = 3.0
    LINE_HEIGHT = 22

    def __init__(self, font):
        self.font = font
        self.open = False
        self.text = ""
        self.messages = []
        self.input_history = []
        self.history_cursor = None
        self.scroll_offset = 0
        self.suggestion_index = 0
        self.suggestion_options = []

    def open_chat(self, initial_text=""):
        self.open = True
        self.text = initial_text
        self.scroll_offset = 0
        self.suggestion_index = 0
        self.suggestion_options = []
        self.history_cursor = None

    def _suggestions(self):
        if not self.text.startswith("/"):
            return []
        body = self.text[1:]
        parts = body.split()
        trailing_space = body.endswith(" ")
        if not parts:
            return ["/" + command for command in self.COMMANDS]
        command = parts[0].lower()
        if len(parts) == 1 and not trailing_space:
            return ["/" + name for name in self.COMMANDS if name.startswith(command)]
        args = self.ARGUMENTS.get(command, ())
        prefix = "" if trailing_space else parts[-1].lower()
        return [value for value in args if value.startswith(prefix)]

    def _reset_suggestions(self):
        self.suggestion_index = 0
        self.suggestion_options = []

    def add_message(self, text):
        self.messages.append({"text": str(text), "age": 0.0})
        self.messages = self.messages[-self.MAX_HISTORY:]
        self.scroll_offset = 0

    def update(self, dt_seconds):
        for message in self.messages:
            message["age"] += dt_seconds

    def scroll(self, amount):
        """Scroll history upward for positive mouse-wheel movement."""
        if not self.open or not self.messages:
            return False
        max_scroll = max(0, len(self.messages) - self.MAX_VISIBLE_MESSAGES)
        self.scroll_offset = max(0, min(max_scroll, self.scroll_offset + amount))
        return True

    def handle_event(self, event):
        if not self.open or event.type != pygame.KEYDOWN:
            return None
        if event.key == pygame.K_ESCAPE:
            self.open = False
            self.text = ""
            self.scroll_offset = 0
        elif event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
            self._reset_suggestions()
        elif event.key == pygame.K_TAB:
            if self.suggestion_index == 0 or not self.suggestion_options:
                self.suggestion_options = self._suggestions()
            suggestions = self.suggestion_options
            if suggestions:
                suggestion = suggestions[self.suggestion_index % len(suggestions)]
                self.suggestion_index += 1
                if suggestion.startswith("/"):
                    self.text = suggestion + (" " if suggestion[1:] in self.ARGUMENTS else "")
                    self.suggestion_index = 0
                    self.suggestion_options = []
                else:
                    prefix = self.text.rsplit(" ", 1)[0] if " " in self.text else self.text
                    self.text = prefix + " " + suggestion
        elif event.key == pygame.K_RETURN:
            text = self.text.strip()
            if text:
                self.input_history.append(text)
                self.input_history = self.input_history[-self.MAX_HISTORY:]
            self.open = False
            self.text = ""
            self.history_cursor = None
            return text
        elif event.key == pygame.K_UP:
            if self.input_history:
                if self.history_cursor is None:
                    self.history_cursor = len(self.input_history) - 1
                else:
                    self.history_cursor = max(0, self.history_cursor - 1)
                self.text = self.input_history[self.history_cursor]
                self._reset_suggestions()
        elif event.key == pygame.K_DOWN:
            if self.history_cursor is not None:
                self.history_cursor += 1
                if self.history_cursor >= len(self.input_history):
                    self.history_cursor = None
                    self.text = ""
                else:
                    self.text = self.input_history[self.history_cursor]
                self._reset_suggestions()
        elif event.unicode and event.unicode.isprintable() and len(self.text) < 160:
            self.text += event.unicode
            self._reset_suggestions()
        return None

    def draw(self, screen, width, height):
        input_top = height - 42 if self.open else height - 10
        if self.open:
            messages = self.messages
        else:
            messages = [message for message in self.messages
                        if message["age"] < self.MESSAGE_HOLD_SECONDS + self.MESSAGE_FADE_SECONDS]

        if messages:
            end = len(messages) - (self.scroll_offset if self.open else 0)
            start = max(0, end - self.MAX_VISIBLE_MESSAGES)
            visible_messages = messages[start:end]
            top = input_top - len(visible_messages) * self.LINE_HEIGHT - 6
            for index, message in enumerate(visible_messages):
                alpha = 255
                if not self.open and message["age"] > self.MESSAGE_HOLD_SECONDS:
                    progress = ((message["age"] - self.MESSAGE_HOLD_SECONDS)
                                / self.MESSAGE_FADE_SECONDS)
                    alpha = max(0, int(255 * (1.0 - progress)))
                if alpha <= 0:
                    continue
                text = self.font.render(message["text"], True, (255, 255, 255))
                y = top + index * self.LINE_HEIGHT
                background = pygame.Surface((min(width - 16, text.get_width() + 16),
                                             self.LINE_HEIGHT), pygame.SRCALPHA)
                background.fill((0, 0, 0, max(0, alpha // 2)))
                screen.blit(background, (8, y - 1))
                text.set_alpha(alpha)
                screen.blit(text, (12, y + 2))

            if self.open and len(self.messages) > self.MAX_VISIBLE_MESSAGES:
                track = pygame.Rect(width - 14, top, 5,
                                    len(visible_messages) * self.LINE_HEIGHT)
                handle_height = max(14, int(track.height * self.MAX_VISIBLE_MESSAGES
                                             / len(self.messages)))
                max_scroll = len(self.messages) - self.MAX_VISIBLE_MESSAGES
                handle_y = track.bottom - handle_height
                if max_scroll:
                    handle_y -= int((track.height - handle_height)
                                    * self.scroll_offset / max_scroll)
                pygame.draw.rect(screen, (30, 30, 30), track)
                pygame.draw.rect(screen, (190, 190, 190),
                                 (track.x, handle_y, track.width, handle_height))
        if self.open:
            rect = pygame.Rect(8, height - 42, width - 16, 32)
            pygame.draw.rect(screen, (0, 0, 0, 190), rect)
            pygame.draw.rect(screen, (220, 220, 220), rect, 1)
            screen.blit(self.font.render(self.text, True, (255, 255, 255)),
                        (rect.x + 8, rect.y + 6))
            suggestions = self._suggestions()
            if suggestions:
                suggestion_text = "  ".join(suggestions)
                suggestion_rect = pygame.Rect(8, rect.y - 28, width - 16, 24)
                pygame.draw.rect(screen, (0, 0, 0, 180), suggestion_rect)
                screen.blit(self.font.render(suggestion_text, True, (210, 210, 210)),
                            (suggestion_rect.x + 8, suggestion_rect.y + 4))


def execute_command(command, player, mode_name, show_debug, set_speed, respawn):
    """Execute a supported slash command and return (message, mode, debug)."""
    parts = command.strip().split()
    if not parts or parts[0] != "/":
        if command.startswith("/"):
            parts = command[1:].split()
        else:
            return command, mode_name, show_debug
    if not parts:
        return "", mode_name, show_debug
    name = parts[0].lower()
    if name == "gamemode" and len(parts) == 2 and parts[1].lower() in ("creative", "spectator"):
        mode_name = parts[1].lower()
        return f"Gamemode set to {mode_name}", mode_name, show_debug
    if name in ("speed", "movespeed") and len(parts) == 2:
        try:
            value = max(0.1, min(50.0, float(parts[1])))
            set_speed(value)
            return f"Movement speed set to {value:g}", mode_name, show_debug
        except ValueError:
            pass
    if name == "debug" and len(parts) == 2 and parts[1].lower() in ("on", "off", "true", "false"):
        show_debug = parts[1].lower() in ("on", "true")
        return f"Debug {'on' if show_debug else 'off'}", mode_name, show_debug
    return "Unknown or invalid command", mode_name, show_debug
