import SwiftUI

private struct DiningSheet: Identifiable {
    enum Kind { case scanner, cart, dish(MenuItem) }
    let id = UUID()
    let kind: Kind
}

struct DiningView: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    @State private var code = ""
    @State private var loading = false
    @State private var sheet: DiningSheet?
    @State private var proposedMenu: DiningMenu?
    @State private var showSwitch = false
    @State private var showEntry = false
    @State private var showPairing = false
    @FocusState private var codeFocused: Bool
    var body: some View {
        ScrollView { VStack(alignment: .leading, spacing: 18) {
            StoreNotices()
            MealEntrySection()
            if store.dining.menu == nil { entryPanel }
            else { DisclosureGroup(prefs.text("Scan or enter another menu", "扫描或输入其他菜单"), isExpanded: $showEntry) { entryPanel.padding(.top, 10) } }
            if !store.dining.menuError.isEmpty {
                Notice(text: prefs.label(store.dining.menuError))
                if store.dining.menu != nil { Button(prefs.text("Refresh menu", "刷新菜单")) { Task { await store.refresh() } } }
            }
            if let menu = store.dining.menu {
                VStack(alignment: .leading, spacing: 8) {
                    HStack { StatusBadge(text: prefs.text(menu.dataOrigin == "replay" ? "Replay menu" : "Demo menu", menu.dataOrigin == "replay" ? "回放菜单" : "演示菜单")); Spacer() }
                    Text(prefs.text(menu.nameEn, menu.nameZh)).font(Theme.font(25, .title2, weight: .bold)).foregroundStyle(Theme.green)
                    Text(prefs.text(menu.serviceType == "staff_portioned" ? "Choose your portions. The kitchen will confirm availability." : "Buffet food is for self-service. Order counter items separately.", menu.serviceType == "staff_portioned" ? "选择份数后，由厨房确认供应。" : "自助菜品请自行取餐，柜台项目可单独下单。"))
                        .font(Theme.font(14)).foregroundStyle(Theme.muted)
                }
                if !menu.serviceOpen { Notice(text: prefs.text("This service has ended. Ordering is closed.", "本餐期已结束，停止接单。")) }
                ForEach(menu.items) { item in
                    Button { sheet = DiningSheet(kind: .dish(item)) } label: { DishRow(item: item) }.buttonStyle(.plain).accessibilityIdentifier("dish." + item.slug)
                }
                Text(prefs.text("Dish photos are illustrative. Prices and service data are for this demonstration.", "菜品图片为示意，价格及供餐数据用于当前演示。"))
                    .font(Theme.font(12, .caption)).foregroundStyle(Theme.muted)
            }
        }.padding(18) }.background(Theme.ivory).multilineTextAlignment(.leading).navigationTitle(prefs.text("Dining", "用餐"))
            .navigationDestination(isPresented: $showPairing) { MealPairingView() }
            .onChange(of: store.meals.pendingPairCode, initial: true) { _, code in if code != nil { showPairing = true } }
            .scrollDismissesKeyboard(.interactively).refreshable { await store.refresh() }
            .safeAreaInset(edge: .bottom) {
                if let cart = store.dining.cart, !cart.entries.isEmpty {
                    Button { sheet = DiningSheet(kind: .cart) } label: {
                        HStack { Image(systemName: "bag"); Text(prefs.text("View order", "查看购物车") + " (\(cart.quantity))"); Spacer(minLength: 4); Text(Format.money(cart.totalMinor)).lineLimit(1).minimumScaleFactor(0.7) }
                    }.buttonStyle(PrimaryButtonStyle()).padding(.horizontal, 18).padding(.vertical, 10).background(Theme.ivory).accessibilityIdentifier("cart.open")
                }
            }
            .sheet(item: $sheet) { destination in
                NavigationStack {
                    switch destination.kind {
                    case .scanner: MenuScannerView { raw in sheet = nil; Task { await open(raw) } }
                    case .cart: CartView()
                    case .dish(let item): DishDetail(item: item)
                    }
                }
            }
            .alert(prefs.text("Start a new order?", "开始新订单？"), isPresented: $showSwitch) {
                Button(prefs.text("Keep current order", "保留当前购物车"), role: .cancel) { proposedMenu = nil }
                Button(prefs.text("Clear cart and continue", "清空购物车并继续"), role: .destructive) {
                    if let menu = proposedMenu { store.activateMenu(menu, clearCart: true); showEntry = false }; proposedMenu = nil
                }
            } message: { Text(prefs.text("Your cart belongs to another menu or service. Its items will be removed if you continue.", "购物车属于另一菜单或餐期，继续会移除其中的菜品。")) }
            .task(id: store.dining.pendingMenuCode) {
                if let pending = store.dining.pendingMenuCode {
                    code = pending; await open(pending)
                    if store.dining.pendingMenuCode == pending { store.dining.pendingMenuCode = nil }
                }
            }
    }
    private var entryPanel: some View {
        Panel {
            Button { sheet = DiningSheet(kind: .scanner) } label: { Label(prefs.text("Scan a menu", "扫描菜单"), systemImage: "qrcode.viewfinder") }.buttonStyle(PrimaryButtonStyle()).accessibilityIdentifier("menu.scan")
            Text(prefs.text("Or enter the code shown at the counter.", "也可以输入柜台显示的菜单代码。"))
                .font(Theme.font(13)).foregroundStyle(Theme.muted)
            TextField(prefs.text("Menu code", "菜单代码"), text: $code).textInputAutocapitalization(.characters).autocorrectionDisabled()
                .textFieldStyle(.roundedBorder).focused($codeFocused).submitLabel(.go).onSubmit { Task { await open(code) } }.accessibilityIdentifier("menu.code")
            Button(prefs.text(loading ? "Opening…" : "Open menu", loading ? "正在打开…" : "打开菜单")) { Task { await open(code) } }
                .disabled(loading || code.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty).accessibilityIdentifier("menu.open")
        }
    }
    private func open(_ raw: String) async {
        guard !loading else { return }; codeFocused = false; loading = true; defer { loading = false }
        guard let menu = await store.openMenu(raw) else { return }
        if let cart = store.dining.cart, !cart.entries.isEmpty, cart.runId != menu.runId { proposedMenu = menu; showSwitch = true }
        else { store.activateMenu(menu); showEntry = false }
    }
}

