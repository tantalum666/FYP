import UIKit
import Capacitor

@UIApplicationMain
class AppDelegate: UIResponder, UIApplicationDelegate {

    var window: UIWindow?

    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        // Override point for customization after application launch.
        return true
    }

    func applicationWillResignActive(_ application: UIApplication) {
        // Sent when the application is about to move from active to inactive state. This can occur for certain types of temporary interruptions (such as an incoming phone call or SMS message) or when the user quits the application and it begins the transition to the background state.
        // Use this method to pause ongoing tasks, disable timers, and invalidate graphics rendering callbacks. Games should use this method to pause the game.
    }

    func applicationDidEnterBackground(_ application: UIApplication) {
        // Use this method to release shared resources, save user data, invalidate timers, and store enough application state information to restore your application to its current state in case it is terminated later.
        // If your application supports background execution, this method is called instead of applicationWillTerminate: when the user quits.
    }

    func applicationWillEnterForeground(_ application: UIApplication) {
        // Called as part of the transition from the background to the active state; here you can undo many of the changes made on entering the background.
    }

    func applicationDidBecomeActive(_ application: UIApplication) {
        // Restart any tasks that were paused (or not yet started) while the application was inactive. If the application was previously in the background, optionally refresh the user interface.
    }

    func applicationWillTerminate(_ application: UIApplication) {
        // Called when the application is about to terminate. Save data if appropriate. See also applicationDidEnterBackground:.
    }

    func application(_ application: UIApplication,
                     configurationForConnecting connectingSceneSession: UISceneSession,
                     options: UIScene.ConnectionOptions) -> UISceneConfiguration {
        let config = UISceneConfiguration(name: "Default Configuration",
                                          sessionRole: connectingSceneSession.role)
        config.delegateClass = SceneDelegate.self
        return config
    }
}

import Security

class DeskViewController: CAPBridgeViewController {
    override func capacitorDidLoad() { bridge?.registerPluginInstance(DeskNativePlugin()) }
}

