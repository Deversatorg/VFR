"""
VFR.AiEngine — Garment Texture Generation Pipeline
Takes a 2D clothing photo, removes the background, processes it into a
clean texture, and applies it to a base 3D GLB primitive.
"""

import io
import os
import base64
import uuid
import logging
import tempfile

from PIL import Image

logger = logging.getLogger(__name__)

# Map primitive_type strings to base GLB filenames in the models/primitives/ folder
PRIMITIVE_MAP = {
    "tshirt": "base_tshirt.glb",
    "hoodie": "base_hoodie.glb",
    "pants":  "base_pants.glb",
    "jacket": "base_jacket.glb",
}

# ---------------------------------------------------------------------------
# Optional heavy imports — guarded so the module can still be imported even
# when rembg / pygltflib are not installed (e.g. in unit-test environments).
# ---------------------------------------------------------------------------
try:
    from rembg import remove as rembg_remove
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False
    logger.warning("rembg not installed — background removal will be skipped (mock mode).")

try:
    from pygltflib import GLTF2, BufferView, Buffer, Image as GltfImage
    HAS_PYGLTFLIB = True
except ImportError:
    HAS_PYGLTFLIB = False
    logger.warning("pygltflib not installed — GLB injection will be skipped (mock mode).")


def _make_minimal_glb() -> bytes:
    """Return a valid, minimal GLB binary (12-byte header only) for testing."""
    # A minimal GLB: magic(4) + version(4) + length(4) = 12 bytes
    import struct
    magic = b'glTF'
    version = struct.pack('<I', 2)
    length = struct.pack('<I', 12)
    return magic + version + length


class GarmentMLPipeline:
    """
    Two-step pipeline:
      1. Process a 2D garment image into a clean 1024×1024 PNG texture.
      2. Inject that texture into a base GLB primitive and return the path.
    """

    CANVAS_SIZE = 1024  # Final texture resolution

    def _process_image_texture(self, image_bytes: bytes) -> bytes:
        """
        Step 1: Remove background with rembg, crop tightly, centre on a
        transparent 1024×1024 canvas and return PNG bytes.

        Falls back to a plain resize+centre if rembg is unavailable.
        """
        logger.info("Garment pipeline: processing image texture...")

        if HAS_REMBG:
            logger.info("Garment pipeline: removing background with rembg...")
            removed_bg: bytes = rembg_remove(image_bytes)
            img = Image.open(io.BytesIO(removed_bg)).convert("RGBA")
        else:
            logger.warning("Garment pipeline: rembg unavailable — skipping background removal.")
            img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")

        # Tight crop: remove fully-transparent border rows/cols
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)

        # Resize proportionally so the longest side == canvas size, with 10% padding
        padded = int(self.CANVAS_SIZE * 0.9)
        img.thumbnail((padded, padded), Image.LANCZOS)

        # Centre on transparent canvas
        canvas = Image.new("RGBA", (self.CANVAS_SIZE, self.CANVAS_SIZE), (0, 0, 0, 0))
        offset_x = (self.CANVAS_SIZE - img.width) // 2
        offset_y = (self.CANVAS_SIZE - img.height) // 2
        canvas.paste(img, (offset_x, offset_y), mask=img)

        # Export as PNG bytes
        buf = io.BytesIO()
        canvas.save(buf, format="PNG")
        buf.seek(0)
        result = buf.getvalue()
        logger.info("Garment pipeline: texture processed (%d bytes).", len(result))
        return result

    def apply_texture_to_primitive(self, primitive_type: str, image_bytes: bytes) -> str:
        """
        Step 2: Load the base GLB for the given primitive type, replace its
        first image buffer with our processed texture, and save to the system
        temp directory.

        Returns the absolute path to the modified GLB file.
        """
        glb_filename = PRIMITIVE_MAP.get(primitive_type.lower())
        if not glb_filename:
            raise ValueError(
                f"Unknown primitive_type '{primitive_type}'. "
                f"Valid options: {list(PRIMITIVE_MAP.keys())}"
            )

        primitives_dir = os.path.join(os.path.dirname(__file__), "models", "primitives")
        primitive_path = os.path.join(primitives_dir, glb_filename)

        # Build a cross-platform temp output path
        tmp_dir = tempfile.gettempdir()
        output_path = os.path.join(tmp_dir, f"garment_{uuid.uuid4().hex}.glb")

        # --- Step 1: Process the raw garment photo into a clean PNG texture ---
        texture_bytes: bytes = self._process_image_texture(image_bytes)

        # --- Step 2: Inject the texture into the GLTF binary blob ---
        if not HAS_PYGLTFLIB:
            logger.warning("pygltflib unavailable — writing minimal mock GLB.")
            with open(output_path, "wb") as f:
                f.write(_make_minimal_glb())
            return output_path

        if not os.path.exists(primitive_path):
            logger.warning(
                "Base primitive GLB not found at '%s'. Writing mock GLB.", primitive_path
            )
            with open(output_path, "wb") as f:
                f.write(_make_minimal_glb())
            return output_path

        logger.info("Garment pipeline: loading primitive GLB from %s", primitive_path)
        gltf = GLTF2().load(primitive_path)

        texture_length = len(texture_bytes)
        new_buffer_index = len(gltf.buffers)
        new_bufferview_index = len(gltf.bufferViews)

        # Encode texture as a data URI so pygltflib embeds it in the GLB without
        # relying on external filesystem references.
        data_uri = "data:image/png;base64," + base64.b64encode(texture_bytes).decode("utf-8")

        new_buffer = Buffer(uri=data_uri, byteLength=texture_length)
        gltf.buffers.append(new_buffer)

        # Add a BufferView pointing to the entire new buffer
        new_bufferview = BufferView(
            buffer=new_buffer_index,
            byteOffset=0,
            byteLength=texture_length,
        )
        gltf.bufferViews.append(new_bufferview)

        # Ensure there is at least one image in the GLTF; if the primitive has
        # none (e.g. a plain geometry GLB), add a placeholder.
        if not gltf.images:
            gltf.images.append(GltfImage())

        # STRICT GLB MODIFICATION RULE per spec:
        #   a. New Buffer + BufferView already appended above.
        #   b. Remove the existing URI (if any) from images[0].
        #   c. Point images[0].bufferView to our new BufferView index.
        #   d. Set mimeType to "image/png".
        gltf.images[0].uri = None          # (b) bufferView takes priority
        gltf.images[0].bufferView = new_bufferview_index  # (c)
        gltf.images[0].mimeType = "image/png"              # (d)

        # --- Step 3: Save the modified GLTF to a temp file ---
        gltf.save(output_path)

        logger.info("Garment pipeline: saved textured GLB to %s", output_path)
        return output_path
