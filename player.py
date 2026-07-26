"""
Player entity with keyboard-controlled movement.
"""

import pygame


class Player:
    """Represents the player with position and movement."""

    def __init__(self, start_x: int = 0, start_y: int = 50):
        self.x = float(start_x)
        self.y = float(start_y)
        self.speed = 4.0
        self.velocity_x = 0.0
        self.velocity_y = 0.0

    def update(self, keys, dt: float = 1.0):
        """Update player position based on pressed keys."""
        self.velocity_x = 0.0
        self.velocity_y = 0.0

        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.velocity_x = -self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.velocity_x = self.speed
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.velocity_y = -self.speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.velocity_y = self.speed

        self.x += self.velocity_x * dt
        self.y += self.velocity_y * dt

    def get_pos(self):
        """Get player position as (x, y)."""
        return self.x, self.y