struct DishRow: View {
    @Environment(Preferences.self) private var prefs
    let item: MenuItem
    var body: some View {
        Panel {
            Image("meal-" + item.slug).resizable().scaledToFill().frame(height: 168).clipped().clipShape(RoundedRectangle(cornerRadius: 8)).accessibilityHidden(true)
            ViewThatFits(in: .horizontal) {
                HStack(alignment: .firstTextBaseline) { title; Spacer(); price }
                VStack(alignment: .leading, spacing: 5) { title; price }
            }
            Text(prefs.text(item.descriptionEn, item.descriptionZh)).font(Theme.font(14)).foregroundStyle(Theme.muted)
            MenuAvailability(item: item)
            if item.popular { Label(prefs.text("Popular this service", "本餐期热销") + " · \(item.completedPortions) " + prefs.text("collected", "份已取餐"), systemImage: "sparkle").font(Theme.font(12, .caption)).foregroundStyle(Theme.green) }
        }
    }
    private var title: some View { Text(prefs.text(item.nameEn, item.nameZh)).font(Theme.font(20, .title3, weight: .bold)) }
    private var price: some View { Text(Format.money(item.priceMinor)).font(Theme.font(17, weight: .semibold)).foregroundStyle(Theme.green).fixedSize() }
}

struct MenuAvailability: View {
    @Environment(Preferences.self) private var prefs
    let item: MenuItem
    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(status).font(Theme.font(13, .footnote, weight: .semibold)).foregroundStyle(item.orderable ? Theme.green : Theme.amber)
            if item.serviceType == "buffet_self_service" {
                Text(prefs.text("Self-service · browse only", "自助取餐 · 仅供浏览")).font(Theme.font(12, .caption)).foregroundStyle(Theme.muted)
            }
            Text(prefs.text(item.stockSource == "measured" ? "Estimated from weight" : "Kitchen-maintained stock", item.stockSource == "measured" ? "按称重估算" : "厨房人工维护") + " · " + Format.time(item.updatedAt))
                .font(Theme.font(11, .caption)).foregroundStyle(Theme.muted)
        }
    }
    private var status: String {
        if item.status == "unavailable" { return prefs.text("Not available in this service", "本餐期暂不供应") }
        if let n = item.availablePortions, ["available", "low"].contains(item.status) { return prefs.text("\(n) portions available", "\(n) 份可供") }
        if item.availablePortions == 0 { return prefs.text("Currently sold out", "暂时售罄") }
        return prefs.text("Availability needs confirmation", "供应待确认")
    }
}

struct DishDetail: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    @Environment(\.dismiss) private var dismiss
    let item: MenuItem
    @State private var quantity = 1
    @State private var failed = false
    private var current: MenuItem { store.dining.menu?.items.first { $0.id == item.id } ?? item }
    private var available: Bool { store.dining.menu?.items.contains { $0.id == item.id && $0.orderable } == true && store.dining.menuError.isEmpty }
    var body: some View {
        ScrollView { VStack(alignment: .leading, spacing: 20) {
            DishRow(item: current)
            Panel {
                Text(prefs.text("Allergen information", "过敏原资料")).font(Theme.font(17, weight: .bold))
                Text(prefs.text(current.allergensEn, current.allergensZh)).font(Theme.font(14))
                if let grams = current.portionG { Text(prefs.text("Standard portion", "标准份量") + " · \(grams) g").font(Theme.font(13)).foregroundStyle(Theme.muted) }
            }
            if available {
                Stepper(prefs.text("Portions", "份数") + ": \(quantity)", value: $quantity, in: 1...max(1, min(20, current.availablePortions ?? 1))).accessibilityIdentifier("dish.quantity")
                Button(prefs.text("Add to order", "加入购物车")) { if store.addToCart(current, quantity: quantity) { dismiss() } else { failed = true } }
                    .buttonStyle(PrimaryButtonStyle()).disabled(store.busy || store.pending != nil).accessibilityIdentifier("dish.add")
            }
            if failed { Notice(text: prefs.text("Review your existing cart before adding items from this service.", "请先复核现有购物车，再添加本餐期菜品。")) }
        }.padding(18) }.background(Theme.ivory).navigationTitle(prefs.text("Dish details", "菜品详情")).navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button(prefs.text("Done", "完成")) { dismiss() } } }
    }
}

