import {
  ClampToEdgeWrapping,
  LinearFilter,
  LinearMipmapLinearFilter,
  LinearMipmapNearestFilter,
  MirroredRepeatWrapping,
  NearestFilter,
  NearestMipmapLinearFilter,
  NearestMipmapNearestFilter,
  RepeatWrapping,
  TextureLoader,
} from "three";
import type { MinificationTextureFilter } from "three";
import type { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

/** Use HTML image loading for embedded bytes. ImageBitmap's fetch(blob:) conflicts with
 * connect-src 'self'; the existing img-src blob: policy already permits these local images. */
export function embeddedTextures(loader: GLTFLoader) {
  loader.register((parser) => ({
    name: "DeskEmbeddedImageTextures",
    async loadTexture(index: number) {
      const definition = parser.json.textures[index];
      const source = parser.json.images[definition.source];
      if (
        !source ||
        source.uri ||
        source.bufferView === undefined ||
        !["image/png", "image/jpeg", "image/webp"].includes(source.mimeType)
      )
        throw new Error("MODEL_TEXTURE");
      const bytes = await parser.getDependency("bufferView", source.bufferView);
      const url = URL.createObjectURL(
        new Blob([bytes], { type: source.mimeType }),
      );
      try {
        const texture = await new TextureLoader(
          parser.options.manager,
        ).loadAsync(url);
        texture.flipY = false;
        const sampler = parser.json.samplers?.[definition.sampler] ?? {};
        const wrap = (value: number) =>
          value === 33071
            ? ClampToEdgeWrapping
            : value === 33648
              ? MirroredRepeatWrapping
              : RepeatWrapping;
        texture.wrapS = wrap(sampler.wrapS);
        texture.wrapT = wrap(sampler.wrapT);
        texture.magFilter =
          sampler.magFilter === 9728 ? NearestFilter : LinearFilter;
        const filters: Record<number, MinificationTextureFilter> = {
          9728: NearestFilter,
          9729: LinearFilter,
          9984: NearestMipmapNearestFilter,
          9985: LinearMipmapNearestFilter,
          9986: NearestMipmapLinearFilter,
          9987: LinearMipmapLinearFilter,
        };
        texture.minFilter =
          filters[sampler.minFilter] ?? LinearMipmapLinearFilter;
        texture.name = source.name ?? `Embedded ${index}`;
        parser.associations.set(texture, { textures: index });
        return texture;
      } finally {
        URL.revokeObjectURL(url);
      }
    },
  }));
  return loader;
}
