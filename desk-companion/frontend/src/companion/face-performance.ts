import { Mesh } from "three";
import {
  VRMExpression,
  VRMExpressionMorphTargetBind,
  type VRM,
  type VRMExpressionManager,
} from "@pixiv/three-vrm";
import type { FaceCue } from "./performance-pose.ts";
import type { Face } from "./performance-score.ts";

type Features = Record<string, number>;
const faces: Record<
  Face,
  { upper: Features; mouth: Features; fallback: string }
> = {
  attentive: {
    upper: { BRW_Surprised: 0.54, EYE_Surprised: 0.58, EYE_Natural: 0.09 },
    mouth: { MTH_Small: 0.24, MTH_U: 0.17 },
    fallback: "neutral",
  },
  pensive: {
    upper: { BRW_Angry: 0.47, BRW_Question_L: 0.61, EYE_Joy_R: 0.34 },
    mouth: { MTH_Small: 0.62, MTH_Down: 0.23 },
    fallback: "relaxed",
  },
  wry: {
    upper: { BRW_Question_L: 0.88, EYE_Joy_L: 0.3, BRW_Fun: 0.18 },
    mouth: { MTH_Up: 0.27, MTH_Fun: 0.28, MTH_Smile_R: 0.14 },
    fallback: "happy",
  },
  proud: {
    upper: { BRW_Joy: 0.6, BRW_Angry: 0.22, EYE_Fun: 0.62 },
    mouth: { MTH_Up: 0.56, MTH_Fun: 0.19, MTH_Smile_R: 0.08 },
    fallback: "happy",
  },
  relieved: {
    upper: { BRW_Sorrow: 0.21, BRW_Fun: 0.42, EYE_Fun: 0.7 },
    mouth: { MTH_U: 0.34, MTH_Small: 0.26 },
    fallback: "relaxed",
  },
  bashful: {
    upper: { BRW_Sorrow: 0.4, EYE_Fun: 0.55, EYE_Joy_R: 0.23 },
    mouth: { MTH_Up: 0.23, MTH_Fun: 0.14, MTH_Smile_R: 0.075 },
    fallback: "relaxed",
  },
  apologetic: {
    upper: { BRW_Sorrow: 0.78, BRW_Apology_R: 0.25, EYE_Sorrow: 0.56 },
    mouth: { MTH_Down: 0.75, MTH_Close: 0.18, MTH_Small: 0.32 },
    fallback: "sad",
  },
  celebrate: {
    upper: { BRW_Joy: 0.9, EYE_Joy: 0.78 },
    mouth: { MTH_Joy: 0.86 },
    fallback: "happy",
  },
  comfort: {
    upper: { BRW_Sorrow: 0.94, EYE_Sorrow: 0.67 },
    mouth: { MTH_Sorrow: 0.7, MTH_Down: 0.18 },
    fallback: "sad",
  },
  appreciate: {
    upper: { BRW_Joy: 0.52, EYE_Fun: 0.74 },
    mouth: { MTH_Fun: 0.77, MTH_Up: 0.15 },
    fallback: "relaxed",
  },
  surprised: {
    upper: { BRW_Surprised: 0.98, EYE_Surprised: 0.91 },
    mouth: { MTH_Surprised: 0.85 },
    fallback: "surprised",
  },
  amused: {
    upper: { BRW_Fun: 0.9, EYE_Joy: 0.96 },
    mouth: { MTH_Joy: 0.82, MTH_Up: 0.12 },
    fallback: "happy",
  },
  curious: {
    upper: { BRW_Surprised: 0.62, EYE_Surprised: 0.32, EYE_Joy_R: 0.26 },
    mouth: { MTH_Small: 0.3 },
    fallback: "surprised",
  },
  encourage: {
    upper: { BRW_Angry: 0.27, BRW_Fun: 0.25, EYE_Fun: 0.54 },
    mouth: { MTH_Up: 0.75, MTH_Fun: 0.15 },
    fallback: "happy",
  },
};

