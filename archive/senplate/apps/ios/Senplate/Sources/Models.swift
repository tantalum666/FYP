import Foundation

struct WorkspaceContext: Codable, Identifiable, Hashable {
    let id: String
    let name: String
    let nameEn: String
    let role: String
    var canWrite: Bool { role == "staff" || role == "manager" }
}
struct AppUser: Codable {
    let id: String
    let name: String
    let username: String
    let contexts: [WorkspaceContext]
}
struct Overview: Decodable {
    let stationCount: Int
    let pendingCount: Int
    let activeTaskCount: Int
    let station: Station
}
struct Station: Decodable {
    let mode: String
    let stationId: String
    let sessionId: String
    let foodName: String
    let foodNameEn: String
    let dataOrigin: String
    let clockAt: String
    let observedAt: String?
    let lastValidAt: String?
    let connectivity: String
    let freshness: String
    let measurementStatus: String
    let visionStatus: String
    let foodBinding: String
    let netG: Int?
    let lastValidG: Int?
    let incomingG: Int
    let reservedG: Int
    let availableToPromiseG: Int?
    let availability: String
    let thresholdG: Int
    let batchG: Int
    let suggestionReason: String
    let paused: Bool
    let recommendation: Recommendation?
    let tasks: [KitchenTask]
    let history: [WeightPoint]
    let events: [FoodEvent]
    var reliable: Bool { connectivity == "online" && freshness == "fresh" && measurementStatus == "valid" && !paused }
}
struct Recommendation: Decodable, Identifiable {
    let id: String
    let version: Int
    let amountG: Int
    let basisG: Int
    let expiresAt: String
}
struct KitchenTask: Decodable, Identifiable {
    let id: String
    let state: String
    let version: Int
    let plannedG: Int
    let actualAddedG: Int?
    let assigneeId: String?
    let assigneeName: String?
    let note: String
    let eligibleEvents: [FoodEvent]
    var active: Bool { !["completed", "closed_unverified", "cancelled"].contains(state) }
}
struct WeightPoint: Decodable, Identifiable {
    let id: String
    let at: String
    let netG: Int?
}
struct FoodEvent: Decodable, Identifiable {
    let id: String
    let kind: String
    let at: String
    let deltaG: Int?
    let netG: Int?
    let dataOrigin: String
}
struct PendingOperation: Codable {
    let id: String
    let path: String
    let body: Data
    var actorId: String? = nil
    var contextId: String? = nil
}
struct AuthResponse: Decodable { let accessToken: String }
struct APIProblem: Decodable { struct Detail: Decodable { let code: String }; let error: Detail }
struct APIError: Error { let code: String; let status: Int }

enum Format {
    static func grams(_ value: Int?) -> String { value.map { $0.formatted(.number.locale(Locale(identifier: "en"))) } ?? "—" }
    static func date(_ value: String?) -> Date? {
        guard let value else { return nil }
        let fractional = ISO8601DateFormatter(); fractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return fractional.date(from: value) ?? ISO8601DateFormatter().date(from: value)
    }
    static func time(_ value: String?) -> String {
        guard let date = date(value) else { return "—" }
        let formatter = DateFormatter(); formatter.locale = Locale(identifier: "en_GB")
        formatter.dateFormat = "HH:mm"; formatter.timeZone = TimeZone(identifier: "Asia/Hong_Kong")
        return formatter.string(from: date)
    }
}
