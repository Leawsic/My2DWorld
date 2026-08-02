"""
Spectator Mode: free-flight camera movement.
- WASD/arrows move freely in all directions (no collision)
- Right-mouse drag pans the camera
- No player rendering
- No block interaction
"""

import pygame

from gamemodes import SPECTATOR, GameModeBase


class SpectatorMode(GameModeBase):
    """Free-flight spectator mode with no physics or collisions."""

    def __init__(self, player, world):
        super().__init__(player, world)
        self.name = SPECTATOR
        self.speed = 4.0  # blocks per second

    def update(self, dt, keys, mouse_buttons, mx, my, block_size, hovered=None):
        # WASD / arrows: free movement in world coordinates.
        # World Y increases upward.
        vx = 0.0
        vy = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            vx = -self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            vx = self.speed
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            vy = self.speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            vy = -self.speed

        self.player.x += vx * dt
        self.player.y += vy * dt

    def render_player(self, screen, camera_x, camera_y, block_size):
        # Spectator has no visible player.
        pass