import Foundation
import Security

enum LocalEndpoint {
    static var isMealQA: Bool {
        #if DEBUG && targetEnvironment(simulator)
        ProcessInfo.processInfo.environment["SENPLATE_QA_ENV"] == "meals"
        #else
        false
        #endif
    }
    static var url: URL { URL(string: isMealQA ? "http://127.0.0.1:8800" : "http://127.0.0.1:8799")! }
}

enum SessionVault {
    static var service: String { "com.group2.senplate.session" + (LocalEndpoint.isMealQA ? ".meals-qa" : "") }
    static func save(_ token: String) throws {
        clear()
        let status = SecItemAdd([kSecClass: kSecClassGenericPassword, kSecAttrService: service,
            kSecAttrAccount: "local", kSecValueData: Data(token.utf8),
            kSecAttrAccessible: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly] as CFDictionary, nil)
        guard status == errSecSuccess else { throw APIError(code: "SESSION_STORAGE_UNAVAILABLE", status: 0) }
    }
    static func load() -> String? {
        var result: CFTypeRef?
        let status = SecItemCopyMatching([kSecClass: kSecClassGenericPassword, kSecAttrService: service,
            kSecAttrAccount: "local", kSecReturnData: true, kSecMatchLimit: kSecMatchLimitOne] as CFDictionary, &result)
        guard status == errSecSuccess, let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }
    static func clear() { SecItemDelete([kSecClass: kSecClassGenericPassword, kSecAttrService: service] as CFDictionary) }
}

final class APIClient {
    let baseURL = LocalEndpoint.url
    let session: URLSession
    var token: String?
    init() {
        let config = URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest = 10
        config.httpShouldSetCookies = false
        config.requestCachePolicy = .reloadIgnoringLocalCacheData
        session = URLSession(configuration: config)
        token = SessionVault.load()
    }
    func request(_ path: String, context: String? = nil, method: String = "GET", body: Data? = nil, key: String? = nil) async throws -> Data {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = method; request.httpBody = body
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token { request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization") }
        if let context { request.setValue(context, forHTTPHeaderField: "X-Context-ID") }
        if let key { request.setValue(key, forHTTPHeaderField: "Idempotency-Key") }
        let data: Data, response: URLResponse
        do { (data, response) = try await session.data(for: request) }
        catch { if Task.isCancelled { throw CancellationError() }; throw APIError(code: "NETWORK", status: 0) }
        guard let http = response as? HTTPURLResponse else { throw APIError(code: "NETWORK", status: 0) }
        guard (200..<300).contains(http.statusCode) else {
            let problem = try? JSONDecoder().decode(APIProblem.self, from: data)
            throw APIError(code: problem?.error.code ?? "NETWORK", status: http.statusCode)
        }
        return data
    }
    func get<T: Decodable>(_ path: String, context: String? = nil) async throws -> T { try decode(await request(path, context: context)) }
    func decode<T: Decodable>(_ data: Data) throws -> T {
        let decoder = JSONDecoder(); decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(T.self, from: data)
    }
    func socket(context: String) -> URLSessionWebSocketTask {
        var url = URLComponents(url: baseURL, resolvingAgainstBaseURL: false)!
        url.scheme = "ws"; url.path = "/v1/events"; url.queryItems = [URLQueryItem(name: "context_id", value: context)]
        var request = URLRequest(url: url.url!)
        if let token { request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization") }
        return session.webSocketTask(with: request)
    }
}
