import type { ArmLandmark } from "./arm-landmarks.ts";
import type { Delivery } from "./delivery.ts";

export type Face = Exclude<Delivery, "neutral">;
export type ArmKey = readonly [seconds: number, pose: ArmLandmark | "rest"];
// Forward bend, head turn, head tilt and independent nod, in radians.
export type BodyKey = readonly [
  seconds: number,
  bend: number,
  turn: number,
  tilt: number,
  nod: number,
];
export interface Performance {
  duration: number;
  face: Face;
  primary: readonly ArmKey[];
  other?: readonly ArmKey[] | "mirror";
  body: readonly BodyKey[];
  wink?: boolean;
  faceStrength?: number;
}
const start = [0, 0, 0, 0, 0] as const;
const rest = [0, "rest"] as const;

export const performances = {
  hairTuck: {
    duration: 5.95,
    face: "appreciate",
    faceStrength: 0.32,
    primary: [
      rest,
      [1.45, "temple"],
      [2.45, "ear"],
      [2.95, "ear"],
      [4.82, "rest"],
    ],
    body: [
      start,
      [1.2, -0.025, -0.12, 0.15, -0.035],
      [2.47, 0.025, -0.2, 0.17, 0.04],
      [3.6, 0.02, 0.065, -0.05, 0.025],
      [5.2, 0, 0, 0, 0],
    ],
  },
  sleeveAdjust: {
    duration: 6.35,
    face: "curious",
    faceStrength: 0.27,
    primary: [
      rest,
      [1.04, "ready"],
      [1.95, "cuff"],
      [2.39, "cuff"],
      [2.95, "ready"],
      [3.57, "cuff"],
      [4.13, "cuff"],
      [5.5, "rest"],
    ],
    other: [rest, [1.18, "ready"], [4.42, "ready"], [5.63, "rest"]],
    body: [
      start,
      [1.12, 0.07, -0.12, -0.09, 0.15],
      [2.06, 0.14, -0.17, -0.11, 0.22],
      [3.68, 0.11, -0.12, -0.08, 0.19],
      [4.66, -0.031, 0.065, 0.035, -0.045],
      [5.8, 0, 0, 0, 0],
    ],
  },
  applause: {
    duration: 6.15,
    face: "celebrate",
    primary: [
      rest,
      [0.98, "clapOpen"],
      [1.45, "clapTouch"],
      [1.84, "clapOpen"],
      [2.21, "clapTouch"],
      [2.67, "clapOpen"],
      [3.07, "clapTouch"],
      [3.65, "clapOpen"],
      [4.35, "ready"],
      [5.4, "rest"],
    ],
    other: "mirror",
    body: [
      start,
      [0.55, -0.1, -0.065, -0.055, -0.08],
      [1.4, 0.09, 0.04, 0.045, 0.065],
      [2.15, 0.03, -0.04, -0.035, -0.025],
      [3.05, 0.1, 0.075, 0.055, 0.06],
      [4.45, -0.035, 0.035, 0.025, -0.045],
      [5.65, 0, 0, 0, 0],
    ],
  },
  victory: {
    duration: 5.9,
    face: "celebrate",
    primary: [
      rest,
      [0.8, "guard"],
      [1.42, "pump"],
      [2.05, "guard"],
      [2.62, "pump"],
      [3.38, "guard"],
      [4.95, "rest"],
    ],
    other: [
      rest,
      [0.94, "guard"],
      [1.65, "pump"],
      [2.34, "guard"],
      [3.1, "guard"],
      [4.65, "rest"],
    ],
    body: [
      start,
      [0.55, 0.11, -0.08, -0.08, 0.09],
      [1.43, -0.17, 0.09, 0.13, -0.1],
      [2.0, 0.085, -0.06, -0.07, 0.06],
      [2.64, -0.11, 0.1, 0.1, -0.075],
      [4.95, 0, 0, 0, 0],
    ],
  },
  comfort: {
    duration: 7.35,
    face: "comfort",
    primary: [
      rest,
      [1.3, "heart"],
      [2.5, "heart"],
      [3.77, "offer"],
      [4.93, "offer"],
      [6.55, "rest"],
    ],
    body: [
      start,
      [1.05, 0.105, -0.07, -0.145, 0.055],
      [2.1, 0.17, -0.11, -0.19, 0.14],
      [3.5, 0.11, 0.035, -0.1, -0.035],
      [4.72, 0.12, 0.035, -0.085, 0.055],
      [6.82, 0, 0, 0, 0],
    ],
  },
  gratefulBow: {
    duration: 6.1,
    face: "appreciate",
    primary: [rest, [1.05, "heart"], [3.54, "heart"], [5.16, "rest"]],
    other: [
      rest,
      [1.14, "ready"],
      [2.08, "fold"],
      [3.4, "fold"],
      [4.88, "rest"],
    ],
    body: [
      start,
      [0.62, -0.035, 0.07, 0.07, -0.035],
      [1.98, 0.31, 0, -0.04, 0.24],
      [2.48, 0.29, 0, -0.045, 0.18],
      [3.72, -0.045, -0.11, -0.095, -0.06],
      [5.3, 0, 0, 0, 0],
    ],
  },
  handToHeart: {
    duration: 5.65,
    face: "appreciate",
    primary: [
      rest,
      [1.1, "heart"],
      [2.6, "heart"],
      [3.62, "palm"],
      [4.92, "rest"],
    ],
    body: [
      start,
      [0.95, 0.075, 0.13, 0.16, 0.075],
      [2, 0.12, 0.09, 0.095, 0.105],
      [3.4, -0.03, -0.06, -0.075, -0.06],
      [5.12, 0, 0, 0, 0],
    ],
  },
  astonished: {
    duration: 5.3,
    face: "surprised",
    primary: [
      rest,
      [0.82, "spread"],
      [1.68, "spread"],
      [2.72, "palm"],
      [4.4, "rest"],
    ],
    other: [
      rest,
      [1.01, "spread"],
      [1.75, "spread"],
      [2.58, "guard"],
      [4.15, "rest"],
    ],
    body: [
      start,
      [0.53, -0.19, -0.11, -0.11, -0.17],
      [1.33, -0.1, 0.055, 0.075, -0.07],
      [2.45, 0.12, 0.1, 0.12, 0.06],
      [4.42, 0, 0, 0, 0],
    ],
  },
  giggle: {
    duration: 5.8,
    face: "amused",
    primary: [rest, [1.12, "cheek"], [3.3, "cheek"], [4.95, "rest"]],
    other: [rest, [1.48, "ready"], [3.35, "ready"], [4.55, "rest"]],
    body: [
      start,
      [0.72, 0.09, -0.14, -0.12, 0.06],
      [1.22, 0.16, -0.17, -0.16, 0.15],
      [1.71, 0.035, -0.12, -0.12, -0.055],
      [2.08, 0.14, -0.14, -0.14, 0.11],
      [2.56, 0.032, -0.08, -0.07, -0.04],
      [3.02, 0.095, -0.06, -0.065, 0.065],
      [4.94, 0, 0, 0, 0],
    ],
  },
  wink: {
    duration: 4.9,
    face: "amused",
    wink: true,
    primary: [
      rest,
      [1.15, "spread"],
      [1.8, "spread"],
      [2.58, "guard"],
      [4, "rest"],
    ],
    body: [
      start,
      [1.1, -0.035, 0.12, 0.2, -0.055],
      [1.83, 0.045, 0.17, 0.22, 0.065],
      [2.74, -0.055, -0.06, -0.05, -0.055],
      [4.2, 0, 0, 0, 0],
    ],
  },
  openQuestion: {
    duration: 5.8,
    face: "curious",
    primary: [
      rest,
      [1.21, "palm"],
      [2.27, "palm"],
      [3.25, "offer"],
      [4.96, "rest"],
    ],
    body: [
      start,
      [0.82, 0.07, -0.15, 0.18, -0.07],
      [1.72, 0.12, -0.1, 0.22, 0.045],
      [3, 0.09, 0.11, -0.12, -0.06],
      [5, 0, 0, 0, 0],
    ],
  },
  chinRest: {
    duration: 5.95,
    face: "curious",
    primary: [rest, [1.27, "chin"], [3.37, "chin"], [5.06, "rest"]],
    body: [
      start,
      [1.03, -0.065, 0.21, -0.11, -0.1],
      [2.3, 0.045, 0.26, -0.15, 0.035],
      [3.65, 0.095, -0.085, 0.075, 0.062],
      [5.2, 0, 0, 0, 0],
    ],
  },
  fistPump: {
    duration: 5.35,
    face: "encourage",
    primary: [
      rest,
      [0.99, "guard"],
      [1.63, "pump"],
      [2.36, "guard"],
      [3.15, "guard"],
      [4.55, "rest"],
    ],
    body: [
      start,
      [0.72, 0.11, -0.09, -0.07, 0.09],
      [1.61, -0.115, 0.12, 0.11, -0.08],
      [2.44, 0.13, 0.035, -0.065, 0.095],
      [3.34, 0.075, -0.055, -0.04, 0.035],
      [4.7, 0, 0, 0, 0],
    ],
  },
} as const satisfies Record<string, Performance>;

export type PerformanceName = keyof typeof performances;
export const performanceDurations = Object.fromEntries(
  Object.entries(performances).map(([name, score]) => [name, score.duration]),
) as Record<PerformanceName, number>;
export const deliveryPerformances: Record<Face, readonly PerformanceName[]> = {
  celebrate: ["applause", "victory"],
  comfort: ["comfort"],
  appreciate: ["gratefulBow", "handToHeart"],
  surprised: ["astonished"],
  amused: ["giggle", "wink"],
  curious: ["openQuestion", "chinRest"],
  encourage: ["fistPump"],
};
