"""Minecraft-style chat input and the small command set supported in-game."""

import pygame


class Chat:
    def __init__(self, font):
        self.font = font
        self.open = False
        self.text = ""
        self.messages = []

    def open_chat(self):
        self.open = True
        self.text = ""

    def add_message(self, text):
        self.messages.append(str(text))
        self.messages = self.messages[-8:]

    def handle_event(self, event):
        if not self.open or event.type != pygame.KEYDOWN:
            return None
        if event.key == pygame.K_ESCAPE:
            self.open = False
            self.text = ""
        elif event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
        elif event.key == pygame.K_RETURN:
            text = self.text.strip()
            self.open = False
            self.text = ""
            return text
        elif event.unicode and event.unicode.isprintable() and len(self.text) < 160:
            self.text += event.unicode
        return None

    def draw(self, screen, width, height):
        if self.messages:
            for index, message in enumerate(self.messages):
                shadow = self.font.render(message, True, (0, 0, 0))
                text = self.font.render(message, True, (255, 255, 255))
                y = height - 118 - index * 22
                screen.blit(shadow, (11, y + 1))
                screen.blit(text, (10, y))
        if self.open:
            rect = pygame.Rect(8, height - 42, width - 16, 32)
            pygame.draw.rect(screen, (0, 0, 0, 190), rect)
            pygame.draw.rect(screen, (220, 220, 220), rect, 1)
            screen.blit(self.font.render(self.text, True, (255, 255, 255)),
                        (rect.x + 8, rect.y + 6))


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