struct CartView: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    @Environment(\.dismiss) private var dismiss
    @State private var submittedId: String?
    var body: some View {
        Group {
            if let id = submittedId { OrderDetailView(id: id, personal: true) }
            else {
                ScrollView { VStack(alignment: .leading, spacing: 18) {
                    StoreNotices()
                    if !store.dining.menuError.isEmpty { Notice(text: prefs.label(store.dining.menuError)) }
                    if let cart = store.dining.cart {
                        if store.dining.menu?.serviceOpen == false { Notice(text: prefs.text("This service has ended or paused. The cart is saved, but it cannot be submitted now.", "本餐期已结束或暂停，购物车已保留，目前不能提交。")) }
                        if store.cartNeedsReview {
                            Notice(text: prefs.text("The menu or service has changed. Review the current items and prices before submitting.", "菜单或餐期已更新，请复核当前菜品和价格后再提交。"))
                            Button(prefs.text("Use latest menu & prices", "采用最新菜单与价格")) { store.reviewCart() }.disabled(store.busy || store.pending != nil)
                        }
                        ForEach(cart.entries) { entry in CartEntryView(entry: entry) }
                        Panel {
                            LabeledContent(prefs.text("Total", "合计"), value: Format.money(cart.totalMinor)).font(Theme.font(24, .title2, weight: .bold))
                            Text(prefs.text("Pay at the counter. This app does not process payment.", "请在柜台付款，App 不处理支付。")) .font(Theme.font(13)).foregroundStyle(Theme.muted)
                            Text(prefs.text("Submitting sends a request. Stock is reserved when the kitchen accepts.", "提交后等候厨房接单，接单时才预留供应。")) .font(Theme.font(13)).foregroundStyle(Theme.muted)
                        }
                        Button(prefs.text(store.busy ? "Submitting…" : "Submit order", store.busy ? "正在提交…" : "提交订单")) { Task { submittedId = await store.submitCart() } }
                            .buttonStyle(PrimaryButtonStyle()).disabled(!store.cartCanSubmit).accessibilityIdentifier("cart.submit")
                    } else { EmptyPanel(title: prefs.text("Your cart is empty", "购物车为空"), message: prefs.text("Choose items from the menu. Submitted orders appear in Records.", "从菜单选择菜品，已提交订单可在记录中查看。")) }
                }.padding(18) }.background(Theme.ivory).navigationTitle(prefs.text("Your order", "购物车")).navigationBarTitleDisplayMode(.inline)
            }
        }
        .toolbar { ToolbarItem(placement: .confirmationAction) { Button(prefs.text("Done", "完成")) { dismiss() }.disabled(store.busy) } }
        .interactiveDismissDisabled(store.busy)
    }
}

private struct CartEntryView: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    let entry: CartEntry
    private var current: MenuItem? { store.dining.menu?.items.first { $0.id == entry.id } }
    var body: some View {
        Panel {
            Text(prefs.text(entry.item.nameEn, entry.item.nameZh)).font(Theme.font(20, .title3, weight: .bold))
            Text(Format.money(entry.item.priceMinor) + " × \(entry.quantity)").font(Theme.font(15))
            if let item = current {
                if item.quoteVersion != entry.item.quoteVersion { Text(prefs.text("Current price", "当前价格") + ": " + Format.money(item.priceMinor)).foregroundStyle(Theme.amber) }
                if !item.orderable || entry.quantity > (item.availablePortions ?? 0) { Notice(text: prefs.text("Not enough available portions. Reduce the quantity or remove this item.", "可供份数不足，请减少数量或移除此项。")) }
            } else { Notice(text: prefs.text("This item is no longer on the current menu.", "当前菜单已没有此菜品。")) }
            Stepper(prefs.text("Portions", "份数") + ": \(entry.quantity)", value: Binding(get: { entry.quantity }, set: { store.cartQuantity(entry.id, quantity: $0) }), in: 1...20).disabled(store.busy || store.pending != nil)
            Button(prefs.text("Remove", "移除"), role: .destructive) { store.cartQuantity(entry.id, quantity: 0) }.disabled(store.busy || store.pending != nil)
        }
    }
}
