import { Component, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode, RefObject } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import {
  Box3,
  Euler,
  NoToneMapping,
  OrthographicCamera,
  Quaternion,
  Vector3,
} from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { VRMLoaderPlugin, VRMUtils } from "@pixiv/three-vrm";
import type { VRM, VRMHumanBoneName } from "@pixiv/three-vrm";
import { inspectVrm, MAX_MODEL_BYTES, playbackLevel } from "./model";
import type { AvatarState, PlaybackSample } from "./model";

interface Props {
  url: string;
  state: AvatarState;
  active: boolean;
  reduced: boolean;
  mouth: RefObject<PlaybackSample | null>;
  allowMouth: boolean;
  onStatus: (status: "loading" | "ready" | "error", name?: string) => void;
}

class SceneBoundary extends Component<
  { children: ReactNode; onError: () => void },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch() {
    this.props.onError();
  }
  render() {
    return this.state.failed ? null : this.props.children;
  }
}

function RenderClock({ active }: { active: boolean }) {
  const invalidate = useThree((s) => s.invalidate);
  useEffect(() => {
    invalidate();
    if (!active) return;
    // Target presentation cadence, not a measured Pi performance claim.
    const timer = setInterval(invalidate, 1000 / 30);
    return () => clearInterval(timer);
  }, [active, invalidate]);
  return null;
}

function ContextWatch({ onStatus }: Pick<Props, "onStatus">) {
  const canvas = useThree((s) => s.gl.domElement);
  useEffect(() => {
    const lost = () => onStatus("error");
    canvas.addEventListener("webglcontextlost", lost);
    return () => canvas.removeEventListener("webglcontextlost", lost);
  }, [canvas, onStatus]);
  return null;
}

