import SwiftUI
import AVFoundation

struct MenuScannerView: View {
    @Environment(Preferences.self) private var prefs
    @Environment(\.dismiss) private var dismiss
    let onCode: (String) -> Void
    var pairing = false
    init(pairing: Bool = false, onCode: @escaping (String) -> Void) { self.pairing = pairing; self.onCode = onCode }
    @State private var unavailable = false
    var body: some View {
        VStack(spacing: 22) {
            if unavailable {
                EmptyPanel(title: prefs.text("Camera unavailable", "相机暂不可用"), message: prefs.text("Allow camera access in Settings, or return and enter the code manually.", "可在系统设置中允许相机权限，或返回手动输入代码。"))
                Button(prefs.text("Enter code instead", "改为输入代码")) { dismiss() }.buttonStyle(PrimaryButtonStyle())
            } else {
                ScannerCamera(onCode: onCode, onUnavailable: { unavailable = true })
                    .frame(height: 340).clipShape(RoundedRectangle(cornerRadius: 16))
                    .overlay { Image(systemName: "viewfinder").font(.system(size: 160, weight: .ultraLight)).foregroundStyle(.white.opacity(0.7)).accessibilityHidden(true) }
                Text(pairing ? prefs.text("Point the camera at the station's meal pairing QR code.", "将镜头对准设备的餐食配对二维码。") : prefs.text("Point the camera at a Senplate menu QR code.", "将镜头对准 Senplate 菜单二维码。"))
                    .font(Theme.font(16)).multilineTextAlignment(.center)
            }
            Spacer(minLength: 0)
        }.padding(20).background(Theme.ivory).navigationTitle(pairing ? prefs.text("Scan pairing code", "扫描配对码") : prefs.text("Scan menu", "扫描菜单")).navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button(prefs.text("Cancel", "取消")) { dismiss() } } }
    }
}

private struct ScannerCamera: UIViewControllerRepresentable {
    let onCode: (String) -> Void
    let onUnavailable: () -> Void
    func makeUIViewController(context: Context) -> ScannerController { ScannerController(onCode: onCode, onUnavailable: onUnavailable) }
    func updateUIViewController(_ controller: ScannerController, context: Context) { }
    static func dismantleUIViewController(_ controller: ScannerController, coordinator: ()) { controller.stop() }
}

private final class CameraEngine {
    let session = AVCaptureSession()
    private let queue = DispatchQueue(label: "com.group2.senplate.qr-camera")
    private var wanted = false
    private var configured = false
    func start(delegate: AVCaptureMetadataOutputObjectsDelegate, unavailable: @escaping () -> Void) {
#if targetEnvironment(simulator)
        DispatchQueue.main.async(execute: unavailable)
#else
        queue.async { [self] in
            wanted = true
            let configure = { [weak self, weak delegate] in
                guard let self, let delegate else { return }
                self.queue.async {
                    guard self.wanted else { return }
                    do {
                        if !self.configured {
                            guard let camera = AVCaptureDevice.default(for: .video) else { throw CameraFailure.unavailable }
                            let input = try AVCaptureDeviceInput(device: camera), output = AVCaptureMetadataOutput()
                            self.session.beginConfiguration()
                            defer { self.session.commitConfiguration() }
                            guard self.session.canAddInput(input) else { throw CameraFailure.unavailable }
                            self.session.addInput(input)
                            guard self.session.canAddOutput(output) else { self.session.removeInput(input); throw CameraFailure.unavailable }
                            self.session.addOutput(output)
                            guard output.availableMetadataObjectTypes.contains(.qr) else {
                                self.session.removeInput(input); self.session.removeOutput(output); throw CameraFailure.unavailable
                            }
                            output.setMetadataObjectsDelegate(delegate, queue: .main)
                            output.metadataObjectTypes = [.qr]
                            self.configured = true
                        }
                        if !self.session.isRunning { self.session.startRunning() }
                    } catch { DispatchQueue.main.async(execute: unavailable) }
                }
            }
            switch AVCaptureDevice.authorizationStatus(for: .video) {
            case .authorized: configure()
            case .notDetermined: AVCaptureDevice.requestAccess(for: .video) { allowed in if allowed { configure() } else { DispatchQueue.main.async(execute: unavailable) } }
            default: DispatchQueue.main.async(execute: unavailable)
            }
        }
#endif
    }
    func stop() { queue.async { [self] in wanted = false; if session.isRunning { session.stopRunning() } } }
    private enum CameraFailure: Error { case unavailable }
}

private final class ScannerController: UIViewController, AVCaptureMetadataOutputObjectsDelegate {
    private let engine = CameraEngine()
    private var preview: AVCaptureVideoPreviewLayer?
    private let onCode: (String) -> Void
    private let onUnavailable: () -> Void
    private var delivered = false
    init(onCode: @escaping (String) -> Void, onUnavailable: @escaping () -> Void) {
        self.onCode = onCode; self.onUnavailable = onUnavailable
        super.init(nibName: nil, bundle: nil)
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) is not supported") }
    override func viewDidLoad() {
        super.viewDidLoad(); view.backgroundColor = .black
        let layer = AVCaptureVideoPreviewLayer(session: engine.session); layer.videoGravity = .resizeAspectFill
        view.layer.addSublayer(layer); preview = layer
        NotificationCenter.default.addObserver(self, selector: #selector(stop), name: UIApplication.didEnterBackgroundNotification, object: nil)
        NotificationCenter.default.addObserver(self, selector: #selector(resume), name: UIApplication.willEnterForegroundNotification, object: nil)
    }
    override func viewDidLayoutSubviews() { super.viewDidLayoutSubviews(); preview?.frame = view.bounds }
    override func viewDidAppear(_ animated: Bool) { super.viewDidAppear(animated); resume() }
    override func viewWillDisappear(_ animated: Bool) { super.viewWillDisappear(animated); stop() }
    @objc private func resume() { if view.window != nil && !delivered { engine.start(delegate: self, unavailable: onUnavailable) } }
    @objc func stop() { engine.stop() }
    deinit { NotificationCenter.default.removeObserver(self); engine.stop() }
    func metadataOutput(_ output: AVCaptureMetadataOutput, didOutput objects: [AVMetadataObject], from connection: AVCaptureConnection) {
        guard !delivered, let value = objects.compactMap({ ($0 as? AVMetadataMachineReadableCodeObject)?.stringValue }).first else { return }
        delivered = true; stop(); onCode(value)
    }
}
