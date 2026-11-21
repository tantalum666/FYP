import {
  BufferAttribute,
  MathUtils,
  SkinnedMesh,
  Vector3,
  type Object3D,
} from "three";
import type { VRM } from "@pixiv/three-vrm";
import fit from "./uniform-rest.json" with { type: "json" };
import { fitAliceSleeves } from "./sleeve-colliders.ts";

type Side = "left" | "right";
type Arm = {
  frame: Object3D;
  elbow: Object3D;
  wrist: Object3D;
  neutralElbow: Vector3;
  neutralWrist: Vector3;
  upperLength: number;
  length: number;
};
const sides = ["left", "right"] as const;

/** How much cloth is in contact with each resting elbow and cuff.
 * All distances are measured in the shoulder's parent frame. */
export class UniformContact {
  readonly weights = [0, 0, 0, 0];
  private arms: Partial<Record<Side, Arm>> = {};
  private point = new Vector3();
  constructor(humanoid: VRM["humanoid"]) {
    for (const side of sides) {
      const upper = humanoid.getNormalizedBoneNode(`${side}UpperArm`);
      const elbow = humanoid.getNormalizedBoneNode(`${side}LowerArm`),
        wrist = humanoid.getNormalizedBoneNode(`${side}Hand`);
      if (!upper?.parent || !elbow || !wrist) continue;
      const frame = upper.parent;
      const local = (n: Object3D) =>
        frame.worldToLocal(n.getWorldPosition(new Vector3()));
      const neutralElbow = local(elbow),
        neutralWrist = local(wrist);
      const upperLength = neutralElbow.distanceTo(local(upper));
      this.arms[side] = {
        frame,
        elbow,
        wrist,
        neutralElbow,
        neutralWrist,
        upperLength,
        length: upperLength + neutralElbow.distanceTo(neutralWrist),
      };
    }
    this.update();
  }
  update() {
    for (const [i, side] of sides.entries()) {
      const arm = this.arms[side];
      if (!arm || arm.upperLength < 1e-5) continue;
      const d = (n: Object3D, neutral: Vector3) =>
        arm.frame
          .worldToLocal(n.getWorldPosition(this.point))
          .distanceTo(neutral);
      this.weights[2 * i] =
        1 -
        MathUtils.smoothstep(
          d(arm.elbow, arm.neutralElbow) / arm.upperLength,
          0.075,
          0.68,
        );
      this.weights[2 * i + 1] =
        1 -
        MathUtils.smoothstep(
          d(arm.wrist, arm.neutralWrist) / arm.length,
          0.075,
          0.5,
        );
    }
    return this.weights;
  }
}

/** Four sparse, authored clothing correctives on the bundled uniform only. */
export class RestingUniform {
  private updateColliders: ReturnType<typeof fitAliceSleeves>;
  private meshes: SkinnedMesh[] = [];
  private contact: UniformContact;
  constructor(vrm: VRM) {
    this.updateColliders = fitAliceSleeves(vrm.springBoneManager);
    this.contact = new UniformContact(vrm.humanoid);
    const attributes = sides.flatMap((side) => {
      const elbow = new Float32Array(fit.vertexCount * 3),
        cuff = new Float32Array(elbow.length);
      for (const [vertex, x, y, z, part] of fit[side]) {
        const u = part / 255;
        [x, y, z].forEach((value, axis) => {
          const displacement = value * 0.0001;
          elbow[vertex * 3 + axis] = displacement * u;
          cuff[vertex * 3 + axis] = displacement * (1 - u);
        });
      }
      return [new BufferAttribute(elbow, 3), new BufferAttribute(cuff, 3)];
    });
    vrm.scene.traverse((node) => {
      if (!(node instanceof SkinnedMesh)) return;
      const materials = Array.isArray(node.material)
          ? node.material
          : [node.material],
        g = node.geometry;
      if (
        !materials.some((m) => /_(Tops|Bottoms)_/.test(m.name)) ||
        g.attributes.position.count !== fit.vertexCount
      )
        return;
      if (
        g.morphAttributes.position?.length &&
        g.morphAttributes.position !== attributes
      )
        return;
      g.morphAttributes.position = attributes;
      g.morphTargetsRelative = true;
      node.updateMorphTargets();
      this.meshes.push(node);
    });
    this.update();
  }
  update() {
    const w = this.contact.update();
    this.updateColliders?.(w);
    for (const mesh of this.meshes)
      for (let i = 0; i < w.length; i++) mesh.morphTargetInfluences![i] = w[i];
  }
}
