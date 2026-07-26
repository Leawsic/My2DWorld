"""
Infinite 2D world generation system.
Terrain is generated using multi-octave sine noise (no external dependencies).
Chunk-based loading/unloading for infinite world support.
"""

import math

# Block types (matching texture filenames)
GRASS = "grass_block_side"
DIRT = "dirt"
STONE = "iron_block"
BEDROCK = "bedrock"

# Chunk size in blocks (columns per chunk)
CHUNK_SIZE = 16

# Terrain heights (how many layers from surface down)
GRASS_DEPTH = 3
DIRT_DEPTH = 12
BEDROCK_THICKNESS = 2


def hash_noise(x: int) -> float:
    """Simple hash-based pseudo-random noise for a given integer x."""
    h = x * 374761393 + 668265263
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return (h & 0x7FFFFFFF) / 0x7FFFFFFF  # return 0..1


def smooth_noise(x: float) -> float:
    """Value noise with cosine interpolation between integer points."""
    ix = math.floor(x)
    fx = x - ix
    # smoothstep interpolation
    fx = fx * fx * (3 - 2 * fx)
    n0 = hash_noise(ix)
    n1 = hash_noise(ix + 1)
    return n0 + (n1 - n0) * fx


def terrain_height(x: int) -> int:
    """
    Generate surface height at world column x using multi-octave sine noise.
    Returns the Y level of the surface (highest solid block).
    World Y increases upward.
    """
    # Multi-octave sine-based noise for large-scale terrain
    octaves = [
        (0.005, 30.0),   # low freq, large amplitude → mountains/hills
        (0.02, 15.0),    # mid freq
        (0.05, 6.0),     # high freq → small bumps
    ]
    y = 0.0
    for freq, amp in octaves:
        y += math.sin(x * freq + math.pi * hash_noise(int(x * freq * 100))) * amp

    # Use value noise for more organic variation
    noise_val = smooth_noise(x * 0.01) * 20 + smooth_noise(x * 0.03) * 8

    y += noise_val
    y += 40  # base height (offset)

    return max(1, int(round(y)))


def get_block_type(x: int, y: int, surface_y: int):
    """Determine the block type at a given (x, y) world coordinate.
    y=1 is the bottom of the world (bedrock).
    surface_y is the topmost grass block.
    """
    if y <= 0:
        return None  # void
    if y <= BEDROCK_THICKNESS:
        return BEDROCK
    if y == surface_y:
        return GRASS
    if y > surface_y - GRASS_DEPTH:
        return GRASS
    if y > surface_y - GRASS_DEPTH - DIRT_DEPTH:
        return DIRT
    return STONE


class Chunk:
    """A column-based chunk that stores block data for a range of x columns."""

    def __init__(self, chunk_x: int):
        self.chunk_x = chunk_x
        self.x_start = chunk_x * CHUNK_SIZE
        self.x_end = self.x_start + CHUNK_SIZE
        # Pre-compute surface heights and block types for this chunk
        self._generate()

    def _generate(self):
        """Generate all block data for this chunk."""
        self._surface_heights = {}
        self._blocks = {}  # (x, y) -> block_type

        for wx in range(self.x_start, self.x_end):
            sy = terrain_height(wx)
            self._surface_heights[wx] = sy
            # Generate from top (y = sy) down to y = 1
            for wy in range(sy, 0, -1):
                bt = get_block_type(wx, wy, sy)
                if bt:
                    self._blocks[(wx, wy)] = bt

    def get_block(self, x: int, y: int):
        """Get block type at local (x, y), or None if air/void."""
        return self._blocks.get((x, y), None)

    def get_surface_height(self, x: int) -> int:
        """Get surface height at column x."""
        return self._surface_heights.get(x, 0)

    def get_all_blocks_in_rect(self, x_start: int, x_end: int, y_start: int, y_end: int):
        """
        Iterate over all blocks in the given rect area.
        Yields (x, y, block_type).
        """
        for wx in range(max(x_start, self.x_start), min(x_end, self.x_end)):
            for wy in range(y_start, y_end + 1):
                bt = self._blocks.get((wx, wy))
                if bt:
                    yield wx, wy, bt