function bind(
  manager: VRMExpressionManager,
  meshes: Mesh[],
  name: string,
  features: Features,
) {
  const expression = new VRMExpression(name);
  for (const mesh of meshes)
    for (const [part, weight] of Object.entries(features)) {
      const index = mesh.morphTargetDictionary?.["Fcl_" + part];
      if (index !== undefined)
        expression.addBind(
          new VRMExpressionMorphTargetBind({
            primitives: [mesh],
            index,
            weight,
          }),
        );
    }
  if (!expression.binds.length) return null;
  manager.registerExpression(expression);
  return name;
}

/** Use the original artist's brow, eyelid and lip shapes through VRM's mixer. */
export class FacePerformance {
  private closedLips: string | null = null;
  private layers: {
    face: Face;
    upper: string | null;
    mouth: string | null;
    fallback: string | null;
    weight: number;
    mouthWeight: number;
  }[] = [];
  constructor(vrm: VRM) {
    const manager = vrm.expressionManager;
    if (!manager) return;
    const meshes: Mesh[] = [];
    vrm.scene.traverse((node) => {
      if (node instanceof Mesh && node.morphTargetDictionary) meshes.push(node);
    });
    this.closedLips = bind(manager, meshes, "alice-closed-lips", {
      MTH_Close: 1,
    });
    for (const face of Object.keys(faces) as Face[]) {
      const spec = faces[face];
      const preset = Object.keys(manager.expressionMap).find(
        (n) => n.toLowerCase() === spec.fallback,
      );
      this.layers.push({
        face,
        upper: bind(manager, meshes, "alice-upper-" + face, spec.upper),
        mouth: bind(manager, meshes, "alice-mouth-" + face, spec.mouth),
        fallback: preset ?? null,
        weight: 0,
        mouthWeight: 0,
      });
    }
  }
  reset() {
    for (const layer of this.layers) {
      layer.weight = 0;
      layer.mouthWeight = 0;
    }
  }

  apply(
    manager: VRMExpressionManager,
    cue: FaceCue | null,
    playback: number,
    delta: number,
  ) {
    const blend = 1 - Math.exp(-12 * delta);
    const mouthBlend = 1 - Math.exp(-8 * delta);
    let expressionMouth = 0;
    for (const layer of this.layers) {
      const target = cue?.face === layer.face ? cue.weight : 0;
      layer.weight += (target - layer.weight) * blend;
      const mouthTarget =
        cue && (cue.mouthFace ?? cue.face) === layer.face ? cue.weight : 0;
      layer.mouthWeight += (mouthTarget - layer.mouthWeight) * mouthBlend;
      const w = layer.weight,
        lips = layer.mouthWeight;
      expressionMouth += lips;
      if (w < 0.001 && lips < 0.001) continue;
      if (layer.upper || layer.mouth) {
        // Leave the other eye open during an intentional wink.
        if (layer.upper)
          manager.setValue(layer.upper, w * (1 - (cue?.wink ?? 0) * 0.85));
        if (layer.mouth)
          manager.setValue(layer.mouth, lips * (1 - 0.85 * playback));
      } else if (layer.fallback) {
        manager.setValue(
          layer.fallback,
          Math.max(
            manager.getValue(layer.fallback) ?? 0,
            w * (1 - 0.65 * playback),
          ),
        );
      }
    }
    if (this.closedLips)
      manager.setValue(
        this.closedLips,
        0.94 *
          Math.max(0, 1 - expressionMouth) *
          Math.max(0, 1 - 12 * playback),
      );
    if (cue?.eyelids && manager.getExpression("blink"))
      manager.setValue(
        "blink",
        Math.max(manager.getValue("blink") ?? 0, cue.eyelids),
      );
    if (cue?.wink && manager.getExpression("blinkLeft"))
      manager.setValue("blinkLeft", cue.wink * 0.97);
  }
}
