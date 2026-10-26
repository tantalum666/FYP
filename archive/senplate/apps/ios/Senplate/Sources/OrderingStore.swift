import Foundation

extension AppStore {
    func restoreDining(for userId: String) {
        dining.clear()
        dining.lastMenuCode = UserDefaults.standard.string(forKey: "senplate.menu.\(userId)") ?? ""
        if let data = UserDefaults.standard.data(forKey: "senplate.cart.\(userId)") {
            dining.cart = try? JSONDecoder().decode(CartDraft.self, from: data)
        }
    }
    func saveCart(for userId: String? = nil) {
        guard let id = userId ?? user?.id else { return }
        if let cart = dining.cart, let data = try? JSONEncoder().encode(cart) {
            UserDefaults.standard.set(data, forKey: "senplate.cart.\(id)")
        } else { UserDefaults.standard.removeObject(forKey: "senplate.cart.\(id)") }
    }
    func openMenu(_ raw: String) async -> DiningMenu? {
        guard let code = MenuCode.parse(raw) else { dining.menuError = "INVALID_MENU_CODE"; return nil }
        guard let actorId = user?.id, contextId == "personal" else { return nil }
        dining.menuError = ""
        do {
            let menu: DiningMenu = try await api.get("/v1/menus/\(code)", context: "personal")
            guard user?.id == actorId, contextId == "personal" else { return nil }
            return menu
        } catch {
            guard user?.id == actorId, contextId == "personal" else { return nil }
            dining.menuError = (error as? APIError)?.code ?? "NETWORK"
            if (error as? APIError)?.status == 401 { handle(error) }
            return nil
        }
    }
    func activateMenu(_ menu: DiningMenu, clearCart: Bool = false) {
        guard let user else { return }
        dining.menu = menu; dining.lastMenuCode = menu.menuCode; dining.pendingMenuCode = nil
        UserDefaults.standard.set(menu.menuCode, forKey: "senplate.menu.\(user.id)")
        if clearCart { dining.cart = nil; saveCart() }
    }
    func addToCart(_ item: MenuItem, quantity: Int) -> Bool {
        guard let menu = dining.menu, item.orderable, contextId == "personal" else { return false }
        if let cart = dining.cart, !cart.entries.isEmpty, cart.runId != menu.runId { return false }
        var cart = dining.cart ?? CartDraft(runId: menu.runId, menuCode: menu.menuCode, entries: [])
        if let index = cart.entries.firstIndex(where: { $0.id == item.id }) {
            cart.entries[index].quantity = min(20, cart.entries[index].quantity + quantity)
        } else { cart.entries.append(CartEntry(item: item, quantity: min(20, max(1, quantity)))) }
        dining.cart = cart
        saveCart(); return true
    }
    func cartQuantity(_ id: String, quantity: Int) {
        guard let index = dining.cart?.entries.firstIndex(where: { $0.id == id }) else { return }
        if quantity <= 0 { dining.cart?.entries.remove(at: index) }
        else { dining.cart?.entries[index].quantity = min(20, quantity) }
        if dining.cart?.entries.isEmpty == true { dining.cart = nil }
        saveCart()
    }
    var cartNeedsReview: Bool {
        guard let cart = dining.cart, let menu = dining.menu else { return false }
        return cart.runId != menu.runId || cart.entries.contains { entry in
            guard let current = menu.items.first(where: { $0.id == entry.id }) else { return true }
            return entry.item.quoteVersion != current.quoteVersion
        }
    }
    var cartCanSubmit: Bool {
        guard contextId == "personal", !busy, pending == nil, errorCode.isEmpty,
              !cartNeedsReview, let cart = dining.cart, !cart.entries.isEmpty,
              let menu = dining.menu, menu.serviceOpen, dining.menuError.isEmpty else { return false }
        return cart.entries.allSatisfy { entry in
            guard let current = menu.items.first(where: { $0.id == entry.id }), current.orderable,
                  let available = current.availablePortions else { return false }
            return entry.quantity <= available
        }
    }
    func reviewCart() {
        guard var cart = dining.cart, let menu = dining.menu else { return }
        cart.entries = cart.entries.map { entry in
            if let current = menu.items.first(where: { $0.slug == entry.item.slug }) {
                return CartEntry(item: current, quantity: entry.quantity)
            }
            return entry
        }
        cart.runId = menu.runId; cart.menuCode = menu.menuCode; dining.cart = cart; saveCart()
    }
    func submitCart() async -> String? {
        guard cartCanSubmit, let cart = dining.cart else { return nil }
        let values: [String: Any] = ["run_id": cart.runId, "lines": cart.entries.map { entry in
            ["menu_item_id": entry.id, "item_version": entry.item.quoteVersion, "quantity": entry.quantity] as [String: Any]
        }]
        guard await mutate("/v1/orders", values: values), let data = lastMutationData else { return nil }
        return (try? api.decode(data) as OrderReceipt)?.orderId
    }
    func orderAction(_ order: FoodOrder, action: String, note: String = "", eventIds: [String] = [], code: String = "", allowVariance: Bool = false) async -> Bool {
        var values: [String: Any] = ["expected_version": order.version, "action": action, "note": note]
        if action == "confirm_fulfillment" { values["physical_event_ids"] = eventIds; values["allow_variance"] = allowVariance }
        if action == "collect" { values["pickup_code"] = code }
        return await mutate("/v1/orders/\(order.id)/actions", values: values)
    }
    func handleMenuLink(_ url: URL) {
        guard let code = MenuCode.parse(url.absoluteString) else { errorCode = "INVALID_MENU_CODE"; return }
        dining.pendingMenuCode = code
        if user != nil, !busy { selectContext("personal") }
    }
}
