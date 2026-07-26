"""
My2DWorld - A 2D Minecraft-style infinite terrain explorer.
Uses pygame for rendering and hand-crafted noise for terrain generation.
"""

import os
import sys
import pygame

from world import World, GRASS, DIRT, STONE, BEDROCK
from player import Player

# Constants
INITIAL_WIDTH = 1024
INITIAL_HEIGHT = 768
BLOCK_SIZE = 32  # pixels per block
FPS = 60
VIEW_DISTANCE_CHUNKS = 8  # chunks loaded in each direction

# Colors (fallback if texture missing)
COLOR_MAP = {
    GRASS: (87, 171, 60),
    DIRT: (130, 96, 52),
    STONE: (120, 120, 120),
    BEDROCK: (50, 50, 50),
}


def load_textures() -> dict:
    """Load all block textures from image/block/ directory."""
    textures = {}
    tex_dir = os.path.join("image", "block")
    if not os.path.isdir(tex_dir):
        print(f"Warning: texture directory '{tex_dir}' not found")
        return textures

    for fname in os.listdir(tex_dir):
        if fname.endswith(".png"):
            path = os.path.join(tex_dir, fname)
            try:
                # Load and scale to BLOCK_SIZE
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.scale(img, (BLOCK_SIZE, BLOCK_SIZE))
                # Use filename without extension as key
                key = fname.rsplit(".", 1)[0]
                textures[key] = img
                print(f"  Loaded texture: {key}")
            except Exception as e:
                print(f"  Failed to load {path}: {e}")

    return textures


def get_texture_or_fallback(textures: dict, block_type: str) -> pygame.Surface:
    """Get a texture surface, or create a colored fallback if missing."""
    if block_type in textures:
        return textures[block_type]

    # Create a fallback colored surface
    color = COLOR_MAP.get(block_type, (200, 0, 200))  # magenta for unknown
    surf = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE))
    surf.fill(color)
    # Draw a border to distinguish blocks
    pygame.draw.rect(surf, (0, 0, 0), surf.get_rect(), 1)
    return surf


def main():
    """Main game entry point."""
    pygame.init()
    screen_width = INITIAL_WIDTH
    screen_height = INITIAL_HEIGHT
    is_fullscreen = False

    screen = pygame.display.set_mode(
        (screen_width, screen_height),
        pygame.RESIZABLE
    )
    pygame.display.set_caption("My2DWorld - Infinite Terrain Explorer")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 14)

    # Load textures
    print("Loading textures...")
    textures = load_textures()
    print(f"Loaded {len(textures)} textures")

    # Create world and player
    world = World(view_distance_chunks=VIEW_DISTANCE_CHUNKS)
    start_surface = world.get_surface_height(0)
    player = Player(start_x=0, start_y=start_surface + 3)

    # Initial view update based on player start position
    world.update_view(player.x)

    running = True
    show_debug = True

    while running:
        dt = clock.tick(FPS) / 16.667  # normalize to ~60 FPS
        keys = pygame.key.get_pressed()

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE and not is_fullscreen:
                # Window resized by user dragging
                screen_width, screen_height = event.w, event.h
                screen = pygame.display.set_mode(
                    (screen_width, screen_height),
                    pygame.RESIZABLE
                )
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F3:
                    show_debug = not show_debug
                elif event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F11:
                    # Toggle fullscreen
                    is_fullscreen = not is_fullscreen
                    if is_fullscreen:
                        screen = pygame.display.set_mode(
                            (0, 0),
                            pygame.FULLSCREEN
                        )
                        screen_width, screen_height = screen.get_size()
                    else:
                        screen_width = INITIAL_WIDTH
                        screen_height = INITIAL_HEIGHT
                        screen = pygame.display.set_mode(
                            (screen_width, screen_height),
                            pygame.RESIZABLE
                        )

        # Update player
        player.update(keys, dt)
        px, py = player.get_pos()

        # Update world view based on player/camera position
        world.update_view(px)

        # Camera follows player
        camera_x = px
        camera_y = py

        # --- RENDER ---
        screen.fill((135, 206, 235))  # sky blue

        # Render blocks using world.render_blocks with a draw callback
        def draw_block(sx, sy, block_type):
            """Draw a single block at screen coordinates."""
            tex = get_texture_or_fallback(textures, block_type)
            screen.blit(tex, (sx, sy))

        world.render_blocks(
            camera_x, camera_y,
            screen_width, screen_height,
            BLOCK_SIZE,
            draw_block
        )

        # Debug info
        if show_debug:
            lines = [
                f"My2DWorld - FPS: {clock.get_fps():.0f}",
                f"Player: ({px:.1f}, {py:.1f})",
                f"Camera: ({camera_x:.1f}, {camera_y:.1f})",
                f"Window: {screen_width}x{screen_height}" +
                (" (FS)" if is_fullscreen else ""),
                f"Chunks loaded: {len(world.chunks)}",
                f"Textures loaded: {len(textures)}",
                "WASD/Arrows: Move | F3: Debug | F11: Fullscreen | ESC: Exit",
            ]
            for i, line in enumerate(lines):
                text_surf = font.render(line, True, (255, 255, 255))
                # Draw shadow for readability
                shadow = font.render(line, True, (0, 0, 0))
                screen.blit(shadow, (11, 11 + i * 18))
                screen.blit(text_surf, (10, 10 + i * 18))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()