@objc(DeskNativePlugin)
class DeskNativePlugin: CAPPlugin, CAPBridgedPlugin, URLSessionTaskDelegate {
    let identifier = "DeskNativePlugin"
    let jsName = "DeskNative"
    let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "configuration", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "configure", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "request", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "exportFile", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "phoneStatus", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "enableNotifications", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "syncPhone", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "clearPhone", returnType: CAPPluginReturnPromise)
    ]
    override func load() {
        NotificationCenter.default.addObserver(self, selector: #selector(routeRequested), name: Notification.Name("DeskRouteRequested"), object: nil)
        NotificationCenter.default.addObserver(self, selector: #selector(routeRequested), name: UIApplication.didBecomeActiveNotification, object: nil)
    }
    @objc private func routeRequested() {
        guard let route = UserDefaults.standard.string(forKey: "desk.pending.route.v1") else { return }
        notifyListeners("route", data: ["route": route], retainUntilConsumed: true)
        UserDefaults.standard.removeObject(forKey: "desk.pending.route.v1")
    }
    private let originKey = "desk.server.origin.v1"
    private lazy var session: URLSession = {
        let config = URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest = 12
        config.timeoutIntervalForResource = 20
        return URLSession(configuration: config, delegate: self, delegateQueue: nil)
    }()
    private var origin: String { UserDefaults.standard.string(forKey: originKey) ?? "" }
    private func query(_ origin: String) -> [String: Any] {
        [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: "dev.group2.deskcompanion.pairing", kSecAttrAccount as String: origin]
    }
    private func token(_ origin: String) -> String? {
        var q = query(origin); q[kSecReturnData as String] = true
        var item: CFTypeRef?
        guard SecItemCopyMatching(q as CFDictionary, &item) == errSecSuccess, let data = item as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }
    private func saveToken(_ value: String?, origin: String) -> Bool {
        let q = query(origin); SecItemDelete(q as CFDictionary)
        guard let value else { return true }
        var entry = q
        entry[kSecValueData as String] = value.data(using: .utf8)!
        entry[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        return SecItemAdd(entry as CFDictionary, nil) == errSecSuccess
    }
    @objc func configuration(_ call: CAPPluginCall) {
        let route = UserDefaults.standard.string(forKey: "desk.pending.route.v1") ?? ""
        UserDefaults.standard.removeObject(forKey: "desk.pending.route.v1")
        call.resolve(["origin": origin, "paired": token(origin) != nil, "route": route])
    }
    @objc func configure(_ call: CAPPluginCall) {
        let value = (call.getString("origin") ?? "").trimmingCharacters(in: .whitespacesAndNewlines).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        guard let parts = URLComponents(string: value), let host = parts.host, parts.user == nil, parts.password == nil, parts.query == nil, parts.fragment == nil, parts.path.isEmpty else { call.reject("Use a server origin without a path"); return }
        var allowed = parts.scheme == "https"
        #if targetEnvironment(simulator)
        allowed = allowed || (parts.scheme == "http" && ["127.0.0.1", "localhost"].contains(host))
        #endif
        guard allowed else { call.reject("A trusted HTTPS address is required"); return }
        if value != origin {
            DeskPhoneFeatures.clear()
            _ = saveToken(nil, origin: origin)
            session.configuration.httpCookieStorage?.removeCookies(since: .distantPast)
        }
        UserDefaults.standard.set(value, forKey: originKey)
        call.resolve(["origin": value])
    }
    @objc func request(_ call: CAPPluginCall) {
        let server = origin
        let path = call.getString("path") ?? ""
        let method = call.getString("method") ?? "GET"
        guard !server.isEmpty, path.hasPrefix("/"), !path.hasPrefix("//"), !path.contains(".."), !path.contains("://"), ["GET", "POST", "DELETE"].contains(method), let url = URL(string: server + "/api" + path) else { call.reject("Invalid desk request"); return }
        var request = URLRequest(url: url); request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("1", forHTTPHeaderField: "X-Desk-Request")
        request.setValue("1", forHTTPHeaderField: "X-Desk-Native")
        if let token = token(server) { request.setValue("Bearer " + token, forHTTPHeaderField: "Authorization") }
        for (name, value) in call.getObject("headers") ?? [:] {
            if ["x-operation-id", "x-desk-share"].contains(name.lowercased()), let value = value as? String { request.setValue(value, forHTTPHeaderField: name) }
        }
        if let body = call.getString("body") {
            guard body.utf8.count <= 5_000_000 else { call.reject("Request too large"); return }
            request.httpBody = body.data(using: .utf8)
        }
        session.dataTask(with: request) { [weak self] data, response, error in
            guard let self, let data, let response = response as? HTTPURLResponse, error == nil, data.count <= 8_000_000 else { call.reject("Desk connection failed"); return }
            if response.statusCode == 401 && method == "GET" { DeskPhoneFeatures.clear() }
            var returnedData = data
            if path == "/pairing/claim", response.statusCode == 200, var object = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any], let token = object.removeValue(forKey: "token") as? String {
                guard self.origin == server, self.saveToken(token, origin: server) else { call.reject("Pairing could not be saved to Keychain"); return }
                returnedData = (try? JSONSerialization.data(withJSONObject: object)) ?? data
            }
            if path == "/session", method == "DELETE", response.statusCode == 200 { _ = self.saveToken(nil, origin: server); DeskPhoneFeatures.clear() }
            call.resolve(["status": response.statusCode, "bodyBase64": returnedData.base64EncodedString(), "contentType": response.value(forHTTPHeaderField: "Content-Type") ?? "application/json"])
        }.resume()
    }
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
        // Never forward the paired identity to an arbitrary redirected destination.
        completionHandler(nil)
    }
    @objc func exportFile(_ call: CAPPluginCall) {
        guard let encoded = call.getString("bodyBase64"), encoded.count <= 12_000_000, let data = Data(base64Encoded: encoded) else { call.reject("Invalid export"); return }
        let supplied = call.getString("filename") ?? "desk-export.json"
        guard !supplied.contains("/"), !supplied.contains("\\"), supplied.count <= 100 else { call.reject("Invalid filename"); return }
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        do {
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            let file = directory.appendingPathComponent(supplied)
            try data.write(to: file, options: [.atomic, .completeFileProtection])
            DispatchQueue.main.async {
                let controller = UIActivityViewController(activityItems: [file], applicationActivities: nil)
                controller.popoverPresentationController?.sourceView = self.bridge?.viewController?.view
                controller.completionWithItemsHandler = { _, completed, _, _ in
                    try? FileManager.default.removeItem(at: directory)
                    call.resolve(["shared": completed])
                }
                self.bridge?.viewController?.present(controller, animated: true)
            }
        } catch { call.reject("Could not prepare the export") }
    }
}
