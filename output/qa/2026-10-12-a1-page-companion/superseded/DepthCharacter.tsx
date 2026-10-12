import { Component, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode, RefObject } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import {
  BufferAttribute,
  DoubleSide,
  MathUtils,
  NoToneMapping,
  PlaneGeometry,
  SRGBColorSpace,
  TextureLoader,
  Vector3,
  Vector4,
} from "three";
import type { Mesh, Texture } from "three";
import { A1_ART } from "./art";
import {
  DEFORM_SHADER,
  depthAt,
  gesturePose,
  MESH_COLUMNS,
  MESH_ROWS,
  weightsAt,
} from "./depth-model";
import type { Gesture } from "./depth-model";

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
function Character(props: Props) {
  const [texture, setTexture] = useState<Texture | null>(null);
  const mesh = useRef<Mesh>(null);
  const { invalidate, gl } = useThree();
  const clock = useRef(0),
    start = useRef(0),
    seenPulse = useRef(-1);
  const smoothed = useRef({ x: 0, y: 0 });
  const uniforms = useMemo(
    () => ({
      uA1Head: { value: new Vector3() },
      uA1Arms: { value: new Vector4() },
      uA1Legs: { value: new Vector4() },
      uA1Breath: { value: 0 },
      uA1Time: { value: 0 },
    }),
    [],
  );
  const geometry = useMemo(() => {
    const g = new PlaneGeometry(
      A1_ART.viewBox[2] / A1_ART.viewBox[3],
      1,
      MESH_COLUMNS,
      MESH_ROWS,
    );
    const positions = g.getAttribute("position"),
      uv = g.getAttribute("uv");
    const skin = new Float32Array(positions.count * 4),
      detail = new Float32Array(positions.count * 4);
    for (let i = 0; i < positions.count; i++) {
      const x = A1_ART.viewBox[0] + uv.getX(i) * A1_ART.viewBox[2];
      const y = A1_ART.viewBox[1] + (1 - uv.getY(i)) * A1_ART.viewBox[3];
      const w = weightsAt(x, y);
      positions.setZ(i, depthAt(x, y));
      uv.setXY(i, x / A1_ART.width, 1 - y / A1_ART.height);
      skin.set([w.head, w.left, w.right, w.leftLeg], i * 4);
      detail.set([w.rightLeg, w.leftWrist, w.rightWrist, w.hair], i * 4);
    }
    g.setAttribute("a1Skin", new BufferAttribute(skin, 4));
    g.setAttribute("a1Detail", new BufferAttribute(detail, 4));
    g.computeVertexNormals();
    return g;
  }, []);
  useEffect(() => {
    let alive = true,
      loaded: Texture | null = null;
    new TextureLoader().load(
      A1_ART.idle,
      (image) => {
        loaded = image;
        if (!alive) {
          image.dispose();
          return;
        }
        image.colorSpace = SRGBColorSpace;
        image.anisotropy = Math.min(4, gl.capabilities.getMaxAnisotropy());
        setTexture(image);
        invalidate();
      },
      undefined,
      () => {
        if (alive) props.onError();
      },
    );
    const lost = (event: Event) => {
      event.preventDefault();
      props.onError();
    };
    gl.domElement.addEventListener("webglcontextlost", lost);
    return () => {
      alive = false;
      loaded?.dispose();
      gl.domElement.removeEventListener("webglcontextlost", lost);
    };
  }, [gl, invalidate, props.onError]);
  useEffect(() => {
    if (!texture) return;
    gl.domElement.dataset.a1Topology = `single-mesh:${geometry.getAttribute("position").count}`;
    gl.domElement.dataset.a1Depth = "sculpted-surface";
    props.onReady();
  }, [texture, geometry, gl, props.onReady]);
  useFrame((_, delta) => {
    if (!mesh.current) return;
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
      props.waveSide,
    );
    const gaze = smoothed.current;
    gaze.x = props.active
      ? MathUtils.damp(gaze.x, props.look.current.x, 4, dt)
      : 0;
    gaze.y = props.active
      ? MathUtils.damp(gaze.y, props.look.current.y, 4, dt)
      : 0;
    uniforms.uA1Head.value.set(
      pose.nod + gaze.y * 0.055,
      gaze.x * 0.13,
      -pose.greet * 0.025,
    );
    uniforms.uA1Arms.value.set(
      pose.armLeft + Math.sin(t * 1.3) * 0.012,
      pose.armRight + Math.sin(t * 1.3 + 0.6) * 0.012,
      pose.wrist,
      -pose.wrist,
    );
    uniforms.uA1Legs.value.set(
      pose.step * 0.025,
      -pose.step * 0.012,
      pose.step,
      0,
    );
    uniforms.uA1Breath.value = props.active ? Math.sin(t * 1.55) : 0;
    uniforms.uA1Time.value = t;
    mesh.current.rotation.set(
      gaze.y * 0.025,
      gaze.x * 0.2,
      Math.sin(t * 0.8) * 0.003,
    );
    mesh.current.position.x = pose.step * 0.0015;
    gl.domElement.dataset.a1Pose = `${props.active ? props.gesture : "paused"}:${pose.armLeft.toFixed(3)},${pose.armRight.toFixed(3)},${pose.nod.toFixed(3)},${pose.step.toFixed(3)}`;
    gl.domElement.dataset.a1Look = `${gaze.x.toFixed(3)},${gaze.y.toFixed(3)}`;
  });
  return texture ? (
    <mesh ref={mesh} geometry={geometry} frustumCulled={false}>
      <meshStandardMaterial
        map={texture}
        transparent
        alphaTest={0.035}
        side={DoubleSide}
        roughness={0.92}
        metalness={0}
        depthWrite={false}
        onBeforeCompile={(shader) => {
          Object.assign(shader.uniforms, uniforms);
          shader.vertexShader = DEFORM_SHADER + shader.vertexShader;
          shader.vertexShader = shader.vertexShader.replace(
            "#include <begin_vertex>",
            "vec3 transformed = a1Deform(position);",
          );
          shader.vertexShader = shader.vertexShader.replace(
            "#include <beginnormal_vertex>",
            "vec3 objectNormal = normalize(a1Deform(position + normal * .0005) - a1Deform(position));",
          );
        }}
      />
    </mesh>
  ) : null;
}
export default function DepthCharacter(props: Props) {
  return (
    <Boundary onError={props.onError}>
      <Canvas
        camera={{ position: [0, 0, 3.3], fov: 18, near: 0.1, far: 10 }}
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
        fallback={<span>2.5D display unavailable</span>}
      >
        <ambientLight intensity={1.45} />
        <directionalLight position={[-1.5, 2, 4]} intensity={1.1} />
        <directionalLight position={[2, 1, 3]} intensity={0.35} />
        <RenderClock active={props.active} />
        <Character {...props} />
      </Canvas>
    </Boundary>
  );
}
