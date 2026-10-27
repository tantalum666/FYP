(function () {
  const device = new URLSearchParams(location.search).get("surface") === "device";
  const manifest = device ? "/manifest-device.webmanifest" : "/manifest.webmanifest";
  document.write('<link rel="manifest" href="' + manifest + '">');
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js");
    });
  }
})();
