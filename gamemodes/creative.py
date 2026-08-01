"""
Creative Mode: block-breaking with particles and player physics.
- Player uses physics engine (gravity, jump, double-jump, flying)
- Left click breaks blocks with particle effects
- Player is rendered with animation
"""

import pygame

from gamemodes import CREATIVE, GameModeBase
from logger import log_event
from particles import ParticleSystem


class CreativeMode(GameModeBase):
    """Creative mode: physics player + block breaking + particles."""

    def __init__(self, player, world, username="", textures=None):
        super().__init__(player, world)
        self.name = CREATIVE
        self.username = username
        self.textures = textures or {}
        self.particles = ParticleSystem()

        # Cooldown to avoid breaking the same block every frame while held.
        self.break_cooldown = 0.0  # remaining frames until next allowed break
        self.break_interval = 8    # frames between breaks while holding LMB

    # ------------------------------------------------------------------
    # GameModeBase overrides
    # ------------------------------------------------------------------
    def handle_event(self, event):
        """Handle mode events (currently none special)."""
        return False

    def update(self, dt, keys, mouse_buttons, mx, my, block_size, hovered=None):
        """Per-frame update: player physics + particles + block breaking."""
        # Update player with physics/collision.
        self.player.update(keys, dt, self.world)

        # Particle physics.
        self.particles.update(dt)

        # Block breaking on left mouse button.
        if self.break_cooldown > 0:
            self.break_cooldown -= 1
        if hovered is not None and mouse_buttons and mouse_buttons[0]:
            if self.break_cooldown <= 0:
                wx, wy, block_type = hovered
                self._break_block(wx, wy, block_type, block_size)
                self.break_cooldown = self.break_interval

    def render_player(self, screen, camera_x, camera_y, block_size):
        """Draw the animated player."""
        self.player.render(screen, camera_x, camera_y, block_size)

    def render_particles(self, screen, camera_x, camera_y, block_size):
        """Draw particles."""
        self.particles.render(screen, camera_x, camera_y, block_size)

    def reset(self):
        """Reset mode-specific state."""
        self.player.reset()
        self.particles.particles.clear()
        self.break_cooldown = 0

    # ------------------------------------------------------------------
    # Block breaking
    # ------------------------------------------------------------------
    def _break_block(self, wx, wy, block_type, block_size):
        """Break a block at (wx, wy) and spawn particles."""
        broken = self.world.break_block(wx, wy)
        if broken:
            self.particles.spawn(wx, wy, broken, self.textures)
            log_event(f"Block Broken: user={self.username} x={wx} y={wy} block={broken}")