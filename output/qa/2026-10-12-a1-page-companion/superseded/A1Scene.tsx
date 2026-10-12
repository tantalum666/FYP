import { Component, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode, RefObject } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import {
  Box3,
  DataTexture,
  DoubleSide,
  MathUtils,
  MeshToonMaterial,
  NearestFilter,
  NoToneMapping,
  Quaternion,
  RGBAFormat,
  Vector3,
} from "three";
import type { Bone, Group, Material, Mesh, SkinnedMesh, Texture } from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { embeddedTextures } from "../avatar/embeddedTextures";
import { gesturePose } from "./motion";
import type { Gesture } from "./motion";

interface Props {
  gesture: Gesture;
  pulse: number;
  active: boolean;
  waveSide: "left" | "right";
  look: RefObject<{ x: number; y: number }>;
  onReady: () => void;
  onError: () => void;
}
class Boundary extends Component<
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
    const timer = setInterval(invalidate, 1000 / 30);
    return () => clearInterval(timer);
  }, [active, invalidate]);
  return null;
}
type Joint = { bone: Bone; rest: Quaternion; inverseWorld: Quaternion };
function dispose(root: Group) {
  const textures = new Set<Texture>(),
    materials = new Set<Material>();
  root.traverse((node) => {
    const mesh = node as Mesh;
    if (!mesh.isMesh) return;
    mesh.geometry.dispose();
    for (const material of Array.isArray(mesh.material)
      ? mesh.material
      : [mesh.material]) {
      materials.add(material);
      for (const value of Object.values(material))
        if (value && typeof value === "object" && "isTexture" in value)
          textures.add(value as Texture);
    }
  });
  textures.forEach((t) => t.dispose());
  materials.forEach((m) => m.dispose());
}
function Character(props: Props) {
  const [model, setModel] = useState<Group | null>(null);
  const joints = useRef(new Map<string, Joint>());
  const faces = useRef<SkinnedMesh[]>([]);
  const { invalidate, gl } = useThree();
  const clock = useRef(0),
    start = useRef(0),
    seenPulse = useRef(-1);
  const gaze = useRef({ x: 0, y: 0 });
  const scratch = useMemo(
    () => ({
      delta: new Quaternion(),
      q: new Quaternion(),
      axis: new Vector3(),
      x: new Vector3(1, 0, 0),
      y: new Vector3(0, 1, 0),
      z: new Vector3(0, 0, 1),
    }),
    [],
  );
  function rotate(name: string, x = 0, y = 0, z = 0) {
    const joint = joints.current.get(name);
    if (!joint) return;
    const s = scratch;
    s.delta.identity();
    for (const [axis, angle] of [
      [s.x, x],
      [s.y, y],
      [s.z, z],
    ] as const) {
      if (!angle) continue;
      s.axis.copy(axis).applyQuaternion(joint.inverseWorld);
      s.q.setFromAxisAngle(s.axis, angle);
      s.delta.multiply(s.q);
    }
    joint.bone.quaternion.copy(joint.rest).multiply(s.delta);
  }
  useEffect(() => {
    const abort = new AbortController();
    let alive = true,
      loaded: Group | null = null;
    const gradient = new DataTexture(
      new Uint8Array([
        142, 142, 142, 255, 205, 205, 205, 255, 255, 255, 255, 255,
      ]),
      3,
      1,
      RGBAFormat,
    );
    gradient.minFilter = gradient.magFilter = NearestFilter;
    gradient.generateMipmaps = false;
    gradient.needsUpdate = true;
    void (async () => {
      const response = await fetch("/companion/a1-engineering-v1.glb", {
        signal: abort.signal,
      });
      const maximum = 8 * 1024 * 1024;
      if (
        !response.ok ||
        Number(response.headers.get("content-length")) > maximum
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
        if (length > maximum) {
          await reader.cancel();
          throw new Error("MODEL_SIZE");
        }
        chunks.push(value);
      }
      const bytes = new Uint8Array(length);
      let offset = 0;
      for (const chunk of chunks) {
        bytes.set(chunk, offset);
        offset += chunk.length;
      }
      const gltf = await embeddedTextures(new GLTFLoader()).parseAsync(
        bytes.buffer,
        "",
      );
      loaded = gltf.scene;
      if (!alive) {
        dispose(loaded);
        loaded = null;
        return;
      }
      loaded.updateMatrixWorld(true);
      joints.current.clear();
      faces.current = [];
      const converted = new Map<Material, MeshToonMaterial>();
      let meshCount = 0,
        skinnedCount = 0;
      loaded.traverse((node) => {
        const bone = node as Bone,
          mesh = node as SkinnedMesh;
        if (bone.isBone)
          joints.current.set(bone.name, {
            bone,
            rest: bone.quaternion.clone(),
            inverseWorld: bone.getWorldQuaternion(new Quaternion()).invert(),
          });
        if (!mesh.isMesh) return;
        meshCount++;
        if (mesh.isSkinnedMesh) skinnedCount++;
        if (mesh.morphTargetDictionary) faces.current.push(mesh);
        mesh.frustumCulled = false;
        const change = (material: Material) => {
          if (converted.has(material)) return converted.get(material)!;
          const m = material as MeshToonMaterial;
          const toon = new MeshToonMaterial({
            color: m.color,
            map: m.map,
            alphaMap: m.alphaMap,
            transparent: m.transparent,
            opacity: m.opacity,
            alphaTest: Math.max(0.05, m.alphaTest),
            side: DoubleSide,
            gradientMap: gradient,
          });
          converted.set(material, toon);
          material.dispose();
          return toon;
        };
        mesh.material = Array.isArray(mesh.material)
          ? mesh.material.map(change)
          : change(mesh.material);
      });
      if (!joints.current.has("J_Bip_C_Head") || skinnedCount < 1)
        throw new Error("MODEL_RIG");
      const bounds = new Box3().setFromObject(loaded),
        size = bounds.getSize(new Vector3()),
        center = bounds.getCenter(new Vector3());
      if (!Number.isFinite(size.y) || size.y < 1 || size.y > 2)
        throw new Error("MODEL_BOUNDS");
      loaded.position.sub(center);
      rotate("J_Bip_L_UpperArm", 0, 0, -1.28);
      rotate("J_Bip_R_UpperArm", 0, 0, 1.28);
      loaded.updateMatrixWorld(true);
      gl.domElement.dataset.a1Topology = `skinned-3d:${meshCount}:${skinnedCount}`;
      gl.domElement.dataset.a1Depth = "volumetric-geometry";
      setModel(loaded);
      props.onReady();
      invalidate();
    })().catch(() => {
      if (loaded) {
        dispose(loaded);
        loaded = null;
      }
      if (alive) props.onError();
    });
    const lost = (event: Event) => {
      event.preventDefault();
      props.onError();
    };
    gl.domElement.addEventListener("webglcontextlost", lost);
    return () => {
      alive = false;
      abort.abort();
      gl.domElement.removeEventListener("webglcontextlost", lost);
      if (loaded) dispose(loaded);
      gradient.dispose();
    };
  }, [gl, invalidate, props.onError, props.onReady]);
  useFrame((_, delta) => {
    if (!model) return;
    const dt = Math.min(delta, 0.06);
    if (props.active) clock.current += dt;
    if (seenPulse.current !== props.pulse) {
      seenPulse.current = props.pulse;
      start.current = clock.current;
    }
    const t = props.active ? clock.current : 0;
    const pose = gesturePose(
      props.active ? props.gesture : "none",
      clock.current - start.current,
    );
    const g = gaze.current;
    g.x = props.active ? MathUtils.damp(g.x, props.look.current.x, 4, dt) : 0;
    g.y = props.active ? MathUtils.damp(g.y, props.look.current.y, 4, dt) : 0;
    const left = props.waveSide === "right" ? pose.greet : 0;
    const right = props.waveSide === "left" ? pose.greet : 0;
    rotate(
      "J_Bip_C_Head",
      pose.nod + g.y * 0.07,
      g.x * 0.17,
      -pose.greet * 0.025,
    );
    rotate(
      "J_Bip_C_Chest",
      Math.sin(t * 1.55) * 0.009,
      g.x * 0.025,
      Math.sin(t * 0.8) * 0.003,
    );
    rotate("J_Bip_C_Hips", 0, 0, pose.step * 0.016);
    rotate(
      "J_Bip_L_UpperArm",
      0,
      0,
      -1.28 + left * 0.33 + Math.sin(t * 1.2) * 0.012,
    );
    rotate(
      "J_Bip_R_UpperArm",
      0,
      0,
      1.28 - right * 0.33 - Math.sin(t * 1.2 + 0.6) * 0.012,
    );
    rotate("J_Bip_L_LowerArm", 0, 0, 0.08 + left * 1.6);
    rotate("J_Bip_R_LowerArm", 0, 0, -0.08 - right * 1.6);
    rotate("J_Bip_L_Hand", left * 0.5, 0, left * pose.wrist * 2);
    rotate("J_Bip_R_Hand", -right * 0.5, 0, -right * pose.wrist * 2);
    rotate("J_Bip_L_UpperLeg", pose.step * 0.055, 0, 0);
    rotate("J_Bip_L_LowerLeg", -pose.step * 0.09, 0, 0);
    rotate("J_Bip_L_Foot", pose.step * 0.045, 0, 0);
    model.rotation.y = g.x * 0.08;
    for (const mesh of faces.current) {
      for (const [name, index] of Object.entries(
        mesh.morphTargetDictionary ?? {},
      )) {
        if (!mesh.morphTargetInfluences) continue;
        if (/Fcl_EYE_Close/.test(name)) mesh.morphTargetInfluences[index] = 0;
        if (/Fcl_MTH_Fun$/.test(name))
          mesh.morphTargetInfluences[index] = pose.greet * 0.1;
      }
    }
    gl.domElement.dataset.a1Pose = `${props.active ? props.gesture : "paused"}:${pose.greet.toFixed(3)},${pose.nod.toFixed(3)},${pose.step.toFixed(3)}`;
    gl.domElement.dataset.a1Look = `${g.x.toFixed(3)},${g.y.toFixed(3)}`;
  });
  return model ? <primitive object={model} dispose={null} /> : null;
}
export default function A1Scene(props: Props) {
  return (
    <Boundary onError={props.onError}>
      <Canvas
        camera={{ position: [0, 0, 4.75], fov: 20, near: 0.1, far: 20 }}
        dpr={[1, 1.5]}
        frameloop="demand"
        resize={{ scroll: false, debounce: 0 }}
        gl={{
          alpha: true,
          antialias: true,
          powerPreference: "low-power",
          toneMapping: NoToneMapping,
        }}
        onCreated={({ gl }) => gl.setClearColor(0x000000, 0)}
        fallback={<span>3D display unavailable</span>}
      >
        <ambientLight intensity={0.55} />
        <directionalLight position={[-2, 3, 4]} intensity={0.85} />
        <directionalLight position={[2, 1, -2]} intensity={0.25} />
        <RenderClock active={props.active} />
        <Character {...props} />
      </Canvas>
    </Boundary>
  );
}
