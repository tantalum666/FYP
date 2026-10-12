export type Gesture = "none" | "nod" | "wave" | "step";
export const MESH_COLUMNS = 96;
export const MESH_ROWS = 192;
export const smooth = (a: number, b: number, n: number) => {
  const t = Math.max(0, Math.min(1, (n - a) / (b - a)));
  return t * t * (3 - 2 * t);
};
const gaussian = (n: number, center: number, radius: number) =>
  Math.exp(-(((n - center) / radius) ** 2));

/** A shallow, continuous sculpted surface. Depth is authored approximation, not a 3D scan. */
export function depthAt(x: number, y: number) {
  return (
    0.014 * gaussian(x, 512, 205) * gaussian(y, 300, 350) +
    0.073 * gaussian(x, 512, 91) * gaussian(y, 159, 100) +
    0.056 * gaussian(x, 512, 116) * gaussian(y, 450, 270) +
    0.038 * gaussian(x, 512, 130) * gaussian(y, 730, 180) +
    0.024 * gaussian(x, 454, 45) * gaussian(y, 1110, 260) +
    0.024 * gaussian(x, 595, 45) * gaussian(y, 1110, 260) +
    0.029 * gaussian(x, 475, 43) * gaussian(y, 1410, 110) +
    0.029 * gaussian(x, 604, 43) * gaussian(y, 1410, 110) +
    0.025 * gaussian(x, 326, 37) * gaussian(y, 643, 170) +
    0.025 * gaussian(x, 713, 37) * gaussian(y, 643, 170)
  );
}

/** Smooth skinning weights keep adjacent vertices connected at neck, elbows and ankles. */
export function weightsAt(x: number, y: number) {
  const leftX = 328 - Math.max(0, y - 520) * 0.05;
  const rightX = 687 + Math.max(0, y - 520) * 0.11;
  const left =
    smooth(490, 635, y) * (1 - smooth(830, 960, y)) * gaussian(x, leftX, 43);
  const right =
    smooth(490, 635, y) * (1 - smooth(830, 960, y)) * gaussian(x, rightX, 43);
  const leg = smooth(945, 1100, y);
  return {
    head: 1 - smooth(225, 380, y),
    left,
    right,
    leftLeg: leg * gaussian(x, 460, 52),
    rightLeg: leg * gaussian(x, 601, 52),
    leftWrist: left * smooth(709, 775, y),
    rightWrist: right * smooth(709, 775, y),
    hair:
      smooth(68, 150, Math.abs(x - 512)) *
      smooth(195, 300, y) *
      (1 - smooth(610, 760, y)),
  };
}

export function gesturePose(
  kind: Gesture,
  elapsed: number,
  side: "left" | "right",
) {
  const progress = Math.max(0, Math.min(1, elapsed / 1.7));
  const envelope = Math.sin(Math.PI * progress) ** 2;
  const wave = envelope * (0.38 + 0.055 * Math.sin(progress * Math.PI * 5));
  return {
    nod: kind === "nod" ? envelope * 0.15 : 0,
    armLeft: kind === "wave" && side === "left" ? wave : 0,
    armRight: kind === "wave" && side === "right" ? -wave : 0,
    wrist:
      kind === "wave" ? envelope * Math.sin(progress * Math.PI * 6) * 0.07 : 0,
    step: kind === "step" ? envelope : 0,
    greet: kind === "wave" ? envelope : 0,
  };
}

export const DEFORM_SHADER = `
attribute vec4 a1Skin;
attribute vec4 a1Detail;
uniform vec3 uA1Head;
uniform vec4 uA1Arms;
uniform vec4 uA1Legs;
uniform float uA1Breath;
uniform float uA1Time;
vec3 a1RotateZ(vec3 p, vec3 pivot, float a) {
  p -= pivot;
  p.xy = mat2(cos(a), sin(a), -sin(a), cos(a)) * p.xy;
  return p + pivot;
}
vec3 a1RotateHead(vec3 p, vec3 pivot, vec3 a) {
  p -= pivot;
  p.yz = mat2(cos(a.x), sin(a.x), -sin(a.x), cos(a.x)) * p.yz;
  p.xz = mat2(cos(a.y), -sin(a.y), sin(a.y), cos(a.y)) * p.xz;
  p.xy = mat2(cos(a.z), sin(a.z), -sin(a.z), cos(a.z)) * p.xy;
  return p + pivot;
}
vec3 a1Deform(vec3 p) {
  p = a1RotateHead(p, vec3(0., .326, .045), uA1Head * a1Skin.x);
  p = a1RotateZ(p, vec3(-.1233, .1736, .024), -uA1Arms.x * a1Skin.y);
  p = a1RotateZ(p, vec3(.1173, .1736, .024), -uA1Arms.y * a1Skin.z);
  p = a1RotateZ(p, vec3(-.1327, .022, .024), -uA1Arms.z * a1Detail.y);
  p = a1RotateZ(p, vec3(.1387, .022, .024), -uA1Arms.w * a1Detail.z);
  p.z += .026 * (abs(uA1Arms.x) * a1Skin.y + abs(uA1Arms.y) * a1Skin.z);
  p = a1RotateZ(p, vec3(-.0382, -.124, .025), uA1Legs.x * a1Skin.w);
  p = a1RotateZ(p, vec3(.054, -.124, .025), uA1Legs.y * a1Detail.x);
  p.y += uA1Legs.z * a1Skin.w * .008;
  p.z += uA1Legs.z * a1Skin.w * .015;
  p.x += a1Detail.w * sin(uA1Time * 1.55 + p.y * 7.) * .0022;
  p.z += a1Detail.w * cos(uA1Time * 1.2 + p.y * 6.) * .002;
  p.y += uA1Breath * smoothstep(-.25, .3, p.y) * .0018;
  return p;
}
`;
