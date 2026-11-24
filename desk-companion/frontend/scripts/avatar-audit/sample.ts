/** Export rendered bone matrices for the optional mesh audit. No GPU or camera inputs. */
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { aliceMotion } from "../../src/companion/alice-motion.ts";
import {
  GESTURE_SECONDS,
  type AliceGesture,
} from "../../src/companion/motion-cues.ts";
import { palmNormal } from "../../src/companion/hand-pose.ts";
import { aliceRig, filteredPose } from "../../tests/alice-rig-fixture.ts";

const out = process.argv[2];
if (!out) throw new Error("Pass an output directory for the frame matrices.");
mkdirSync(out, { recursive: true });
const gestures = Object.keys(GESTURE_SECONDS) as AliceGesture[];
const crossings: [AliceGesture, AliceGesture][] = [
  ["giggle", "gratefulBow"],
  ["gratefulBow", "giggle"],
  ["hairTuck", "comfort"],
  ["applause", "comfort"],
  ["sleeveAdjust", "victory"],
  ["chinRest", "astonished"],
];
const cases: {
  name: string;
  first: AliceGesture | null;
  second: AliceGesture | null;
}[] = [
  { name: "idle", first: null, second: null },
  ...gestures.map((name) => ({ name, first: name, second: null })),
];
for (const [first, second] of crossings)
  cases.push({ name: first + "-to-" + second, first, second });
const rad = 180 / Math.PI;
const index = [];
for (const { name, first, second } of cases)
  for (const side of ["left", "right"] as const) {
    const rig = aliceRig(),
      joints = rig.joints;
    const count = Math.ceil(
      (second
        ? 2.6 + GESTURE_SECONDS[second] + 0.8
        : first
          ? 1 + GESTURE_SECONDS[first] + 0.8
          : 18) * 30,
    );
    const matrices = new Float32Array(count * rig.nodes.length * 16);
    const limits = { bend: 0, sideBend: 0, wristRotation: 0, footTravel: 0 };
    const handStats = [];
    const uniformContact = [];
    for (let frame = 0; frame < count; frame++) {
      const t = frame / 30,
        switched = second !== null && t >= 2.6,
        gesture = switched ? second! : first;
      const state =
        gesture === "explain"
          ? "speaking"
          : gesture === "ponder"
            ? "thinking"
            : "idle";
      const m = aliceMotion(t, {
        gesture: gesture ?? undefined,
        gestureAt: switched ? 2.6 : 1,
        waveSide: side,
        state,
      });
      filteredPose(rig, joints, m, side, 1 / 30);
      uniformContact.push(rig.contact.update().map((w) => +w.toFixed(5)));
      rig.nodes.forEach((n, i) =>
        matrices.set(
          n.matrixWorld.elements,
          (frame * rig.nodes.length + i) * 16,
        ),
      );
      for (const [i, h] of (["left", "right"] as const).entries()) {
        const wrist = rig.position(h + "Hand"),
          dir = rig
            .position(h + "MiddleProximal")
            .sub(wrist)
            .normalize();
        const fromElbow = wrist
          .clone()
          .sub(rig.position(h + "LowerArm"))
          .normalize();
        const palm = palmNormal(
          h,
          wrist,
          rig.position(h + "IndexProximal"),
          rig.position(h + "MiddleProximal"),
          rig.position(h + "LittleProximal"),
        );
        const bend = dir.angleTo(fromElbow) * rad;
        const lateral = Math.abs(
          Math.asin(
            Math.max(
              -1,
              Math.min(1, fromElbow.dot(dir.clone().cross(palm).normalize())),
            ),
          ) * rad,
        );
        const twist =
          rig.humanoid
            .getNormalizedBoneNode(h + "Hand")!
            .quaternion.angleTo(rig.rest.get(h + "Hand")!) * rad;
        limits.bend = Math.max(limits.bend, bend);
        limits.sideBend = Math.max(limits.sideBend, lateral);
        limits.wristRotation = Math.max(limits.wristRotation, twist);
        limits.footTravel = Math.max(
          limits.footTravel,
          rig.position(h + "Foot").distanceTo(rig.feet[i]),
        );
        if (h === side && frame % 3 === 0)
          handStats.push([
            frame,
            ...[
              bend,
              lateral,
              twist,
              ...wrist.toArray(),
              ...palm.toArray(),
            ].map((x) => +x.toFixed(4)),
          ]);
      }
    }
    const file = name + "-" + side + ".bin";
    writeFileSync(join(out, file), new Uint8Array(matrices.buffer));
    index.push({
      name,
      first,
      second,
      side,
      file,
      count,
      nodes: rig.nodes.length,
      limits,
      handStats,
      uniformContact,
    });
  }
writeFileSync(join(out, "index.json"), JSON.stringify(index));
console.log(index.length, "gesture and interruption paths sampled");
