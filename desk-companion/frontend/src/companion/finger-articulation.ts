export type Finger = "Index" | "Middle" | "Ring" | "Little";
type Joints = readonly [number, number, number];
type Profile = {
  rest: Joints;
  open: Joints;
  grip: Joints;
  spread: Joints;
  cup: Joints;
  openRate: number;
  closeRate: number;
};

// Joint angles run from the knuckle to the fingertip. Spread and cup
// describe the relaxed, open and gripping hand respectively, in degrees.
export const fingers: Record<Finger, Profile> = {
  Index: {
    rest: [8, 15, 8],
    open: [2, 5, 2],
    grip: [50, 67, 43],
    spread: [1, 6, -1],
    cup: [0, 0, 0],
    openRate: 14,
    closeRate: 8,
  },
  Middle: {
    rest: [11, 21, 11],
    open: [3, 6, 3],
    grip: [52, 70, 46],
    spread: [0, 0, 0],
    cup: [0, 0, 0],
    openRate: 12,
    closeRate: 10,
  },
  Ring: {
    rest: [15, 27, 14],
    open: [5, 8, 4],
    grip: [54, 71, 48],
    spread: [1.5, 3, 10],
    cup: [4, 1, 6],
    openRate: 10,
    closeRate: 12,
  },
  Little: {
    rest: [17, 31, 16],
    open: [7, 11, 5],
    grip: [55, 72, 49],
    spread: [3, 7, 12],
    cup: [7, 2, 10],
    openRate: 8,
    closeRate: 14,
  },
};

const rad = Math.PI / 180;
export function fingerAngle(
  shape: number,
  rest: number,
  open: number,
  grip: number,
) {
  return (rest + Math.abs(shape) * ((shape >= 0 ? open : grip) - rest)) * rad;
}
export function followHandShape(
  current: number,
  target: number,
  delta: number,
  opening: number,
  closing: number,
) {
  const rate = target > current ? opening : closing;
  return (
    current + (target - current) * (1 - Math.exp(-rate * Math.max(0, delta)))
  );
}
