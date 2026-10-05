import Foundation
import Observation

struct DiningMenu: Decodable {
    let workspaceId: String
    let runId: String
    let menuCode: String
    let nameEn: String
    let nameZh: String
    let dataOrigin: String
    let serviceType: String
    let serviceVersion: Int
    let serviceOpen: Bool
    let items: [MenuItem]
}
struct MenuItem: Codable, Identifiable {
    let id: String
    let slug: String
    let nameEn: String
    let nameZh: String
    let descriptionEn: String
    let descriptionZh: String
    let allergensEn: String
    let allergensZh: String
    let priceMinor: Int
    let currency: String
    let version: Int
    let quoteVersion: Int
    let stockSource: String
    let portionG: Int?
    let availablePortions: Int?
    let status: String
    let orderable: Bool
    let serviceType: String
    let updatedAt: String?
    let completedPortions: Int
    let popular: Bool
}
struct FoodOrder: Decodable, Identifiable {
    let id: String
    let number: String
    let workspaceId: String
    let workspaceNameEn: String
    let workspaceNameZh: String
    let runId: String
    let dataOrigin: String
    let state: String
    let version: Int
    let totalMinor: Int
    let currency: String
    let createdAt: String
    let updatedAt: String
    let cancellation: String?
    let note: String
    let assigneeId: String?
    let assigneeName: String?
    let expectedG: Int
    let actualG: Int?
    let reservedG: Int
    let pickupCode: String?
    let lines: [FoodOrderLine]
    let history: [FoodOrderHistory]
    let eligibleEvents: [FoodEvent]
    var active: Bool { ["submitted", "accepted", "preparing", "ready"].contains(state) }
}
struct FoodOrderLine: Decodable, Identifiable {
    let id: String
    let nameEn: String
    let nameZh: String
    let quantity: Int
    let unitPriceMinor: Int
    let stockSource: String
    let portionG: Int?
}
struct FoodOrderHistory: Decodable, Identifiable {
    let id: String
    let action: String
    let at: String
    let note: String
}
struct OrderList: Decodable { let items: [FoodOrder] }
struct OrderReceipt: Decodable { let orderId: String }
struct CartEntry: Codable, Identifiable {
    var item: MenuItem
    var quantity: Int
    var id: String { item.id }
}
struct CartDraft: Codable {
    var runId: String
    var menuCode: String
    var entries: [CartEntry]
    var totalMinor: Int { entries.reduce(0) { $0 + $1.quantity * $1.item.priceMinor } }
    var quantity: Int { entries.reduce(0) { $0 + $1.quantity } }
}
@MainActor @Observable final class DiningState {
    var menu: DiningMenu?
    var ownOrders: [FoodOrder] = []
    var workOrders: [FoodOrder] = []
    var cart: CartDraft?
    var lastMenuCode = ""
    var pendingMenuCode: String?
    var menuError = ""
    func clear() {
        menu = nil; ownOrders = []; workOrders = []; cart = nil; lastMenuCode = ""; menuError = ""
    }
}
extension Format {
    static func money(_ minor: Int, currency: String = "HKD") -> String {
        (Double(minor) / 100).formatted(.currency(code: currency).locale(Locale(identifier: "en_HK")))
    }
}