class World:
    """Infinite world manager with chunk-based loading/unloading."""

    def __init__(self, view_distance_chunks: int = 8):
        self.view_distance = view_distance_chunks
        self.chunks: dict[int, Chunk] = {}
        self.last_center_chunk = None

    def _get_chunk_x(self, world_x: float) -> int:
        """Get the chunk index for a world x coordinate."""
        return math.floor(world_x / CHUNK_SIZE)

    def _load_chunk(self, chunk_x: int):
        """Load a chunk if not already loaded."""
        if chunk_x not in self.chunks:
            self.chunks[chunk_x] = Chunk(chunk_x)

    def _unload_distant_chunks(self, center_chunk: int):
        """Unload chunks that are too far from the center."""
        to_remove = []
        for cx in self.chunks:
            if abs(cx - center_chunk) > self.view_distance + 2:
                to_remove.append(cx)
        for cx in to_remove:
            del self.chunks[cx]

    def update_view(self, camera_x: float):
        """Update loaded chunks based on camera x position."""
        center_chunk = self._get_chunk_x(camera_x)
        if center_chunk == self.last_center_chunk:
            return

        self.last_center_chunk = center_chunk
        # Load chunks in view
        for dx in range(-self.view_distance, self.view_distance + 1):
            self._load_chunk(center_chunk + dx)

        # Unload distant chunks
        self._unload_distant_chunks(center_chunk)

    def get_block(self, x: int, y: int):
        """Get block type at any world coordinate."""
        cx = self._get_chunk_x(x)
        chunk = self.chunks.get(cx)
        if chunk is None:
            return None
        return chunk.get_block(x, y)

    def get_surface_height(self, x: int) -> int:
        """Get surface height at world column x."""
        cx = self._get_chunk_x(x)
        chunk = self.chunks.get(cx)
        if chunk is None:
            return terrain_height(x)
        return chunk.get_surface_height(x)

    def render_blocks(self, camera_x: float, camera_y: float,
                      screen_width: int, screen_height: int, block_size: int,
                      draw_func):
        """
        Render all visible blocks.
        camera_x, camera_y = world coordinates at screen center.
        draw_func(x_screen, y_screen, block_type) is called for each visible block.
        """
        # Calculate visible world coordinate range (with margins)
        half_w = screen_width / (2.0 * block_size)
        half_h = screen_height / (2.0 * block_size)

        world_left = camera_x - half_w - 1
        world_right = camera_x + half_w + 1
        # World Y increases upward. Screen Y increases downward.
        # Higher world Y → lower screen Y (top of screen)
        world_top = camera_y + half_h + 1      # highest world Y visible
        world_bottom = camera_y - half_h - 1   # lowest world Y visible

        # Round to integer block coordinates
        wx_start = max(0, int(math.floor(world_left)))
        wx_end = int(math.ceil(world_right))
        wy_bottom = max(1, int(math.floor(world_bottom)))
        wy_top = int(math.ceil(world_top))

        # Screen center offset
        cx_off = screen_width // 2
        cy_off = screen_height // 2

        # Iterate over all loaded chunks
        for chunk in list(self.chunks.values()):
            # Check if this chunk is in visible x range
            if chunk.x_end <= wx_start or chunk.x_start >= wx_end:
                continue

            # Calculate visible x range within this chunk
            cx_start = max(wx_start, chunk.x_start)
            cx_end = min(wx_end, chunk.x_end)

            for wx in range(cx_start, cx_end):
                sy = chunk.get_surface_height(wx)
                if sy == 0:
                    continue

                # Visible y range: from world_bottom up to world_top,
                # clamped to actual block range (1 to sy)
                y_end = min(wy_top, sy)
                y_start = max(wy_bottom, 1)

                for wy in range(y_start, y_end + 1):
                    bt = chunk.get_block(wx, wy)
                    if bt:
                        # Convert world coords to screen coords
                        # sx = (wx - camera_x) * block_size + screen_width // 2
                        # sy_px = (camera_y - wy) * block_size + screen_height // 2
                        sx = (wx - camera_x) * block_size + cx_off
                        sy_px = (camera_y - wy) * block_size + cy_off

                        # Only draw if on screen (with margin)
                        if (-block_size <= sx <= screen_width and
                                -block_size <= sy_px <= screen_height):
                            draw_func(sx, sy_px, bt)