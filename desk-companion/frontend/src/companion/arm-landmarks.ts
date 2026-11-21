// Angles in degrees on the normalized left arm. The right side mirrors the pose.
// Elbow flexion and forearm roll are independent; the wrist only bends or deviates.
type Triple = readonly [number, number, number];
type Pair = readonly [number, number];
type Arm = { upper: Triple; elbow: Pair; wrist: Pair; fingers: number };

export const armLandmarks = {
  ready: {
    upper: [-24.9, -2.5, -2.8],
    elbow: [50.3, -86.0],
    wrist: [0.7, 3.3],
    fingers: 0.12,
  },
  heart: {
    upper: [-33.8, 3.8, -25.3],
    elbow: [110.0, -48.2],
    wrist: [38.0, 16.0],
    fingers: 0.32,
  },
  offer: {
    upper: [2.5, -9.2, 5.6],
    elbow: [68.5, -86.0],
    wrist: [15.7, 5.7],
    fingers: 0.72,
  },
  palm: {
    upper: [15.5, -9.6, 7.4],
    elbow: [79.2, -86.0],
    wrist: [-0.4, 1.0],
    fingers: 0.75,
  },
  guard: {
    upper: [7.6, -5.2, -3.5],
    elbow: [100.9, 13.1],
    wrist: [-34.6, 16.0],
    fingers: -0.84,
  },
  pump: {
    upper: [31.0, -22.3, -2.7],
    elbow: [122.2, 62.7],
    wrist: [4.4, -16.0],
    fingers: -0.96,
  },
  spread: {
    upper: [29.2, -13.2, -0.7],
    elbow: [115.0, 52.0],
    wrist: [-15.1, -16.0],
    fingers: 1,
  },
  clapOpen: {
    upper: [0.9, -23.4, -18.9],
    elbow: [105.3, 33.8],
    wrist: [33.1, 7.9],
    fingers: 0.77,
  },
  clapTouch: {
    upper: [-24.07, -20.67, -35.57],
    elbow: [98.99, 9.85],
    wrist: [40.81, -2.19],
    fingers: 0.73,
  },
  clapCatch: {
    upper: [-16.0, -15.0, -1.0],
    elbow: [93.7, -86.0],
    wrist: [18.4, -11.5],
    fingers: 0.7,
  },
  clapRecoil: {
    upper: [-17.0, -14.6, -1.0],
    elbow: [90.1, -86.0],
    wrist: [22.3, -10.4],
    fingers: 0.68,
  },
  cheek: {
    upper: [1.7, -30.7, -11.0],
    elbow: [125.7, -86.0],
    wrist: [16.3, -1.8],
    fingers: -0.55,
  },
  temple: {
    upper: [25.2, -45.6, -10.3],
    elbow: [121.8, -86.0],
    wrist: [0.6, 5.5],
    fingers: 0.28,
  },
  ear: {
    upper: [34.5, -40.9, -6.5],
    elbow: [127.2, -73.8],
    wrist: [-5.1, 9.0],
    fingers: 0.28,
  },
  cuff: {
    upper: [-62.3, -13.8, -27.7],
    elbow: [67.5, 10.8],
    wrist: [0.9, 16.0],
    fingers: -0.18,
  },
  chin: {
    upper: [1.9, -18.3, -4.2],
    elbow: [121.7, -84.3],
    wrist: [17.2, 4.3],
    fingers: -0.28,
  },
} satisfies Record<string, Arm>;

export type ArmLandmark = keyof typeof armLandmarks;