function Character({
  url,
  state,
  active,
  reduced,
  mouth,
  allowMouth,
  onStatus,
}: Props) {
  const [vrm, setVrm] = useState<VRM | null>(null);
  const { camera, size, invalidate, gl } = useThree();
  const extent = useRef({ width: 1, height: 1.8 });
  const clock = useRef(0),
    open = useRef(0);
  const scratch = useMemo(
    () => ({ rotation: new Euler(), quaternion: new Quaternion() }),
    [],
  );
  const bones = useMemo(() => {
    const names: VRMHumanBoneName[] = [
      "hips",
      "spine",
      "head",
      "leftUpperArm",
      "rightUpperArm",
      "leftLowerArm",
      "rightLowerArm",
    ];
    return names.map((name) => ({
      name,
      node: vrm?.humanoid.getNormalizedBoneNode(name) ?? null,
    }));
  }, [vrm]);

  useEffect(() => {
    const abort = new AbortController();
    let live = true,
      loaded: VRM | null = null;
    onStatus("loading");
    setVrm(null);
    void (async () => {
      const response = await fetch(url, { signal: abort.signal });
      if (
        !response.ok ||
        Number(response.headers.get("content-length")) > MAX_MODEL_BYTES
      )
        throw new Error("MODEL_FETCH");
      const reader = response.body?.getReader();
      if (!reader) throw new Error("MODEL_FETCH");
      const chunks: Uint8Array[] = [];
      let length = 0;
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        length += value.byteLength;
        if (length > MAX_MODEL_BYTES) {
          await reader.cancel();
          throw new Error("MODEL_SIZE");
        }
        chunks.push(value);
      }
      const bytes = new Uint8Array(length);
      let offset = 0;
      for (const chunk of chunks) {
        bytes.set(chunk, offset);
        offset += chunk.byteLength;
      }
      const info = inspectVrm(bytes.buffer);
      const loader = new GLTFLoader();
      loader.register((parser) => new VRMLoaderPlugin(parser));
      const gltf = await loader.parseAsync(bytes.buffer, "");
      loaded = (gltf.userData.vrm as VRM | undefined) ?? null;
      if (!loaded) {
        VRMUtils.deepDispose(gltf.scene);
        throw new Error("MODEL_NOT_VRM");
      }
      if (!live) {
        VRMUtils.deepDispose(loaded.scene);
        loaded = null;
        return;
      }
      VRMUtils.rotateVRM0(loaded);
      loaded.humanoid
        .getNormalizedBoneNode("leftUpperArm")
        ?.rotation.set(0, 0, -1.22);
      loaded.humanoid
        .getNormalizedBoneNode("rightUpperArm")
        ?.rotation.set(0, 0, 1.22);
      loaded.update(0);
      loaded.scene.updateMatrixWorld(true);
      const bounds = new Box3().setFromObject(loaded.scene),
        center = bounds.getCenter(new Vector3()),
        dimensions = bounds.getSize(new Vector3());
      if (
        ![dimensions.x, dimensions.y, dimensions.z].every(Number.isFinite) ||
        dimensions.y < 0.1 ||
        dimensions.y > 10
      )
        throw new Error("MODEL_BOUNDS");
      loaded.scene.position.sub(center);
      extent.current = { width: dimensions.x, height: dimensions.y };
      loaded.scene.traverse((node) => {
        node.frustumCulled = false;
      });
      setVrm(loaded);
      onStatus("ready", info.name);
      invalidate();
    })().catch(() => {
      if (loaded) {
        VRMUtils.deepDispose(loaded.scene);
        loaded = null;
      }
      if (live) onStatus("error");
    });
    return () => {
      live = false;
      abort.abort();
      if (loaded) {
        VRMUtils.deepDispose(loaded.scene);
        loaded = null;
      }
    };
  }, [url, invalidate, onStatus]);

  useEffect(() => {
    if (!(camera instanceof OrthographicCamera) || !vrm) return;
    const aspect = size.width / Math.max(1, size.height),
      fit = extent.current;
    const half = Math.max(fit.height * 0.6, (fit.width * 0.64) / aspect);
    camera.left = -half * aspect;
    camera.right = half * aspect;
    camera.top = half;
    camera.bottom = -half;
    camera.position.set(0, 0, 5);
    camera.lookAt(0, 0, 0);
    camera.updateProjectionMatrix();
    invalidate();
  }, [camera, size.width, size.height, vrm, invalidate]);

  useFrame((_, delta) => {
    if (!vrm) return;
    const dt = Math.min(delta, 0.05),
      moving = active && !reduced;
    if (moving) clock.current += dt;
    const t = clock.current,
      breathe = moving ? Math.sin(t * 1.8) : 0;
    const talking = state === "speaking",
      listening = state === "listening";
    for (const { name, node } of bones) {
      if (!node) continue;
      let x = 0,
        y = 0,
        z = 0;
      if (name === "spine") {
        x = breathe * 0.012;
        z = moving ? Math.sin(t * 0.65) * 0.012 : 0;
      }
      if (name === "head") {
        x =
          state === "alert" && moving
            ? Math.sin(t * 3) * 0.12
            : state === "thinking"
              ? -0.08
              : 0;
        y = moving ? Math.sin(t * 0.6) * 0.06 : 0;
        z = listening ? 0.1 : state === "confirm" ? -0.06 : 0;
      }
      if (name === "leftUpperArm") {
        z = -1.22;
        x = breathe * 0.015;
      }
      if (name === "rightUpperArm") {
        z = 1.22 - (talking && moving ? 0.18 + Math.sin(t * 2) * 0.06 : 0);
        x = talking && moving ? -0.18 : 0;
      }
      if (name === "leftLowerArm") z = -0.08;
      if (name === "rightLowerArm") {
        z = talking && moving ? 0.55 : 0.08;
        x = state === "thinking" ? -0.3 : 0;
      }
      scratch.rotation.set(x, y, z);
      scratch.quaternion.setFromEuler(scratch.rotation);
      node.quaternion.slerp(scratch.quaternion, 1 - Math.exp(-dt * 9));
    }
    const desired = active && allowMouth ? playbackLevel(mouth.current) : 0;
    open.current = active
      ? open.current + (desired - open.current) * (1 - Math.exp(-dt * 22))
      : 0;
    vrm.expressionManager?.setValue("aa", open.current);
    // Small, non-sensitive presentation values support rendered regression QA.
    // They carry no audio, transcript or workspace content.
    gl.domElement.dataset.mouthOpen = open.current.toFixed(2);
    gl.domElement.dataset.playbackLevel = desired.toFixed(2);
    gl.domElement.dataset.animation = !active
      ? "paused"
      : reduced
        ? "reduced"
        : "active";
    vrm.expressionManager?.setValue("oh", open.current * 0.12);
    vrm.expressionManager?.setValue("happy", state === "idle" ? 0.08 : 0);
    const phase = t % 4.7;
    vrm.expressionManager?.setValue(
      "blink",
      moving && phase < 0.16 ? Math.sin((phase / 0.16) * Math.PI) : 0,
    );
    vrm.update(active ? dt : 0);
  });
  return vrm ? <primitive object={vrm.scene} dispose={null} /> : null;
}

export default function AvatarScene(props: Props) {
  return (
    <SceneBoundary onError={() => props.onStatus("error")}>
      <Canvas
        orthographic
        camera={{ position: [0, 0, 5], near: 0.01, far: 30 }}
        dpr={[1, 1.5]}
        frameloop="demand"
        gl={{
          alpha: true,
          antialias: true,
          powerPreference: "low-power",
          toneMapping: NoToneMapping,
        }}
        onCreated={({ gl }) => {
          gl.setClearColor(0x000000, 0);
        }}
        fallback={<span>3D display unavailable</span>}
      >
        <ambientLight intensity={0.8} />
        <directionalLight position={[1, 3, 4]} intensity={1.3} />
        <directionalLight position={[-2, 1, -2]} intensity={0.5} />
        <RenderClock active={props.active} />
        <ContextWatch onStatus={props.onStatus} />
        <Character {...props} />
      </Canvas>
    </SceneBoundary>
  );
}
