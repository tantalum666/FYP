const KEY = "desk.microphone.v1";
let sessionSelection = "";

export function selectedMicrophone(): string {
  try {
    sessionSelection = localStorage.getItem(KEY) ?? "";
    return sessionSelection;
  } catch {
    return sessionSelection;
  }
}

export function selectMicrophone(deviceId: string) {
  sessionSelection = deviceId;
  try {
    if (deviceId) localStorage.setItem(KEY, deviceId);
    else localStorage.removeItem(KEY);
  } catch {
    // Keep the explicit input for this page even if it cannot be persisted.
  }
}

/** Local preview, keyword listening and conversation use the same input. */
export function microphoneConstraints(): MediaTrackConstraints {
  const deviceId = selectedMicrophone();
  return {
    channelCount: 1,
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true,
    ...(deviceId ? { deviceId: { exact: deviceId } } : {}),
  };
}
