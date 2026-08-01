"""
Game mode system for My2DWorld.
Contains mode constants, the base class, and a factory function.
"""

SPECTATOR = "spectator"
CREATIVE = "creative"

MODE_LIST = [SPECTATOR, CREATIVE]


class GameModeBase:
    """Base class for all game modes."""

    def __init__(self, player, world):
        self.player = player
        self.world = world
        self.name = SPECTATOR

    def handle_event(self, event):
        """
        Handle a mode-specific pygame event.
        Return True if the event was consumed (e.g. jump on space).
        """
        return False

    def update(self, dt, keys, mouse_buttons, mx, my, block_size, hovered=None):
        """
        Per-frame update.
        - dt: normalized delta (60fps = 1.0)
        - hovered: (wx, wy, block_type) or None (for block interaction)
        """
        pass

    def render_player(self, screen, camera_x, camera_y, block_size):
        """Render the player (no-op for modes without a visible player)."""
        pass

    def render_particles(self, screen, camera_x, camera_y, block_size):
        """Render particles (no-op for modes without particles)."""
        pass

    def reset(self):
        """Reset mode-specific state when switching modes."""
        pass


def create_mode(mode_name, player, world, textures=None, username=""):
    """Factory: create a game mode instance by name."""
    if mode_name == CREATIVE:
        from gamemodes.creative import CreativeMode
        return CreativeMode(player, world, username=str(username or ""),
                            textures=textures or {})
    from gamemodes.spectator import SpectatorMode
    return SpectatorMode(player, world)
