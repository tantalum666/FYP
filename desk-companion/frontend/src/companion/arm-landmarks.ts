// Normalized left arm offsets from the relaxed VRM pose, in radians.
// These landmarks were fitted on the shipped rig; the other arm mirrors Y and Z.
type Rotation = readonly [number, number, number];
type Arm = {
  upper: Rotation;
  lower: Rotation;
  wrist: Rotation;
  fingers: number;
};

export const armLandmarks = {
  ready: {
    upper: [-0.84, -0.09, 0.16],
    lower: [-0.83, 1.08, -1.12],
    wrist: [-0.83, 0.53, 0.27],
    fingers: 0.12,
  },
  heart: {
    upper: [-1.19, 0.11, -0.2],
    lower: [-1.17, -0.42, -2.28],
    wrist: [1.83, 0.08, 0.83],
    fingers: 0.35,
  },
  offer: {
    upper: [-0.1, -0.14, -0.1],
    lower: [-0.1, -1.53, -0.12],
    wrist: [1.95, 0.08, 0.24],
    fingers: 0.72,
  },
  palm: {
    upper: [-1.14, -0.0, -0.02],
    lower: [-1.14, -1.2, -2.6],
    wrist: [1.95, -0.21, 0.02],
    fingers: 0.75,
  },
  guard: {
    upper: [-0.62, -0.06, 0.12],
    lower: [-0.61, 0.04, -2.06],
    wrist: [0.21, -0.1, -0.56],
    fingers: -0.84,
  },
  pump: {
    upper: [-0.62, -0.23, -0.74],
    lower: [-0.44, -0.1, -2.25],
    wrist: [0.49, 0.32, 0.13],
    fingers: -0.96,
  },
  spread: {
    upper: [-0.56, -0.16, -0.45],
    lower: [-0.51, -0.11, -2.2],
    wrist: [0.53, 0.29, -0.16],
    fingers: 1,
  },
  clapOpen: {
    upper: [-0.8, 0.03, -0.2],
    lower: [-0.79, -0.32, -2.11],
    wrist: [1.05, -0.38, -0.13],
    fingers: 0.91,
  },
  clapTouch: {
    upper: [-1.16, -0.23, -0.44],
    lower: [-1.07, -0.24, -2.0],
    wrist: [0.88, -0.2, -0.44],
    fingers: 0.91,
  },
  cheek: {
    upper: [-1.34, 0.03, -0.83],
    lower: [-0.92, -0.7, -2.55],
    wrist: [1.95, 0.86, 0.4],
    fingers: 0.46,
  },
  fold: {
    upper: [-1.18, 0.23, -0.13],
    lower: [-1.2, -0.54, -1.99],
    wrist: [1.55, -0.1, 1.0],
    fingers: 0.27,
  },
  temple: {
    upper: [-1.05, 0.31, -1.27],
    lower: [-0.5, -0.71, -2.56],
    wrist: [1.95, 0.06, -0.01],
    fingers: 0.28,
  },
  ear: {
    upper: [-0.82, 0.26, -1.26],
    lower: [-0.4, -0.52, -2.6],
    wrist: [1.93, 0.04, -0.34],
    fingers: 0.28,
  },
  cuff: {
    upper: [-0.58, -0.5, -0.15],
    lower: [-0.65, -1.29, -0.12],
    wrist: [-0.43, -0.54, 0.72],
    fingers: -0.18,
  },
  chin: {
    upper: [-1.29, -0.03, -0.48],
    lower: [-1.14, -0.58, -2.53],
    wrist: [1.95, 0.22, 0.52],
    fingers: -0.28,
  },
} satisfies Record<string, Arm>;

export type ArmLandmark = keyof typeof armLandmarks;
