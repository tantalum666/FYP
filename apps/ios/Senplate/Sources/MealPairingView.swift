import SwiftUI

struct MealEntrySection: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    var body: some View {
        if let meal = store.meals.records.first(where: \.active) {
            NavigationLink { MealDetailView(id: meal.id) } label: { MealRow(meal: meal) }.buttonStyle(.plain).accessibilityIdentifier("meal.continue")
        } else {
            NavigationLink { MealPairingView() } label: {
                Panel {
                    Label(prefs.text("Record a meal", "记录餐食"), systemImage: "scalemass").font(Theme.font(20, .title3, weight: .bold))
                    Text(prefs.text("Connect to the station to record each food as you add it.", "连接设备，逐项记录加入餐盘的食物。")) .font(Theme.font(14)).foregroundStyle(Theme.muted)
                    HStack { Text(prefs.text("Connect your plate", "连接餐盘")); Spacer(); Image(systemName: "arrow.right") }.font(Theme.font(15, weight: .semibold)).foregroundStyle(Theme.green)
                }
            }.buttonStyle(.plain).accessibilityIdentifier("meal.connect")
        }
    }
}

struct MealPairingView: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    @State private var code = ""
    @State private var scan = false
    @State private var requestId: String?
    @FocusState private var focused: Bool
    private var currentRequest: MealPairRequest? {
        if let requestId { return store.meals.requests.first { $0.id == requestId } }
        return store.meals.requests.first { $0.state == "pending" }
    }
    var body: some View {
        ScrollView { VStack(alignment: .leading, spacing: 22) {
            StoreNotices()
            if !store.meals.pairError.isEmpty { Notice(text: prefs.label(store.meals.pairError)) }
            if let meal = store.meals.records.first(where: \.active) {
                Panel {
                    Label(prefs.text("Your phone is connected", "手机已连接"), systemImage: "checkmark.circle").font(Theme.font(22, .title2, weight: .bold))
                    Text(prefs.text("Add one food at a time on the station.", "在设备上每次加入一种食物。")) .foregroundStyle(Theme.muted)
                    NavigationLink { MealDetailView(id: meal.id) } label: { Text(prefs.text("Open this meal", "打开此次餐食")) }.buttonStyle(PrimaryButtonStyle()).accessibilityIdentifier("meal.open")
                }
            } else if let request = currentRequest, request.state == "pending" {
                Panel {
                    Image(systemName: "link").font(.largeTitle).foregroundStyle(Theme.green)
                    Text(prefs.text("Confirm on the station", "请在设备上确认")).font(Theme.font(25, .title2, weight: .bold))
                    Text(prefs.text("Check that the station shows your name and this number. Your meal stays private until the station confirms the connection.", "请核对设备显示的姓名和此号码，设备确认连接后才会建立你的餐食记录。")) .font(Theme.font(14)).foregroundStyle(Theme.muted)
                    Text(request.checkCode).font(.system(size: 44, weight: .semibold, design: .monospaced)).tracking(6).foregroundStyle(Theme.green).accessibilityIdentifier("pair.check")
                    Text(prefs.text("Code expires at ", "代码有效至 ") + Format.time(request.expiresAt)).font(Theme.font(12, .caption)).foregroundStyle(Theme.muted)
                }
            } else {
                if let request = currentRequest, ["rejected", "expired"].contains(request.state) { Notice(text: prefs.text("This request ended. Get a new code from the station.", "此申请已结束，请在设备上获取新代码。")) }
                Panel {
                    Text(prefs.text("A private record, paired to you.", "配对到本人，私密地记录。")) .font(Theme.font(25, .title2, weight: .bold)).foregroundStyle(Theme.green)
                    Text(prefs.text("Start a personal meal on the station and confirm the empty plate. Use the short-lived pairing code it displays.", "在设备上开始个人餐食并确认空盘，再使用设备显示的短时配对码。")) .font(Theme.font(14)).foregroundStyle(Theme.muted)
                    Button { scan = true } label: { Label(prefs.text("Scan pairing code", "扫描配对码"), systemImage: "qrcode.viewfinder") }.buttonStyle(PrimaryButtonStyle())
                    TextField(prefs.text("Meal pairing code", "餐食配对码"), text: $code).textInputAutocapitalization(.characters).autocorrectionDisabled().textFieldStyle(.roundedBorder).focused($focused).submitLabel(.go).onSubmit { apply() }.accessibilityIdentifier("pair.code")
                    Button(prefs.text("Request connection", "申请连接")) { apply() }.disabled(store.busy || store.pending != nil || code.isEmpty).accessibilityIdentifier("pair.submit")
                }
                Text(prefs.text("Menu codes open menus. Meal pairing codes connect only after local confirmation.", "菜单代码用于浏览菜单，餐食配对码需要设备确认后才能连接。")) .font(Theme.font(12, .caption)).foregroundStyle(Theme.muted)
            }
        }.padding(20) }.background(Theme.ivory).navigationTitle(prefs.text("Connect your plate", "连接餐盘")).navigationBarTitleDisplayMode(.inline)
            .refreshable { await store.refresh() }.scrollDismissesKeyboard(.interactively)
            .sheet(isPresented: $scan) { NavigationStack { MenuScannerView(pairing: true) { raw in code = raw; scan = false } } }
            .onAppear { if let pending = store.meals.pendingPairCode { code = pending; store.meals.pendingPairCode = nil } }
            .onChange(of: store.meals.pendingPairCode) { _, pending in if let pending { code = pending; store.meals.pendingPairCode = nil } }
    }
    private func apply() {
        focused = false
        Task {
            if await store.applyPairing(code), let data = store.lastMutationData {
                struct Receipt: Decodable { let requestId: String }
                let result: Receipt? = try? store.api.decode(data); requestId = result?.requestId
            }
        }
    }
}

