import Foundation
import Observation

struct FoodReference: Decodable, Identifiable {
    let id: String
    let slug: String
    let nameEn: String
    let nameZh: String
    let foodGroup: String
    let cookedState: String
    let notesEn: String
    let notesZh: String
    let source: String
    let sourceId: String?
    let sourceDescription: String
    let sourceType: String
    let sourceUrl: String?
    let publishedAt: String?
    let dataVersion: String
}
struct FoodReferences: Decodable { let items: [FoodReference] }
struct NutrientValues: Decodable {
    let energyKcal: Double?
    let proteinG: Double?
    let carbohydrateG: Double?
    let fatG: Double?
    let fibreG: Double?
    var rows: [(String, Double?, String)] {
        [("energy_kcal", energyKcal, "kcal"), ("protein_g", proteinG, "g"),
         ("carbohydrate_g", carbohydrateG, "g"), ("fat_g", fatG, "g"), ("fibre_g", fibreG, "g")]
    }
}
struct MealNutrition: Decodable {
    let status: String
    let total: NutrientValues
    let knownSubtotal: NutrientValues
}
struct MealMeasurement: Decodable {
    let netG: Int?
    let lastValidG: Int?
    let observationId: String?
    let observedAt: String?
    let lastValidAt: String?
    let connectivity: String
    let freshness: String
    let measurementStatus: String
    let snapshotVersion: Int
}
struct MealPrepared: Decodable {
    let reference: FoodReference
    let baselineG: Int
    let candidateG: Int?
    let validationError: String?
}
struct MealPortion: Decodable, Identifiable {
    let id: String
    let amountG: Int
    let reference: FoodReference
    let referenceId: String
    let entrySource: String
    let version: Int
    let at: String
}
struct MealHistory: Decodable, Identifiable {
    let id: String
    let action: String
    let at: String
    let note: String
}
struct MealRecord: Decodable, Identifiable {
    let id: String
    let runId: String
    let workspaceId: String
    let mode: String
    let state: String
    let version: Int
    let sampleCode: String?
    let createdAt: String
    let updatedAt: String
    let completedAt: String?
    let dataOrigin: String
    let current: MealMeasurement?
    let prepared: MealPrepared?
    let providedG: Int
    let remainingG: Int?
    let remainingReason: String?
    let remainingComparable: Bool
    let nutrition: MealNutrition
    let foodGroupsG: [String: Int]
    let portions: [MealPortion]
    let history: [MealHistory]
    var active: Bool { ["setup", "pairing", "recording", "observing"].contains(state) }
}
struct MealList: Decodable { let items: [MealRecord] }
struct MealPairRequest: Decodable, Identifiable {
    let id: String
    let state: String
    let checkCode: String
    let expiresAt: String
    let mealId: String?
}
struct MealPairList: Decodable { let items: [MealPairRequest] }
@MainActor @Observable final class MealsState {
    var records: [MealRecord] = []
    var requests: [MealPairRequest] = []
    var references: [FoodReference] = []
    var pendingPairCode: String?
    var pairError = ""
    var loadingReferences = false
    func clearRecords() { records = []; requests = []; references = []; pairError = ""; loadingReferences = false }
}
extension Format {
    static func nutrient(_ value: Double?) -> String {
        value.map { $0.formatted(.number.precision(.fractionLength(0...2)).locale(Locale(identifier: "en"))) } ?? "—"
    }
    static func mealDate(_ value: String) -> String {
        guard let date = date(value) else { return "—" }
        let chinese = UserDefaults.standard.string(forKey: "senplate.language") == "zh-Hans"
        let formatter = DateFormatter(); formatter.locale = Locale(identifier: chinese ? "zh_CN" : "en_GB"); formatter.dateFormat = chinese ? "M月d日 · HH:mm" : "d MMM · HH:mm"; formatter.timeZone = TimeZone(identifier: "Asia/Hong_Kong")
        return formatter.string(from: date)
    }
}
