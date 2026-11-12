import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import {
  VRMLoaderPlugin,
  VRMUtils,
  MToonMaterial,
  type VRM,
} from "@pixiv/three-vrm";
import { mouthLevel, subscribePlayback, type PlaybackSample } from "./output";
import type { Presentation } from "./renderer";
import { MODELS, readAppearance } from "./appearance";
import { HandPose, relaxArms } from "./hand-pose";
import {
  aliceMotion,
  blinkWeight,
  MOTION_BONES,
  type MotionBone,
} from "./alice-motion";
import {
  companionState,
  subscribeInteraction,
  type CompanionState,
} from "./interaction";

export type VrmExpression = "neutral" | "smile" | "blink" | "speak";

/** Load complete licensed VRMs with their own MToon, expression and spring bones. */
export class VrmViewer {
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.01, 30);
  private controls: OrbitControls;
  private resizeObserver: ResizeObserver;
  private abort = new AbortController();
  private vrm: VRM | null = null;
  private frame = 0;
  private previous = 0;
  private elapsed = 0;
  private disposed = false;
  private paused = matchMedia("(prefers-reduced-motion: reduce)").matches;
  private expression: VrmExpression = "neutral";
  private blinkStart = -10;
  private halfHeight = 0.3;
  private framingMode: "portrait" | "full" = "portrait";
  private height = 1.6;
  private target = new THREE.Vector3(0, 1.45, 0);
  private angle = 0;
  private palette: "original" | "silver" = "original";
  private originalColors = new Map<
    MToonMaterial,
    { color: THREE.Color; shade: THREE.Color }
  >();
  private headRatio = 1;
  private headScale = new THREE.Vector3(1, 1, 1);
  private presentation: Presentation | null = null;
  private pointer = { x: 0, y: 0 };
  private responseAt = -10;
  private gesture: "wave" | "nod" = "nod";
  private waveSide: "left" | "right" = "left";
  private bones = new Map<
    MotionBone,
    { node: THREE.Object3D; rest: THREE.Quaternion }
  >();
  private rotation = new THREE.Euler();
  private offset = new THREE.Quaternion();
  private goal = new THREE.Quaternion();
  private interaction: CompanionState | null = null;
  private unsubscribeInteraction: (() => void) | null = null;
  private frames = 0;
  private hands: HandPose | null = null;
  private sample: PlaybackSample = { level: 0, at: 0 };
  private unsubscribe: (() => void) | null = null;
  private intersection: IntersectionObserver;
  private inView = true;

  constructor(
    private host: HTMLDivElement,
    source: string | ArrayBuffer,
    private ready: () => void,
    private failed: () => void,
    private floating = false,
  ) {
    this.framingMode = floating ? "full" : "portrait";
    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: "low-power",
    });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.NoToneMapping;
    this.renderer.setClearColor(floating ? 0 : 0xf1f0ee, floating ? 0 : 1);
    this.renderer.domElement.setAttribute("aria-hidden", "true");
    host.append(this.renderer.domElement);
    host.dataset.loaded = "false";
    this.renderer.domElement.addEventListener("webglcontextlost", this.lost);
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0xc4c1d0, 1.4));
    const key = new THREE.DirectionalLight(0xffffff, 1.5);
    key.position.set(-1, 2, 3);
    this.scene.add(key);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enablePan = false;
    this.controls.minZoom = 0.65;
    this.controls.maxZoom = 2.2;
    this.controls.enabled = !floating;
    this.controls.addEventListener("change", this.schedule);
    this.resizeObserver = new ResizeObserver(this.resize);
    this.resizeObserver.observe(host);
    this.intersection = new IntersectionObserver((entries) => {
      this.inView = entries[0]?.isIntersecting ?? true;
      this.schedule();
    });
    this.intersection.observe(host);
    if (floating) {
      window.addEventListener("pointermove", this.follow, { passive: true });
      this.unsubscribe = subscribePlayback((sample) => {
        this.sample = sample;
        if (!this.paused) this.schedule();
      });
      this.unsubscribeInteraction = subscribeInteraction((state) => {
        this.interaction = state;
        if (!this.paused) this.schedule();
      });
    }
    document.addEventListener("visibilitychange", this.schedule);
    void this.load(source);
  }

  private async load(source: string | ArrayBuffer) {
    let loaded: THREE.Object3D | null = null;
    try {
      let buffer: ArrayBuffer;
      if (typeof source !== "string") {
        if (source.byteLength > 64 * 1024 * 1024)
          throw new Error("VRM_TOO_LARGE");
        buffer = source;
      } else {
        const response = await fetch(source, { signal: this.abort.signal });
        if (!response.ok || !response.body) throw new Error("VRM_UNAVAILABLE");
        const reader = response.body.getReader();
        const chunks: Uint8Array[] = [];
        let bytes = 0;
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          bytes += value.byteLength;
          if (bytes > 64 * 1024 * 1024) {
            await reader.cancel();
            throw new Error("VRM_TOO_LARGE");
          }
          chunks.push(value);
        }
        if (this.disposed) return;
        const joined = new Uint8Array(bytes);
        let offset = 0;
        for (const chunk of chunks) {
          joined.set(chunk, offset);
          offset += chunk.length;
        }
        buffer = joined.buffer;
      }
      const manager = new THREE.LoadingManager();
      let textureFailed = false;
      manager.onError = () => {
        textureFailed = true;
      };
      const loader = new GLTFLoader(manager);
      loader.register((parser) => {
        // Keep the same CSP as the application, using img-src blob: for images.
        parser.textureLoader = new THREE.TextureLoader(manager);
        return new VRMLoaderPlugin(parser);
      });
      const gltf = await loader.parseAsync(buffer, "");
      loaded = gltf.scene;
      const vrm = gltf.userData.vrm as VRM | undefined;
      if (this.disposed || textureFailed || !vrm) {
        VRMUtils.deepDispose(loaded);
        loaded = null;
        if (!this.disposed) throw new Error("VRM_OR_TEXTURE_UNAVAILABLE");
        return;
      }
      VRMUtils.rotateVRM0(vrm);
      this.vrm = vrm;
      for (const material of vrm.materials ?? [])
        if (material instanceof MToonMaterial)
          this.originalColors.set(material, {
            color: material.color.clone(),
            shade: material.shadeColorFactor.clone(),
          });
      const head = vrm.humanoid.getRawBoneNode("head");
      if (head) this.headScale.copy(head.scale);
      this.scene.add(vrm.scene);
      vrm.scene.updateMatrixWorld(true);
      relaxArms(vrm);
      vrm.humanoid.update();
      vrm.scene.updateMatrixWorld(true);
      for (const name of MOTION_BONES) {
        const node = vrm.humanoid.getNormalizedBoneNode(name);
        if (node) this.bones.set(name, { node, rest: node.quaternion.clone() });
      }
      this.hands = new HandPose(vrm);
      const left = vrm.humanoid.getRawBoneNode("leftUpperArm");
      const right = vrm.humanoid.getRawBoneNode("rightUpperArm");
      // Greet on the free side of the phone scene, away from its left calendar.
      if (left && right)
        this.waveSide =
          left.getWorldPosition(new THREE.Vector3()).x >
          right.getWorldPosition(new THREE.Vector3()).x
            ? "left"
            : "right";
      if (
        this.floating &&
        !this.interaction &&
        companionState(this.presentation?.state ?? "idle") === "idle"
      ) {
        this.gesture = "wave";
        this.responseAt = this.elapsed + 0.35;
      }
      // VRM0 was rotated after import. Initialize spring state in its final
      // world transform so the first frame does not throw the hair upward.
      vrm.springBoneManager?.setInitState();
      vrm.springBoneManager?.reset();
      vrm.update(1 / 60);
      vrm.scene.updateMatrixWorld(true);
      const box = new THREE.Box3().setFromObject(vrm.scene);
      this.height = Math.max(1, box.max.y - box.min.y);
      this.host.dataset.bytes = String(buffer.byteLength);
      this.host.dataset.materials = String(vrm.materials?.length ?? 0);
      this.host.dataset.source =
        typeof source === "string" ? source : "local-file";
      delete this.host.dataset.error;
      this.host.dataset.loaded = "true";
      this.framing(this.framingMode);
      this.setPalette(this.palette);
      this.ready();
      this.schedule();
    } catch (error) {
      this.host.dataset.error =
        error instanceof Error ? error.message : "VRM_LOAD_FAILED";
      if (loaded && !this.vrm) VRMUtils.deepDispose(loaded);
      if (!this.disposed) {
        this.dispose();
        this.failed();
      }
    }
  }

  framing(mode: "portrait" | "full") {
    this.framingMode = mode;
    if (!this.vrm) return;
    if (mode === "portrait") {
      this.vrm.humanoid.getRawBoneNode("head")?.getWorldPosition(this.target);
      this.target.y += 0.015;
      this.halfHeight = this.height * 0.18;
    } else {
      const box = new THREE.Box3().setFromObject(this.vrm.scene);
      box.getCenter(this.target);
      this.halfHeight = this.height * 0.55;
    }
    this.host.dataset.framing = mode;
    this.camera.zoom = 1;
    this.view(this.angle);
  }

  view(angle: number) {
    this.angle = angle;
    this.camera.position.set(
      this.target.x + 3 * Math.sin(angle),
      this.target.y,
      this.target.z + 3 * Math.cos(angle),
    );
    this.controls.target.copy(this.target);
    this.controls.update();
    this.host.dataset.angle = String(angle);
    this.resize();
  }

  setExpression(expression: VrmExpression) {
    this.expression = expression;
    this.blinkStart = this.elapsed;
    this.host.dataset.expression = expression;
    this.schedule();
  }

  setPaused(paused: boolean) {
    this.paused = paused;
    this.schedule();
  }

  present(value: Presentation) {
    const previous = this.presentation;
    this.presentation = value;
    this.controls.enabled = value.review;
    this.setPaused(!value.active);
    if (
      value.action !== "Idle" &&
      (value.nonce !== previous?.nonce || value.action !== previous?.action)
    ) {
      this.gesture = value.action === "Wave" ? "wave" : "nod";
      this.responseAt = this.elapsed;
    }
    if (
      value.review !== previous?.review ||
      value.framing !== previous?.framing
    )
      this.framing(value.framing === "face" ? "portrait" : "full");
  }

  private follow = (event: PointerEvent) => {
    if (event.pointerType !== "mouse" || this.paused) return;
    const box = this.host.getBoundingClientRect();
    this.pointer.x = THREE.MathUtils.clamp(
      (event.clientX - box.left - box.width / 2) / Math.max(box.width, 250),
      -1,
      1,
    );
    this.pointer.y = THREE.MathUtils.clamp(
      (event.clientY - box.top - box.height * 0.16) / Math.max(box.height, 350),
      -1,
      1,
    );
  };

  setPalette(palette: "original" | "silver") {
    this.palette = palette;
    for (const [material, original] of this.originalColors) {
      material.color.copy(original.color);
      material.shadeColorFactor.copy(original.shade);
      if (palette === "silver" && /hair|brow/i.test(material.name)) {
        material.color.set("#b7b3c6");
        material.shadeColorFactor.set("#858196");
      }
    }
    this.host.dataset.palette = palette;
    this.schedule();
  }

  setHeadRatio(ratio: number) {
    this.headRatio = THREE.MathUtils.clamp(
      Number.isFinite(ratio) ? ratio : 1,
      0.92,
      1.08,
    );
    this.host.dataset.headRatio = String(this.headRatio);
    this.schedule();
  }

  private resize = () => {
    if (this.disposed) return;
    const { width, height } = this.host.getBoundingClientRect();
    if (!width || !height) return;
    this.camera.left = (-this.halfHeight * width) / height;
    this.camera.right = (this.halfHeight * width) / height;
    this.camera.top = this.halfHeight;
    this.camera.bottom = -this.halfHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height, false);
    this.schedule();
  };

  private lost = (event: Event) => {
    event.preventDefault();
    this.dispose();
    this.failed();
  };
  private schedule = () => {
    if (!this.disposed && this.inView && !document.hidden && !this.frame)
      this.frame = requestAnimationFrame(this.draw);
  };

  private draw = (at: number) => {
    this.frame = 0;
    if (this.disposed || !this.inView || document.hidden) return;
    if (at - this.previous < 1000 / 30) {
      this.schedule();
      return;
    }
    const delta = this.previous
      ? Math.min((at - this.previous) / 1000, 0.05)
      : 0;
    this.previous = at;
    if (!this.paused) this.elapsed += delta;
    const playback =
      this.floating && !this.paused ? mouthLevel(this.sample, Date.now()) : 0;
    const motion = aliceMotion(this.elapsed, {
      state:
        playback > 0.02
          ? "speaking"
          : (this.interaction ?? this.presentation?.state),
      lookX: this.pointer.x,
      lookY: this.pointer.y,
      gesture: this.gesture,
      gestureAt: this.responseAt,
      waveSide: this.waveSide,
    });
    if (this.floating && this.vrm && !this.paused) {
      const blend = 1 - Math.exp(-9 * delta);
      for (const [name, { node, rest }] of this.bones) {
        const [x, y, z] = motion.pose[name];
        this.offset.setFromEuler(this.rotation.set(x, y, z));
        this.goal.copy(rest).multiply(this.offset);
        node.quaternion.slerp(this.goal, blend);
      }
      this.hands?.update(
        delta,
        motion.gesture === "wave" ? this.waveSide : null,
        motion.openness,
      );
    }
    const manager = this.vrm?.expressionManager;
    if (manager) {
      manager.resetValues();
      const blink =
        this.expression === "blink"
          ? this.paused
            ? 1
            : Math.exp(
                -Math.pow((this.elapsed - this.blinkStart - 0.16) / 0.08, 2),
              )
          : this.paused
            ? 0
            : blinkWeight(this.elapsed);
      manager.setValue("blink", blink);
      manager.setValue(
        "happy",
        this.expression === "smile" ? 0.25 : this.floating ? motion.smile : 0,
      );
      manager.setValue(
        "aa",
        this.expression === "speak"
          ? 0.1 + 0.14 * (0.5 + 0.5 * Math.sin(this.elapsed * 9))
          : playback * 0.5,
      );
      this.host.dataset.mouth = (
        this.expression === "speak" ? 0.2 : playback * 0.5
      ).toFixed(3);
    }
    if (this.vrm) {
      if (this.paused) {
        this.vrm.humanoid.update();
        this.vrm.expressionManager?.update();
        this.vrm.nodeConstraintManager?.update();
        for (const material of this.vrm.materials ?? [])
          if (material instanceof MToonMaterial) material.update(0);
      } else this.vrm.update(delta);
    }
    const head = this.vrm?.humanoid.getRawBoneNode("head");
    if (head) {
      head.scale.copy(this.headScale).multiplyScalar(this.headRatio);
      head.updateMatrixWorld(true);
    }
    this.renderer.render(this.scene, this.camera);
    this.host.dataset.motion = motion.gesture ?? motion.state;
    this.host.dataset.frames = String(++this.frames);
    if (!this.paused && this.vrm) this.schedule();
  };

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    this.abort.abort();
    cancelAnimationFrame(this.frame);
    this.resizeObserver.disconnect();
    this.intersection.disconnect();
    this.controls.removeEventListener("change", this.schedule);
    this.controls.dispose();
    document.removeEventListener("visibilitychange", this.schedule);
    window.removeEventListener("pointermove", this.follow);
    this.unsubscribe?.();
    this.unsubscribeInteraction?.();
    this.bones.clear();
    this.hands = null;
    this.renderer.domElement.removeEventListener("webglcontextlost", this.lost);
    if (this.vrm) VRMUtils.deepDispose(this.vrm.scene);
    this.originalColors.clear();
    this.renderer.dispose();
    this.renderer.forceContextLoss();
    this.renderer.domElement.remove();
  }
}

/** Resident/device adapter: keep the established presentation and audio boundary. */
export class NativeA1Renderer {
  private viewer: VrmViewer;
  constructor(host: HTMLDivElement, ready: () => void, failed: () => void) {
    const appearance = readAppearance();
    this.viewer = new VrmViewer(
      host,
      MODELS[appearance.model].file,
      ready,
      failed,
      true,
    );
    this.viewer.setPalette(appearance.palette);
    this.viewer.setHeadRatio(appearance.headRatio);
  }
  update(presentation: Presentation) {
    this.viewer.present(presentation);
  }
  view(angle: number) {
    this.viewer.view(angle);
  }
  dispose() {
    this.viewer.dispose();
  }
}
