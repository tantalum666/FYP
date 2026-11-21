import { MathUtils, Object3D, Quaternion, Vector3 } from "three";

type ThumbNodes = readonly [Object3D, Object3D, Object3D];
type ThumbPose = readonly [Quaternion, Quaternion, Quaternion];
const position = (node: Object3D) => node.getWorldPosition(new Vector3());
const rotation = (node: Object3D) => node.getWorldQuaternion(new Quaternion());

/** Fit the two thumb segments once. The radial knuckle goes around the
 * index finger, then the pad turns across the palm on a closed hand. */
function fitThumb(
  nodes: ThumbNodes,
  target: Vector3,
  pole: Vector3,
  tipBend: number,
): ThumbPose {
  const [base, mid, tip] = nodes;
  const origin = position(base),
    first = position(mid).sub(origin),
    second = position(tip).sub(position(mid));
  const a = first.length(),
    b = second.length(),
    axis = target.clone().sub(origin);
  const distance = MathUtils.clamp(
    axis.length(),
    Math.abs(a - b) + 1e-6,
    a + b - 1e-6,
  );
  axis.normalize();
  const along = (a * a - b * b + distance * distance) / (2 * distance);
  const outward = pole.clone().sub(origin);
  outward.addScaledVector(axis, -outward.dot(axis)).normalize();
  const newFirst = axis
    .clone()
    .multiplyScalar(along)
    .addScaledVector(outward, Math.sqrt(Math.max(0, a * a - along * along)));
  const newSecond = axis.multiplyScalar(distance).sub(newFirst);
  const swing1 = new Quaternion().setFromUnitVectors(
    first.normalize(),
    newFirst.clone().normalize(),
  );
  const swing2 = new Quaternion().setFromUnitVectors(
    second.normalize().applyQuaternion(swing1),
    newSecond.clone().normalize(),
  );
  const baseWorld = rotation(base),
    midWorld = swing1.clone().multiply(rotation(mid)),
    tipWorld = swing2.clone().multiply(swing1).multiply(rotation(tip));
  const bendAxis = newFirst
    .cross(newSecond)
    .normalize()
    .applyQuaternion(tipWorld.invert());
  return [
    base.quaternion
      .clone()
      .multiply(
        baseWorld.clone().invert().multiply(swing1).multiply(baseWorld),
      ),
    mid.quaternion
      .clone()
      .multiply(midWorld.clone().invert().multiply(swing2).multiply(midWorld)),
    tip.quaternion
      .clone()
      .multiply(new Quaternion().setFromAxisAngle(bendAxis, tipBend)),
  ];
}

export function thumbPoses(
  nodes: ThumbNodes,
  wrist: Vector3,
  middle: Vector3,
  index: Vector3,
  little: Vector3,
  normal: Vector3,
) {
  const forward = middle.clone().sub(wrist),
    length = forward.length();
  forward.normalize();
  const radial = index.clone().sub(little).projectOnPlane(forward),
    span = radial.length();
  radial.normalize();
  const origin = position(nodes[0]);
  const point = (lengths: number, widths: number, depths: number) =>
    origin
      .clone()
      .addScaledVector(forward, length * lengths)
      .addScaledVector(radial, span * widths)
      .addScaledVector(normal, length * depths);
  return {
    rest: fitThumb(
      nodes,
      point(0.97, 0.41, 0.19),
      point(0.5, 0.77, 0.24),
      0.12,
    ),
    open: [
      nodes[0].quaternion.clone(),
      nodes[1].quaternion.clone(),
      nodes[2].quaternion.clone(),
    ] as ThumbPose,
    clear: fitThumb(
      nodes,
      point(0.7, 0.78, 0.45),
      point(0.4, 1.12, 0.46),
      0.14,
    ),
    grip: fitThumb(
      nodes,
      point(0.5, 0.065, 0.643),
      point(0.42, 1.08, 0.55),
      0.16,
    ),
  };
}
