import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

export type HeadPose = "neutral" | "smile" | "blink" | "speak";
type ReferenceFit = { pitch: number; yaw: number; roll: number; size: number; target_x: number; target_y: number };

/** Isolated art viewer. No workspace, microphone, provider or audio subscriptions. */
export class HeadRenderer {
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.OrthographicCamera(-0.25, 0.25, 0.25, -0.25, 0.1, 10);
  private controls: OrbitControls;
  private observer: ResizeObserver;
  private abort = new AbortController();
  private model: THREE.Group | null = null;
  private headPose: THREE.Object3D | null = null;
  private fit: ReferenceFit | null = null;
  private referenceMode = false;
  private neck: THREE.BufferGeometry | null = null;
  private neckRest: Float32Array | null = null;
  private morphs: THREE.Mesh[] = [];
  private shaders: THREE.WebGLProgramParametersWithUniforms[] = [];
  private disposed = false;
  private frame = 0;
  private last = 0;
  private elapsed = 0;
  private pose: HeadPose = "neutral";
  private blinkStart = -10;
  private paused = matchMedia("(prefers-reduced-motion: reduce)").matches;

  constructor(
    private host: HTMLDivElement,
    private ready: () => void,
    private failed: () => void,
  ) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "low-power" });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.NoToneMapping;
    this.renderer.setClearColor(0xf0efed);
    this.renderer.domElement.setAttribute("aria-hidden", "true");
    host.append(this.renderer.domElement);
    this.renderer.domElement.addEventListener("webglcontextlost", this.lost);
    this.camera.position.set(0, 0.085, 2);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.target.set(0, 0.085, 0);
    this.controls.enablePan = false;
    this.controls.minZoom = 0.7;
    this.controls.maxZoom = 2.5;
    this.controls.addEventListener("change", this.schedule);
    this.controls.update();
    this.observer = new ResizeObserver(this.resize);
    this.observer.observe(host);
    document.addEventListener("visibilitychange", this.schedule);
    void this.load();
  }

  private lost = (event: Event) => {
    event.preventDefault();
    this.dispose();
    this.failed();
  };

  private disposeRoot(root: THREE.Object3D) {
    const geometries = new Set<THREE.BufferGeometry>();
    const materials = new Set<THREE.Material>();
    const textures = new Set<THREE.Texture>();
    root.traverse((object) => {
      if (!(object instanceof THREE.Mesh)) return;
      geometries.add(object.geometry);
      for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
        materials.add(material);
        for (const value of Object.values(material)) if (value instanceof THREE.Texture) textures.add(value);
      }
    });
    geometries.forEach((geometry) => geometry.dispose());
    materials.forEach((material) => material.dispose());
    textures.forEach((texture) => texture.dispose());
  }

  private toon(source: THREE.Material) {
    const original = source as THREE.MeshStandardMaterial;
    const face = original.name === "A1_FacePaint";
    const hair = original.name === "A1_SilverAsh_PaintedHair";
    const metal = original.name === "A1_SatinSilver";
    const material = new THREE.MeshBasicMaterial({
      name: original.name,
      color: original.color?.clone() ?? new THREE.Color(0xffffff),
      map: original.map ?? null,
      side: THREE.DoubleSide,
      alphaTest: hair ? 0.4 : 0,
      depthWrite: true,
    });
    material.onBeforeCompile = (shader) => {
      shader.uniforms.uA1Key = { value: new THREE.Vector3(-0.8, 1.2, 2).normalize() };
      shader.uniforms.uA1Shade = { value: new THREE.Vector3(...(hair ? [0.70, 0.70, 0.80] as const : [0.82, 0.80, 0.88] as const)) };
      shader.uniforms.uA1Blink = { value: 0 };
      shader.vertexShader = shader.vertexShader
        .replace("#include <common>", "#include <common>\nvarying vec3 vA1Normal;\nvarying vec3 vA1Rest;\nvarying vec3 vA1Surface;")
        .replace("#include <begin_vertex>", `
          {
            vec3 objectNormal = vec3(normal);
            #include <morphnormal_vertex>
            vA1Normal = normalize(normalMatrix * objectNormal);
            vA1Rest = position;
          }
          #include <begin_vertex>
        `)
        .replace("#include <morphtarget_vertex>", "#include <morphtarget_vertex>\nvA1Surface = transformed;");
      shader.fragmentShader = shader.fragmentShader
        .replace("#include <common>", "#include <common>\nvarying vec3 vA1Normal;\nvarying vec3 vA1Rest;\nvarying vec3 vA1Surface;\nuniform vec3 uA1Key;\nuniform vec3 uA1Shade;\nuniform float uA1Blink;")
        .replace("#include <color_fragment>", `
          #include <color_fragment>
          ${face ? `
            diffuseColor.rgb = mix(vec3(0.91, 0.745, 0.68), diffuseColor.rgb, diffuseColor.a);
            diffuseColor.a = 1.0;
            // The inherited blink closes the geometry, but stretches the open-eye
            // ink over the lid. Fade that ink and draw a thin closed-lid stroke.
            float a1EyeDx = min(abs(vA1Rest.x - 0.0376), abs(vA1Rest.x + 0.0376));
            float a1LidMask = (1.0 - smoothstep(0.028, 0.033, a1EyeDx))
              * smoothstep(0.069, 0.078, vA1Rest.y) * (1.0 - smoothstep(0.111, 0.119, vA1Rest.y));
            float a1Closed = smoothstep(0.25, 0.9, uA1Blink);
            diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.915, 0.775, 0.725), a1LidMask * a1Closed);
            float a1LidY = 0.089 + 0.006 * pow(a1EyeDx / 0.026, 2.0);
            float a1LidInk = (1.0 - smoothstep(0.0003, 0.0011, abs(vA1Surface.y - a1LidY)))
              * (1.0 - smoothstep(0.024, 0.028, a1EyeDx));
            diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.055, 0.048, 0.063), a1LidInk * a1Closed * a1LidMask);
          ` : ""}
          vec3 a1Normal = normalize(vA1Normal) * (gl_FrontFacing ? 1.0 : -1.0);
          float a1Band = smoothstep(-0.35, 0.75, dot(a1Normal, uA1Key));
          diffuseColor.rgb *= mix(uA1Shade, vec3(1.0), a1Band);
          ${metal ? "diffuseColor.rgb = mix(diffuseColor.rgb * vec3(1.06, 1.02, 0.94), vec3(0.95, 0.93, 0.87), pow(max(0.0, dot(a1Normal, normalize(uA1Key + vec3(0.0, 0.0, 1.0)))), 22.0) * 0.75);" : ""}
        `);
      this.shaders.push(shader);
    };
    material.customProgramCacheKey = () => `a1-head-toon-lid2-${face}-${hair}-${metal}`;
    return material;
  }

  private faceOutline(mesh: THREE.Mesh) {
    const material = new THREE.MeshBasicMaterial({ name: "A1_FaceInk", color: 0x514653, side: THREE.BackSide, transparent: true, depthWrite: false });
    material.onBeforeCompile = (shader) => {
      shader.vertexShader = shader.vertexShader
        .replace("#include <common>", "#include <common>\nvarying float vA1JawHeight;")
        .replace("#include <morphtarget_vertex>", "#include <morphtarget_vertex>\nvA1JawHeight = transformed.y;\ntransformed += normalize(normal) * 0.0005;");
      // Only the lower jaw needs silhouette ink; outlining the inherited ear
      // folds produced distracting internal lines across the cheek.
      shader.fragmentShader = shader.fragmentShader
        .replace("#include <common>", "#include <common>\nvarying float vA1JawHeight;")
        .replace("#include <color_fragment>", "#include <color_fragment>\ndiffuseColor.a *= 1.0 - smoothstep(0.015, 0.04, vA1JawHeight);");
    };
    material.customProgramCacheKey = () => "a1-lower-jaw-ink-0.0005";
    const outline = new THREE.Mesh(mesh.geometry, material);
    outline.name = "A1_FaceInk";
    outline.morphTargetInfluences = mesh.morphTargetInfluences;
    outline.morphTargetDictionary = mesh.morphTargetDictionary;
    mesh.add(outline);
  }

  private async load() {
    let loaded: THREE.Group | null = null;
    try {
      const fitPromise = fetch("/companion/a1-reference-fit.json", { signal: this.abort.signal })
        .then((response) => response.ok ? response.json() : null)
        .catch(() => null);
      const response = await fetch("/companion/a1-head-study.glb", { signal: this.abort.signal });
      if (!response.ok || !response.body) throw new Error("HEAD_MODEL_UNAVAILABLE");
      const reader = response.body.getReader();
      const chunks: Uint8Array[] = [];
      let length = 0;
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        length += value.byteLength;
        if (length > 12 * 1024 * 1024) {
          await reader.cancel();
          throw new Error("HEAD_MODEL_TOO_LARGE");
        }
        chunks.push(value);
      }
      if (this.disposed) return;
      const buffer = new Uint8Array(length);
      let offset = 0;
      for (const chunk of chunks) { buffer.set(chunk, offset); offset += chunk.length; }
      const manager = new THREE.LoadingManager();
      let textureFailed = false;
      manager.onError = () => { textureFailed = true; };
      const loader = new GLTFLoader(manager);
      // Same CSP boundary as the resident renderer: img-src blob:, connect-src self.
      loader.register((parser) => {
        parser.textureLoader = new THREE.TextureLoader(manager);
        return { name: "FYP_HEAD_EMBEDDED_IMAGE_LOADER" };
      });
      const gltf = await loader.parseAsync(buffer.buffer, "");
      loaded = gltf.scene;
      if (this.disposed || textureFailed) {
        this.disposeRoot(loaded);
        loaded = null;
        if (textureFailed && !this.disposed) throw new Error("HEAD_TEXTURE_UNAVAILABLE");
        return;
      }
      const originals = new Set<THREE.Material>();
      const converted = new Map<THREE.Material, THREE.Material>();
      const faces: THREE.Mesh[] = [];
      loaded.traverse((object) => {
        if (!(object instanceof THREE.Mesh)) return;
        const convert = (source: THREE.Material) => {
          originals.add(source);
          if (!converted.has(source)) converted.set(source, this.toon(source));
          return converted.get(source)!;
        };
        object.material = Array.isArray(object.material) ? object.material.map(convert) : convert(object.material);
        if (object.morphTargetDictionary) this.morphs.push(object);
        if ((Array.isArray(object.material) ? object.material : [object.material]).some((material) => material.name === "A1_FacePaint")) faces.push(object);
      });
      faces.forEach((mesh) => this.faceOutline(mesh));
      originals.forEach((material) => material.dispose());
      this.model = loaded;
      const fit = await fitPromise;
      if (this.disposed) { this.disposeRoot(loaded); this.model = null; return; }
      if (fit && [fit.pitch, fit.yaw, fit.roll, fit.size, fit.target_x, fit.target_y].every(Number.isFinite) && fit.size > 0.3 && fit.size < 0.7)
        this.fit = fit as ReferenceFit;
      this.headPose = loaded.getObjectByName("A1_HeadPose") ?? null;
      const neck = loaded.getObjectByName("A1_Neck");
      if (neck instanceof THREE.Mesh) {
        this.neck = neck.geometry;
        this.neckRest = new Float32Array(neck.geometry.getAttribute("position").array);
      }
      this.scene.add(loaded);
      this.host.dataset.loaded = "true";
      this.host.dataset.model = "a1-head-study";
      this.resize();
      this.ready();
    } catch (error) {
      if (!this.disposed) {
        if (loaded && loaded !== this.model) this.disposeRoot(loaded);
        this.failed();
      }
    }
  }

  private resize = () => {
    if (this.disposed) return;
    const { width, height } = this.host.getBoundingClientRect();
    if (!width || !height) return;
    const half = this.referenceMode && this.fit ? this.fit.size / 2 : 0.235;
    this.camera.left = -half * width / height;
    this.camera.right = half * width / height;
    this.camera.top = half;
    this.camera.bottom = -half;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height, false);
    this.schedule();
  };

  setPose(pose: HeadPose) {
    this.pose = pose;
    this.blinkStart = this.elapsed;
    this.host.dataset.pose = pose;
    this.schedule();
  }

  setPaused(paused: boolean) { this.paused = paused; this.schedule(); }

  matchReference(active: boolean) {
    this.referenceMode = active && !!this.fit;
    if (this.headPose) {
      const fit = this.fit;
      this.headPose.rotation.set(active && fit ? fit.pitch : 0, active && fit ? fit.yaw : 0, active && fit ? fit.roll : 0, "ZYX");
      this.followNeck();
    }
    if (this.referenceMode && this.fit) {
      const { target_x: x, target_y: y } = this.fit;
      this.camera.position.set(x, y, 2);
      this.controls.target.set(x, y, 0);
      this.camera.zoom = 1;
      this.controls.update();
    }
    this.host.dataset.reference = String(this.referenceMode);
    this.resize();
  }

  setOverlay(active: boolean) { this.controls.enabled = !active; }

  private followNeck() {
    if (!this.neck || !this.neckRest || !this.headPose) return;
    this.headPose.updateMatrix();
    const attribute = this.neck.getAttribute("position");
    const point = new THREE.Vector3(), posed = new THREE.Vector3();
    for (let i = 0; i < attribute.count; i++) {
      point.fromArray(this.neckRest, i * 3);
      const weight = THREE.MathUtils.smoothstep(point.y, -0.02, 0.045);
      posed.copy(point).applyMatrix4(this.headPose.matrix);
      point.lerp(posed, weight);
      attribute.setXYZ(i, point.x, point.y, point.z);
    }
    attribute.needsUpdate = true;
    this.neck.computeVertexNormals();
    this.neck.computeBoundingSphere();
  }

  view(angle: number) {
    this.referenceMode = false;
    this.headPose?.rotation.set(0, 0, 0);
    this.followNeck();
    this.camera.position.set(2 * Math.sin(angle), 0.085, 2 * Math.cos(angle));
    this.controls.target.set(0, 0.085, 0);
    this.controls.update();
    this.resize();
    this.host.dataset.angle = String(angle);
    this.schedule();
  }

  private schedule = () => {
    if (!this.disposed && !document.hidden && !this.frame) this.frame = requestAnimationFrame(this.draw);
  };

  private draw = (at: number) => {
    this.frame = 0;
    if (this.disposed || document.hidden) return;
    if (at - this.last < 1000 / 30) { this.schedule(); return; }
    const delta = this.last ? Math.min((at - this.last) / 1000, 0.1) : 0;
    this.last = at;
    if (!this.paused) this.elapsed += delta;
    const pulse = this.pose === "blink"
      ? Math.exp(-Math.pow((this.elapsed - this.blinkStart - 0.18) / 0.08, 2))
      : Math.exp(-Math.pow(((this.elapsed + 1.4) % 4.8 - 4.4) / 0.08, 2));
    const blink = this.paused ? (this.pose === "blink" ? 1 : 0) : pulse;
    for (const mesh of this.morphs) {
      const dictionary = mesh.morphTargetDictionary!, values = mesh.morphTargetInfluences!;
      values.fill(0);
      const set = (name: string, value: number) => { if (dictionary[name] !== undefined) values[dictionary[name]] = value; };
      set("blink", blink);
      set("A1Smile", this.pose === "smile" ? 0.8 : 0);
      if (this.pose === "speak") {
        set("AE", 0.12 + 0.18 * (0.5 + 0.5 * Math.sin(this.elapsed * 8)));
        set("O", 0.07 * (0.5 + 0.5 * Math.sin(this.elapsed * 5)));
      }
    }
    const light = new THREE.Vector3(-0.8, 1.2, 2).normalize().transformDirection(this.camera.matrixWorldInverse);
    for (const shader of this.shaders) {
      (shader.uniforms.uA1Key.value as THREE.Vector3).copy(light);
      shader.uniforms.uA1Blink.value = blink;
    }
    this.renderer.render(this.scene, this.camera);
    if (!this.paused && this.model) this.schedule();
  };

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    this.abort.abort();
    cancelAnimationFrame(this.frame);
    this.observer.disconnect();
    this.controls.removeEventListener("change", this.schedule);
    this.controls.dispose();
    document.removeEventListener("visibilitychange", this.schedule);
    this.renderer.domElement.removeEventListener("webglcontextlost", this.lost);
    if (this.model) this.disposeRoot(this.model);
    this.renderer.dispose();
    this.renderer.domElement.remove();
    this.shaders.length = 0;
  }
}
