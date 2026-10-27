import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { mouthLevel, subscribePlayback } from "./output";
export type ActionName =
  "Idle" | "Wave" | "Turn" | "Walk" | "Stretch" | "Gesture";
export interface Presentation {
  active: boolean;
  action: ActionName;
  nonce: number;
  state: string;
  review: boolean;
  framing?: "full" | "face";
}
function disposeModel(root: THREE.Object3D) {
  const mats = new Set<THREE.Material>(),
    textures = new Set<THREE.Texture>();
  root.traverse((o) => {
    if (o instanceof THREE.Mesh) {
      o.geometry.dispose();
      for (const mat of Array.isArray(o.material) ? o.material : [o.material])
        mats.add(mat);
    }
  });
  for (const mat of mats) {
    for (const value of Object.values(mat))
      if (value instanceof THREE.Texture) textures.add(value);
    mat.dispose();
  }
  for (const tex of textures) {
    const img = tex.source.data;
    if (typeof ImageBitmap !== "undefined" && img instanceof ImageBitmap)
      img.close();
    tex.dispose();
  }
}
export class A1Renderer {
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 30);
  private controls: OrbitControls;
  private abort = new AbortController();
  private disposed = false;
  private model: THREE.Group | null = null;
  private mixer: THREE.AnimationMixer | null = null;
  private actions = new Map<string, THREE.AnimationAction>();
  private current: THREE.AnimationAction | null = null;
  private head: THREE.Bone | null = null;
  private headRest = new THREE.Quaternion();
  private headPose = new THREE.Quaternion();
  private hasGaze = false;
  private morphs: THREE.Mesh[] = [];
  private sample = { level: 0, at: 0 };
  private unsubscribe: () => void;
  private observer: ResizeObserver;
  private intersection: IntersectionObserver;
  private inView = true;
  private frame = 0;
  private last = 0;
  private elapsed = 0;
  private pointer = { x: 0, y: 0 };
  private presentation: Presentation = {
    active: true,
    action: "Idle",
    nonce: 0,
    state: "idle",
    review: false,
  };
  private rendered = 0;
  constructor(
    private host: HTMLDivElement,
    private ready: () => void,
    private failed: () => void,
  ) {
    this.renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: "low-power",
    });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
    this.renderer.setClearColor(0, 0);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.1;
    host.append(this.renderer.domElement);
    this.renderer.domElement.addEventListener(
      "webglcontextlost",
      this.contextLost,
    );
    this.camera.position.set(0, 0.89, 3);
    this.camera.lookAt(0, 0.89, 0);
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0xa3afc7, 2.3));
    const key = new THREE.DirectionalLight(0xfff6ed, 3.1);
    key.position.set(-1.5, 3, 3);
    this.scene.add(key);
    const rim = new THREE.DirectionalLight(0xc5d5ff, 1.1);
    rim.position.set(2, 2, -2);
    this.scene.add(rim);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.target.set(0, 0.89, 0);
    this.controls.enablePan = false;
    this.controls.enableDamping = false;
    this.controls.minZoom = 0.7;
    this.controls.maxZoom = 3;
    this.controls.enabled = false;
    this.controls.addEventListener("change", this.changedView);
    this.observer = new ResizeObserver(this.resize);
    this.observer.observe(host);
    this.intersection = new IntersectionObserver((entries) => {
      this.inView = entries[0]?.isIntersecting ?? true;
      this.restart();
    });
    this.intersection.observe(host);
    document.addEventListener("visibilitychange", this.restart);
    window.addEventListener("pointermove", this.follow, { passive: true });
    this.unsubscribe = subscribePlayback((sample) => {
      this.sample = sample;
      this.schedule();
    });
    void this.load();
  }
  private contextLost = (e: Event) => {
    e.preventDefault();
    this.dispose();
    this.failed();
  };
  private changedView = () => {
    this.host.dataset.view = this.camera.position
      .toArray()
      .map((n) => n.toFixed(2))
      .join(",");
    this.schedule();
  };
  private follow = (e: PointerEvent) => {
    if (e.pointerType !== "mouse") return;
    const b = this.host.getBoundingClientRect();
    this.pointer = {
      x: THREE.MathUtils.clamp(
        (e.clientX - b.left - b.width / 2) / Math.max(b.width, 200),
        -1,
        1,
      ),
      y: THREE.MathUtils.clamp(
        (e.clientY - b.top - b.height * 0.18) / Math.max(b.height, 300),
        -1,
        1,
      ),
    };
  };
  private resize = () => {
    if (this.disposed) return;
    const { width, height } = this.host.getBoundingClientRect();
    if (!width || !height) return;
    const large = ["Wave", "Stretch", "Gesture"].includes(
      this.current?.getClip().name ?? this.presentation.action,
    );
    const half = this.presentation.review
      ? this.presentation.framing === "face"
        ? 0.205
        : 1.04
      : large
        ? 0.96
        : 0.83;
    if (!this.presentation.review) {
      this.camera.position.y = large ? 0.89 : 0.81;
      this.controls.target.y = this.camera.position.y;
      this.camera.lookAt(this.controls.target);
    }
    this.camera.left = (-half * width) / height;
    this.camera.right = (half * width) / height;
    this.camera.top = half;
    this.camera.bottom = -half;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height, false);
    this.schedule();
  };
  private async load() {
    try {
      const response = await fetch("/companion/a1-v3.glb", {
        signal: this.abort.signal,
      });
      if (!response.ok) throw new Error("MODEL_UNAVAILABLE");
      const reader = response.body?.getReader();
      if (!reader) throw new Error("MODEL_UNAVAILABLE");
      const chunks: Uint8Array[] = [];
      let size = 0;
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > 20 * 1024 * 1024) {
          await reader.cancel();
          throw new Error("MODEL_TOO_LARGE");
        }
        chunks.push(value);
      }
      const bytes = new Uint8Array(size);
      let offset = 0;
      for (const c of chunks) {
        bytes.set(c, offset);
        offset += c.length;
      }
      if (this.disposed) return;
      const manager = new THREE.LoadingManager();
      let textureFailed = false;
      manager.onError = () => {
        textureFailed = true;
      };
      const loader = new GLTFLoader(manager);
      // The app permits img-src blob:, while connect-src remains same-origin.
      // HTML images decode embedded GLB textures without a blob fetch.
      loader.register((parser) => {
        parser.textureLoader = new THREE.TextureLoader(manager);
        return { name: "FYP_EMBEDDED_IMAGE_LOADER" };
      });
      const gltf = await loader.parseAsync(bytes.buffer, "");
      if (textureFailed) {
        disposeModel(gltf.scene);
        throw new Error("MODEL_TEXTURE_UNAVAILABLE");
      }
      if (this.disposed) {
        disposeModel(gltf.scene);
        return;
      }
      this.model = gltf.scene;
      this.scene.add(gltf.scene);
      gltf.scene.updateMatrixWorld(true);
      gltf.scene.traverse((o) => {
        if (o instanceof THREE.Mesh && o.morphTargetDictionary)
          this.morphs.push(o);
        if (o.name === "J_Bip_C_Head" && o instanceof THREE.Bone) {
          this.head = o;
          o.getWorldQuaternion(this.headRest);
        }
      });
      this.mixer = new THREE.AnimationMixer(gltf.scene);
      for (const clip of gltf.animations)
        this.actions.set(clip.name, this.mixer.clipAction(clip));
      this.mixer.addEventListener("finished", this.finished);
      this.play(this.presentation.action);
      this.mixer.update(0);
      this.host.dataset.loaded = "true";
      this.host.dataset.clips = [...this.actions.keys()].join(",");
      this.ready();
      this.resize();
      this.schedule();
    } catch (e) {
      if (
        !this.disposed &&
        !(e instanceof DOMException && e.name === "AbortError")
      ) {
        this.dispose();
        this.failed();
      }
    }
  }
  private finished = (event: { action: THREE.AnimationAction }) => {
    if (event.action !== this.current) return;
    this.play("Idle");
    this.host.dataset.action = "Idle";
  };
  private play(name: ActionName) {
    const next = this.actions.get(name) ?? this.actions.get("Idle");
    if (!next) return;
    const prev = this.current;
    next.reset().setEffectiveWeight(1).setEffectiveTimeScale(1);
    next.setLoop(
      name === "Idle" || name === "Walk" ? THREE.LoopRepeat : THREE.LoopOnce,
      Infinity,
    );
    next.clampWhenFinished = name !== "Idle" && name !== "Walk";
    next.play();
    if (prev && prev !== next) {
      prev.fadeOut(0.22);
      next.fadeIn(0.22);
    }
    this.current = next;
    this.host.dataset.action = name;
    this.resize();
  }
  update(next: Presentation) {
    const prior = this.presentation;
    this.presentation = next;
    this.controls.enabled = next.review;
    if (next.review && next.framing !== prior.framing) {
      const direction = this.camera.position
        .clone()
        .sub(this.controls.target)
        .normalize();
      this.controls.target.set(0, next.framing === "face" ? 1.48 : 0.89, 0);
      this.camera.position
        .copy(this.controls.target)
        .addScaledVector(direction, 3);
      this.camera.zoom = 1;
      this.camera.lookAt(this.controls.target);
      this.controls.update();
    }
    this.host.dataset.framing = next.framing ?? "full";
    if (next.nonce !== prior.nonce || next.action !== prior.action)
      this.play(next.action);
    if (!next.active) {
      this.sample = { level: 0, at: 0 };
      this.setMorph("Fcl_MTH_A", 0);
      this.setMorph("Fcl_EYE_Close", 0);
    }
    this.resize();
    this.restart();
  }
  view(angle: number) {
    this.camera.position.set(
      Math.sin(angle) * 3,
      this.controls.target.y,
      Math.cos(angle) * 3,
    );
    this.camera.lookAt(this.controls.target);
    this.controls.update();
    this.changedView();
  }
  private setMorph(suffix: string, value: number) {
    for (const m of this.morphs) {
      const dict = m.morphTargetDictionary!;
      const k = Object.keys(dict).find((k) => k.endsWith(suffix));
      if (k && m.morphTargetInfluences)
        m.morphTargetInfluences[dict[k]] = value;
    }
  }
  private restart = () => {
    if (this.frame) cancelAnimationFrame(this.frame);
    this.frame = 0;
    this.last = 0;
    this.schedule();
  };
  private schedule() {
    if (!this.disposed && !this.frame && !document.hidden && this.inView)
      this.frame = requestAnimationFrame(this.draw);
  }
  private draw = (time: number) => {
    this.frame = 0;
    if (this.disposed || document.hidden || !this.inView) return;
    if (this.last && time - this.last < 1000 / 30) {
      this.schedule();
      return;
    }
    const dt = this.last ? Math.min(0.08, (time - this.last) / 1000) : 0;
    this.last = time;
    if (this.presentation.active) {
      this.elapsed += dt;
      if (this.head && this.hasGaze) this.head.quaternion.copy(this.headPose);
      this.hasGaze = false;
      this.mixer?.update(dt);
      const blink = this.elapsed % 4.3;
      this.setMorph(
        "Fcl_EYE_Close",
        blink > 4.07 ? Math.sin(((blink - 4.07) / 0.23) * Math.PI) : 0,
      );
      this.setMorph("Fcl_MTH_A", mouthLevel(this.sample, Date.now()));
      if (this.head && !this.presentation.review) {
        this.headPose.copy(this.head.quaternion);
        const gaze = new THREE.Quaternion().setFromEuler(
          new THREE.Euler(-this.pointer.y * 0.06, this.pointer.x * 0.12, 0),
        );
        const local = this.headRest
          .clone()
          .invert()
          .multiply(gaze)
          .multiply(this.headRest);
        this.head.quaternion.multiply(local);
        this.hasGaze = true;
      }
    } else {
      this.setMorph("Fcl_EYE_Close", 0);
      this.setMorph("Fcl_MTH_A", 0);
      if (this.rendered === 0) this.mixer?.update(0);
    }
    this.renderer.render(this.scene, this.camera);
    this.host.dataset.frames = String(++this.rendered);
    if (this.presentation.active) this.schedule();
  };
  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    this.abort.abort();
    cancelAnimationFrame(this.frame);
    this.observer.disconnect();
    this.intersection.disconnect();
    this.unsubscribe();
    document.removeEventListener("visibilitychange", this.restart);
    window.removeEventListener("pointermove", this.follow);
    this.controls.removeEventListener("change", this.changedView);
    this.controls.dispose();
    this.mixer?.removeEventListener("finished", this.finished);
    this.mixer?.stopAllAction();
    if (this.model) {
      this.mixer?.uncacheRoot(this.model);
      disposeModel(this.model);
    }
    this.renderer.domElement.removeEventListener(
      "webglcontextlost",
      this.contextLost,
    );
    this.renderer.dispose();
    this.renderer.forceContextLoss();
    this.renderer.domElement.remove();
  }
}
