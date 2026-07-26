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
DEFAULT_BLOCK_SIZE = 32  # pixels per block (default = max zoom out)
MIN_BLOCK_SIZE = 32      # cannot zoom out further than default
FPS = 60
VIEW_DISTANCE_CHUNKS = 8  # chunks loaded in each direction

# Colors (fallback if texture missing)
COLOR_MAP = {
    GRASS: (87, 171, 60),
    DIRT: (130, 96, 52),
    STONE: (120, 120, 120),
    BEDROCK: (50, 50, 50),
}

# Zoom limits
ZOOM_FACTOR = 1.15


def load_textures(tex_dir: str = "image/block") -> dict:
    """Load all block textures at original size from the image directory."""
    textures = {}
    if not os.path.isdir(tex_dir):
        print(f"Warning: texture directory '{tex_dir}' not found")
        return textures

    for fname in os.listdir(tex_dir):
        if fname.endswith(".png"):
            path = os.path.join(tex_dir, fname)
            try:
                img = pygame.image.load(path).convert_alpha()
                key = fname.rsplit(".", 1)[0]
                textures[key] = img
                print(f"  Loaded texture: {key} ({img.get_width()}x{img.get_height()})")
            except Exception as e:
                print(f"  Failed to load {path}: {e}")

    return textures


def get_texture_or_fallback(textures: dict, block_type: str,
                            block_size: int) -> pygame.Surface:
    """Get a texture scaled to block_size, or create a colored fallback."""
    if block_type in textures:
        raw = textures[block_type]
        return pygame.transform.scale(raw, (block_size, block_size))

    # Create a fallback colored surface
    color = COLOR_MAP.get(block_type, (200, 0, 200))  # magenta for unknown
    surf = pygame.Surface((block_size, block_size))
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

    # Zoom state
    block_size = DEFAULT_BLOCK_SIZE

    # Camera pan (right mouse drag)
    camera_offset_x = 0.0
    camera_offset_y = 0.0
    is_rmb_dragging = False
    rmb_drag_start_mouse = (0, 0)   # screen coords
    rmb_drag_start_offset = (0.0, 0.0)  # world coords

    running = True
    show_debug = True

    while running:
        dt = clock.tick(FPS) / 16.667  # normalize to ~60 FPS
        keys = pygame.key.get_pressed()
        mouse_buttons = pygame.mouse.get_pressed()

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE and not is_fullscreen:
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

            elif event.type == pygame.MOUSEWHEEL:
                # Zoom in/out
                if event.y > 0:
                    new_size = block_size * ZOOM_FACTOR
                    # Max zoom in: clamp so at least 2 blocks visible in the shorter dimension
                    max_bs = max(min(screen_width, screen_height) / 2, DEFAULT_BLOCK_SIZE)
                    if new_size <= max_bs:
                        block_size = int(new_size)
                elif event.y < 0:
                    new_size = block_size / ZOOM_FACTOR
                    if new_size >= MIN_BLOCK_SIZE:
                        block_size = max(int(new_size), MIN_BLOCK_SIZE)

        # --- Right mouse button drag to pan camera ---
        if mouse_buttons[2]:  # right button pressed
            if not is_rmb_dragging:
                # Start drag
                is_rmb_dragging = True
                rmb_drag_start_mouse = pygame.mouse.get_pos()
                rmb_drag_start_offset = (camera_offset_x, camera_offset_y)
            else:
                # Continue drag
                mx, my = pygame.mouse.get_pos()
                sx0, sy0 = rmb_drag_start_mouse
                dx_px = mx - sx0
                dy_px = my - sy0
                # Convert screen pixel delta to world coordinate delta
                # Note: Y is inverted (screen down = world down)
                camera_offset_x = rmb_drag_start_offset[0] - dx_px / block_size
                camera_offset_y = rmb_drag_start_offset[1] + dy_px / block_size
        else:
            if is_rmb_dragging:
                # End drag - keep current offset, just stop dragging
                is_rmb_dragging = False

        # Update player
        player.update(keys, dt)
        px, py = player.get_pos()

        # Update world view based on player/camera position
        adjusted_cam_x = px + camera_offset_x
        world.update_view(adjusted_cam_x)

        # Camera follows player with offset
        camera_x = adjusted_cam_x
        camera_y = py + camera_offset_y

        # --- RENDER ---
        screen.fill((135, 206, 235))  # sky blue

        # Render blocks
        def draw_block(sx, sy, block_type):
            tex = get_texture_or_fallback(textures, block_type, block_size)
            screen.blit(tex, (sx, sy))

        world.render_blocks(
            camera_x, camera_y,
            screen_width, screen_height,
            block_size,
            draw_block
        )

        # Debug info
        if show_debug:
            zoom_pct = int(block_size / DEFAULT_BLOCK_SIZE * 100)
            lines = [
                f"My2DWorld - FPS: {clock.get_fps():.0f}",
                f"Player: ({px:.1f}, {py:.1f})",
                f"Camera: ({camera_x:.1f}, {camera_y:.1f})",
                f"Block size: {block_size}px ({zoom_pct}%)",
                f"Window: {screen_width}x{screen_height}" +
                (" (FS)" if is_fullscreen else ""),
                f"Chunks loaded: {len(world.chunks)}",
                f"Textures loaded: {len(textures)}",
                "WASD: Move | Scroll: Zoom | RMB: Pan | F3: Debug | F11: FS | ESC: Exit",
            ]
            for i, line in enumerate(lines):
                text_surf = font.render(line, True, (255, 255, 255))
                shadow = font.render(line, True, (0, 0, 0))
                screen.blit(shadow, (11, 11 + i * 18))
                screen.blit(text_surf, (10, 10 + i * 18))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()