"""
Particle system for block-breaking effects.
Particles are sampled from the block texture itself for authentic appearance.
"""

import random

import pygame

PARTICLE_COUNT = 8          # particles spawned per block break
PARTICLE_LIFE = 0.6         # seconds
GRAVITY = 14.0              # blocks/s²
AIR_DRAG = 0.95             # per-frame velocity multiplier


class Particle:
    """A single particle with world-space position and velocity."""

    def __init__(self, wx, wy, vx, vy, life, image):
        self.wx = wx
        self.wy = wy
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.image = image

    def update(self, dt):
        """Advance particle physics. dt is in real seconds."""
        self.vx *= AIR_DRAG
        self.vy -= GRAVITY * dt  # world Y increases upward
        self.wx += self.vx * dt
        self.wy += self.vy * dt
        self.life -= dt

    def render(self, screen, camera_x, camera_y, block_size, cx_off, cy_off):
        """Draw the particle on screen with fade-out based on remaining life."""
        sx = int((self.wx - camera_x) * block_size + cx_off)
        sy = int((camera_y - self.wy) * block_size + cy_off)
        alpha = max(0, int(255 * (self.life / self.max_life)))
        if alpha <= 0:
            return
        frame = self.image.copy()
        frame.set_alpha(alpha)
        half = frame.get_width() // 2
        screen.blit(frame, (sx - half, sy - half))


class ParticleSystem:
    """Manages all active particles."""

    def __init__(self):
        self.particles = []

    def spawn(self, wx, wy, block_type, textures):
        """
        Spawn break particles for a block at world (wx, wy).
        Particles are tiny cutouts of the block texture.
        textures: dict of block_type -> pygame.Surface (raw texture).
        """
        tex = textures.get(block_type)
        for _ in range(PARTICLE_COUNT):
            img = self._sample_texture(tex, block_type)
            if img is None:
                continue
            # Random velocity: x spreads horizontally, y is up-biased (explosion look)
            vx = random.uniform(-3.0, 3.0)
            vy = random.uniform(0.5, 6.5)
            life = PARTICLE_LIFE * random.uniform(0.6, 1.2)
            self.particles.append(Particle(wx + 0.5, wy + 0.5, vx, vy, life, img))

    def _sample_texture(self, tex, block_type):
        """Create a small particle image by cutting out a piece of the texture."""
        if tex is None:
            # Fallback: a colored square based on a simple hash of the block name
            h = sum(ord(c) for c in block_type)
            color = ((h * 37) % 255, (h * 73) % 255, (h * 131) % 255)
            surf = pygame.Surface((8, 8))
            surf.fill(color)
            return pygame.transform.scale(surf, (6, 6))
        w, h = tex.get_size()
        size = max(2, min(w, h) // 4)
        px = random.randint(0, w - size)
        py = random.randint(0, h - size)
        try:
            sub = tex.subsurface((px, py, size, size)).copy()
        except Exception:
            return pygame.transform.scale(tex, (6, 6))
        return pygame.transform.scale(sub, (6, 6))

    def update(self, dt):
        """Advance all particles. dt is normalized (60fps = 1.0)."""
        dt_sec = dt / 60.0
        alive = []
        for p in self.particles:
            p.update(dt_sec)
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def render(self, screen, camera_x, camera_y, block_size):
        """Render all particles."""
        cx_off = screen.get_width() // 2
        cy_off = screen.get_height() // 2
        for p in self.particles:
            p.render(screen, camera_x, camera_y, block_size, cx_off, cy_off)