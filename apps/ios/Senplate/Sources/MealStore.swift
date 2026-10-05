import Foundation

extension AppStore {
    func applyPairing(_ raw: String) async -> Bool {
        guard let code = PairCode.parse(raw) else { meals.pairError = "INVALID_PAIR_CODE"; return false }
        guard contextId == "personal" else { return false }
        meals.pairError = ""
        return await mutate("/v1/pairing/requests", values: ["code": code])
    }
    func loadFoodReferences() async {
        guard let actor = user?.id, contextId == "personal" else { return }
        meals.loadingReferences = true
        defer { meals.loadingReferences = false }
        do {
            let result: FoodReferences = try await api.get("/v1/food-references")
            guard user?.id == actor, contextId == "personal" else { return }
            meals.references = result.items
        } catch { if user?.id == actor, contextId == "personal" { handle(error) } }
    }
    func mealAction(_ meal: MealRecord, _ action: String, referenceId: String? = nil, portionId: String? = nil, note: String = "", remainingReason: String? = nil) async -> Bool {
        var values: [String: Any] = ["action": action, "expected_version": meal.version, "note": note]
        if let referenceId { values["reference_id"] = referenceId }
        if let portionId { values["portion_id"] = portionId }
        if let remainingReason { values["remaining_reason"] = remainingReason }
        else if ["prepare_portion", "confirm_portion", "cancel_portion", "finish_plating", "complete"].contains(action), let observation = meal.current?.observationId { values["observation_id"] = observation }
        return await mutate("/v1/meals/\(meal.id)/actions", values: values)
    }
    func handleAppLink(_ url: URL) {
        if let code = PairCode.parse(url.absoluteString) {
            dining.pendingMenuCode = nil; meals.pendingPairCode = code
            if user != nil, !busy { selectContext("personal") }
        } else { meals.pendingPairCode = nil; handleMenuLink(url) }
    }
}