struct PersonalRecordsView: View {
    @Environment(Preferences.self) private var prefs
    @Environment(\.dynamicTypeSize) private var typeSize
    @State private var kind = "orders"
    var body: some View {
        VStack(spacing: 0) {
            Group { if typeSize.isAccessibilitySize { picker.pickerStyle(.menu) } else { picker.pickerStyle(.segmented) } }.padding(.horizontal, 18).padding(.vertical, 8)
            if kind == "orders" { CustomerOrdersView() } else { MealRecordsView() }
        }.background(Theme.ivory)
    }
    private var picker: some View {
        Picker(prefs.text("Record type", "记录类型"), selection: $kind) {
            Text(prefs.text("Orders", "订单")).tag("orders"); Text(prefs.text("Meals", "餐食")).tag("meals")
        }.accessibilityIdentifier("records.kind")
    }
}

struct MealRecordsView: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    @State private var source = "all"
    var body: some View {
        ScrollView { VStack(alignment: .leading, spacing: 18) {
            StoreNotices()
            Picker(prefs.text("Data source", "数据来源"), selection: $source) {
                Text(prefs.text("All", "全部")).tag("all"); Text(prefs.text("Demo", "演示")).tag("simulated"); Text(prefs.text("Replay", "回放")).tag("replay"); Text(prefs.text("Device", "设备")).tag("hardware")
            }.pickerStyle(.menu)
            let meals = store.meals.records.filter { source == "all" || $0.dataOrigin == source }
            if meals.isEmpty { EmptyPanel(title: prefs.text("Your next plate starts here", "从下一餐开始记录"), message: prefs.text("Connect to a station from Dining. Your recorded portions and references will appear here.", "在用餐页连接设备，记录的份量和参考资料会显示在这里。")) }
            ForEach(meals) { meal in NavigationLink { MealDetailView(id: meal.id) } label: { MealRow(meal: meal) }.buttonStyle(.plain).accessibilityIdentifier("meal.record." + meal.id) }
            Text(prefs.text("Your latest 100 meals. Reference nutrition describes the food provided, not verified intake.", "最近 100 次餐食。参考营养描述已提供食物，不表示已经确认的摄入。")) .font(Theme.font(12, .caption)).foregroundStyle(Theme.muted)
        }.padding(18) }.background(Theme.ivory).navigationTitle(prefs.text("Your meals", "我的餐食")).refreshable { await store.refresh() }
    }
}

struct MealRow: View {
    @Environment(Preferences.self) private var prefs
    let meal: MealRecord
    var body: some View {
        Panel {
            ViewThatFits(in: .horizontal) {
                HStack { Text(Format.mealDate(meal.createdAt)); Spacer(); StatusBadge(text: prefs.label("meal_" + meal.state)) }
                VStack(alignment: .leading, spacing: 8) { Text(Format.mealDate(meal.createdAt)); StatusBadge(text: prefs.label("meal_" + meal.state)) }
            }.font(Theme.font(14, weight: .semibold))
            Text("\(Format.grams(meal.providedG)) g").font(Theme.font(32, .largeTitle, weight: .bold)).foregroundStyle(Theme.green)
            Text(meal.portions.map { prefs.text($0.reference.nameEn, $0.reference.nameZh) }.joined(separator: " · ")).font(Theme.font(14)).foregroundStyle(Theme.muted)
            HStack { MealSourceBadge(origin: meal.dataOrigin); Spacer(); Image(systemName: "chevron.right").font(.caption) }
        }
    }
}

struct MealSourceBadge: View {
    @Environment(Preferences.self) private var prefs
    let origin: String
    var body: some View { StatusBadge(text: prefs.text(origin == "hardware" ? "Device data" : origin == "replay" ? "Replay data" : "Demo data", origin == "hardware" ? "设备数据" : origin == "replay" ? "回放数据" : "演示数据")) }
}
